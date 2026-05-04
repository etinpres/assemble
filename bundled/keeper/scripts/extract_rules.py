"""Deterministic 5-rule violation extractor — keeper Step 2.

V4 Spike X, Task B3.

Reads run_dir artifacts that earlier bundle steps deposited (Step 1's
``audit_inventory.json`` plus optional ``parsed_scope.json``,
``dispatches.jsonl``, ``verify_result.json``) and applies five
deterministic rules to produce ``learning_candidates.json``:

  R1 ``rule-violation``   one candidate per failed dispatches.jsonl row
  R2 ``scope-deviation``  parsed_scope.deny ∩ git_diff_files (fnmatch)
  R3 ``ac-failure``       verify_result.verdict == "fail" → 1 candidate
  R4 ``todo-leakage``     TODO/FIXME/XXX added in HEAD~..HEAD diff
  R5 ``dispatch-failure`` aggregate of all failed dispatch rows

This script is *self-contained*: stdlib only, no ``server.*`` imports,
no LLM. The keeper Step 2 sub-agent invokes it via the canned bash
command ``python3 .../extract_rules.py <run_dir>``. Two runs against
the same run_dir produce byte-identical output (candidates are sorted
by (rule_id, evidence_hash) before write, evidence_hash is computed
from canonical-form JSON with sort_keys=True).

Exit codes:
  0 success — ``learning_candidates.json`` written.
  1 ``audit_inventory.json`` missing or unreadable in run_dir.

Stdout contract: prints exactly ``WROTE: <abs path>`` on success
(orchestrator regex ``^WROTE: (.+)$`` last-match parsing — Spike VII
F7 inheritance). All diagnostics go to stderr.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Markers R4 scans for in added diff lines. ``\b`` word boundaries
# prevent partial matches inside identifiers (e.g. ``MYTODO``).
_TODO_MARKER_RE = re.compile(r"\b(TODO|FIXME|XXX)\b")

# Per-rule line excerpt cap (R4 evidence). 120 chars matches the
# project's narrow-margin convention; longer additions are truncated
# without ellipsis (the marker + first 120 chars is enough triage signal).
_LINE_EXCERPT_CAP = 120


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_evidence(evidence: dict) -> str:
    """Compute the canonical sha256 of an evidence object.

    ``sort_keys=True`` + ``ensure_ascii=False`` so identical evidence
    always produces identical hashes regardless of dict insertion order
    or non-ASCII content (Korean run summaries round-trip).
    """
    canonical = json.dumps(evidence, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _make_candidate(rule_id: str, category: str, evidence: dict) -> dict:
    """Build a candidate dict with hash already computed."""
    return {
        "rule_id": rule_id,
        "category": category,
        "evidence": evidence,
        "evidence_hash": _hash_evidence(evidence),
    }


def _load_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file. Empty/missing → empty list. Skips blank lines.

    Malformed lines are silently dropped — keeper is observational and
    must not raise on partially-corrupt run artifacts.
    """
    if not path.exists():
        return []
    rows: list[dict] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    rows.append(json.loads(stripped))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return rows


def _load_json(path: Path) -> dict | None:
    """Read a JSON file. Missing or malformed → None."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _load_deny_patterns(parsed_scope: dict) -> list[str]:
    """Extract deny patterns from parsed_scope.json, tolerating both
    string-form (legacy / hand-authored) and object-form (production
    parser output schema: ``{"path": str, "note": str}``).

    Codex retro Finding 1 (Spike X E2): the production parser at
    ``server/scope_parser.py`` emits object-form deny entries; the
    earlier list[str]-only path silently false-negatived on real V4
    ``parsed_scope.json`` files, so keeper missed core deny-list scope
    deviations. Forward-compat: unknown shapes are skipped silently
    (keeper is observational and never raises on partial artifacts).
    """
    raw = parsed_scope.get("deny", []) or []
    patterns: list[str] = []
    for item in raw:
        if isinstance(item, str):
            if item:
                patterns.append(item)
        elif isinstance(item, dict):
            path = item.get("path")
            if isinstance(path, str) and path:
                patterns.append(path)
        # else: silently skip unknown shapes (forward-compat)
    return patterns


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

def rule_r1_dispatch_failures_per_row(dispatches: list[dict]) -> list[dict]:
    """R1 — one candidate per ``status == "failed"`` dispatch row."""
    candidates: list[dict] = []
    for row in dispatches:
        if row.get("status") != "failed":
            continue
        evidence = {
            "step": row.get("step", ""),
            "subagent_type": row.get("subagent_type", ""),
            "note": row.get("note", "") or "",
        }
        candidates.append(_make_candidate("R1", "rule-violation", evidence))
    return candidates


def rule_r2_scope_deviation(deny_patterns: list[str],
                            diff_files: list[str]) -> list[dict]:
    """R2 — one candidate per (deny_pattern, diff_file) fnmatch hit.

    ``fnmatch.fnmatch`` handles both literal paths and glob patterns
    uniformly: ``"src/auth.py"`` only matches exactly that path,
    while ``"auth/*"`` matches any file directly under ``auth/``.
    """
    candidates: list[dict] = []
    for pattern in deny_patterns:
        if not isinstance(pattern, str) or not pattern:
            continue
        for fpath in diff_files:
            if not isinstance(fpath, str) or not fpath:
                continue
            if fnmatch.fnmatch(fpath, pattern):
                evidence = {"file": fpath, "deny_pattern": pattern}
                candidates.append(
                    _make_candidate("R2", "scope-deviation", evidence)
                )
    return candidates


def rule_r3_ac_failure(verify_result: dict | None) -> list[dict]:
    """R3 — one candidate iff verify_result.verdict == "fail"."""
    if not verify_result:
        return []
    if verify_result.get("verdict") != "fail":
        return []
    evidence = {
        "command": verify_result.get("command_executed") or "unknown",
        "reason": verify_result.get("reason") or "verdict=fail",
    }
    return [_make_candidate("R3", "ac-failure", evidence)]


def rule_r4_todo_leakage(cwd: Path) -> list[dict]:
    """R4 — one candidate per *net-added* line containing TODO/FIXME/XXX.

    Runs ``git diff --unified=0 HEAD~..HEAD`` via argv-list subprocess
    (no shell). On non-zero exit (no commits, not a repo, etc.) returns
    an empty list — keeper is observational, never raises.

    Spike X cleanup F-X1: a refactor that *moves* a pre-existing TODO
    (delete from line N, add at line M) used to emit a spurious
    candidate — net count of markers is unchanged but the script counted
    only the addition. Fix: track both adds and deletes per
    ``(marker, line excerpt)`` key and emit only ``net_added > 0``
    candidates. If the user *modifies* the TODO text during the move
    (different excerpt), the new text is a net addition (correct) and
    the old text is a net zero (correctly suppressed).
    """
    try:
        proc = subprocess.run(
            ["git", "diff", "--unified=0", "HEAD~..HEAD"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []
    if proc.returncode != 0:
        return []

    # (marker, excerpt) → counter. Key collapses identical lines so a
    # moved TODO with the same text matches.
    added: dict[tuple[str, str], int] = {}
    deleted: dict[tuple[str, str], int] = {}

    for raw_line in proc.stdout.splitlines():
        # Skip diff headers (``+++ b/path`` and ``--- a/path``).
        if raw_line.startswith("+++") or raw_line.startswith("---"):
            continue
        if raw_line.startswith("+"):
            content = raw_line[1:]
            m = _TODO_MARKER_RE.search(content)
            if not m:
                continue
            marker = m.group(1)
            excerpt = content[:_LINE_EXCERPT_CAP]
            key = (marker, excerpt)
            added[key] = added.get(key, 0) + 1
        elif raw_line.startswith("-"):
            content = raw_line[1:]
            m = _TODO_MARKER_RE.search(content)
            if not m:
                continue
            marker = m.group(1)
            excerpt = content[:_LINE_EXCERPT_CAP]
            key = (marker, excerpt)
            deleted[key] = deleted.get(key, 0) + 1

    candidates: list[dict] = []
    for key, n_added in added.items():
        marker, excerpt = key
        net_added = n_added - deleted.get(key, 0)
        if net_added <= 0:
            continue
        evidence = {"marker": marker, "line_excerpt": excerpt}
        # Preserve the original 1-per-line semantics for net additions:
        # if the user adds the same TODO text 3× and deletes 1×, emit
        # 2 candidates (each identical → identical evidence_hash; sort
        # de-duplication is the keeper-aggregator's responsibility).
        for _ in range(net_added):
            candidates.append(_make_candidate("R4", "todo-leakage", evidence))
    return candidates


def rule_r5_dispatch_failure_aggregate(dispatches: list[dict]) -> list[dict]:
    """R5 — single aggregate candidate enumerating all failed steps.

    Distinct from R1 (per-row detail); R5 is the dispatch-discipline
    summary used by Track B's STAGE_CATEGORY_PRIORITY for ranking.
    """
    failed_steps: list[str] = []
    for row in dispatches:
        if row.get("status") != "failed":
            continue
        step = row.get("step", "")
        if isinstance(step, str):
            failed_steps.append(step)
    if not failed_steps:
        return []
    evidence = {
        "failed_count": len(failed_steps),
        "steps": failed_steps,
    }
    return [_make_candidate("R5", "dispatch-failure", evidence)]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def extract_candidates(run_dir: Path, cwd: Path | None = None) -> dict:
    """Apply all 5 rules. Returns the full result dict (run_id +
    sorted candidates list).

    ``cwd`` is the working directory passed to the R4 ``git diff`` probe
    (defaults to current working directory). Tests can override to point
    at a fixture repo without polluting the assemble repo's HEAD.
    """
    if cwd is None:
        cwd = Path.cwd()

    audit_inventory = _load_json(run_dir / "audit_inventory.json")
    if audit_inventory is None:
        raise FileNotFoundError(
            f"audit_inventory.json missing or unreadable in {run_dir}"
        )

    run_id = audit_inventory.get("run_id", "")

    # Pull inputs for each rule. All optional except audit_inventory.
    parsed_scope = _load_json(run_dir / "parsed_scope.json") or {}
    dispatches = _load_jsonl(run_dir / "dispatches.jsonl")
    verify_result = _load_json(run_dir / "verify_result.json")

    # Shape-tolerant deny loader — production parser emits object-form
    # ``{"path": str, "note": str}`` while legacy / hand-authored fixtures
    # use list[str]. See _load_deny_patterns docstring for Codex F1 ref.
    deny_patterns = _load_deny_patterns(parsed_scope)

    git_probes = audit_inventory.get("git_probes", {}) or {}
    diff_files = git_probes.get("git_diff_files", []) or []

    # Run rules.
    candidates: list[dict] = []
    candidates.extend(rule_r1_dispatch_failures_per_row(dispatches))
    candidates.extend(rule_r2_scope_deviation(deny_patterns, diff_files))
    candidates.extend(rule_r3_ac_failure(verify_result))
    candidates.extend(rule_r4_todo_leakage(cwd))
    candidates.extend(rule_r5_dispatch_failure_aggregate(dispatches))

    # Deterministic order — (rule_id, evidence_hash) lexicographic.
    candidates.sort(key=lambda c: (c["rule_id"], c["evidence_hash"]))

    return {"run_id": run_id, "candidates": candidates}


def write_candidates(run_dir: Path, result: dict) -> Path:
    """Serialize the result dict into ``learning_candidates.json``.

    ``sort_keys=True`` + ``ensure_ascii=False`` — same canonicalization
    used for evidence_hash so file content matches what hashes covered.
    """
    out = run_dir / "learning_candidates.json"
    out.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            "usage: extract_rules.py <run_dir>",
            file=sys.stderr,
        )
        return 1
    run_dir = Path(argv[1])
    if not run_dir.is_dir():
        print(
            f"run_dir does not exist or is not a directory: {run_dir}",
            file=sys.stderr,
        )
        return 1
    try:
        result = extract_candidates(run_dir)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    out = write_candidates(run_dir, result)
    print(f"WROTE: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
