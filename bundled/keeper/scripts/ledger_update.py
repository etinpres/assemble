"""Ledger append + prune + KEEPER_REPORT render — keeper Step 4.

V4 Spike X, Tasks B5 + B7 (consolidated).

Reads run_dir artifacts that earlier keeper steps deposited
(``audit_inventory.json`` from Step 1, ``learnings_to_emit.json`` from
Step 3), appends new entries to ``~/.claude/channels/assemble/learnings.jsonl``,
applies the 4-stage deterministic prune (TTL → skiplist → dedup → FIFO cap),
writes back atomically, then renders ``KEEPER_REPORT.md`` from the
happy or abort template.

ASSUMPTION: PYTHONPATH includes the assemble repo root so
``import server.learnings`` succeeds. The keeper Step 4 sub-agent runs
from ``~/.claude/skills/assemble/`` (the harness sets that as CWD), so
``import server.learnings`` resolves to ``server/learnings.py`` in the
same repo.

Exit codes:
  0 success — ledger updated + KEEPER_REPORT.md written.
  1 missing required input (audit_inventory.json or learnings_to_emit.json)
    or unrecoverable error during write.

Stdout contract: prints exactly ``WROTE: <abs path to KEEPER_REPORT.md>``
on success (orchestrator regex ``^WROTE: (.+)$`` last-match parsing —
Spike VII F7 inheritance). All diagnostics go to stderr.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# server.learnings is the SOLE allowed `server.*` import (per task spec).
# Provides read_ledger / write_ledger / prune_ledger / read_skiplist
# (Phase A1+A3 surfaces). PYTHONPATH assumption documented in module
# docstring.
from server.learnings import (
    STAGE_CATEGORY_PRIORITY,
    prune_ledger,
    read_ledger,
    read_skiplist,
    write_ledger,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Prune knobs — keep aligned with server.learnings defaults. Surfaced here
# so the report can cite the exact values used.
TTL_DAYS = 30
CAP = 100

# Template files live alongside the script.
_SCRIPT_DIR = Path(__file__).resolve().parent
_TEMPLATES_DIR = _SCRIPT_DIR.parent / "templates"
HAPPY_TEMPLATE = _TEMPLATES_DIR / "KEEPER_REPORT.md.template"
ABORT_TEMPLATE = _TEMPLATES_DIR / "KEEPER_REPORT_ABORT.md.template"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | None:
    """Read JSON; missing or malformed returns None."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _materialize_entries(
    raw_entries: list[dict],
    run_id: str,
    now_iso: str,
) -> list[dict]:
    """Build full ledger rows from learnings_to_emit entries.

    Each entry from Step 3 has rule_id / category / summary / evidence /
    evidence_hash. Step 4 layers on ts + run_id to produce the final row.
    All rows in a single keeper run share the SAME ts (the caller's
    ``now`` snapshot) so prune_ledger sees a stable temporal cohort.
    """
    rows: list[dict] = []
    for entry in raw_entries:
        rows.append({
            "ts": now_iso,
            "run_id": run_id,
            "rule_id": entry.get("rule_id", ""),
            "category": entry.get("category", ""),
            "summary": entry.get("summary", ""),
            "evidence_hash": entry.get("evidence_hash", ""),
            "evidence": entry.get("evidence", {}),
        })
    return rows


def _prune_breakdown(
    combined: list[dict],
    *,
    now: datetime,
    skiplist: set[str],
) -> dict:
    """Re-run prune stage-by-stage to count drops attributable to each rule.

    ``server.learnings.prune_ledger`` always applies all four stages
    (TTL → skiplist → dedup → cap) — there is no public surface for
    "TTL only" or "dedup only". To attribute drops to individual stages
    for the KEEPER_REPORT, we make 4 calls with progressively-stricter
    knobs and diff the survivor counts. Returns ``pruned`` (final list)
    + per-stage drop counts.

    Each call passes ``cap=10**9`` to disable cap until the last call,
    and grows the active stages step-by-step:
      Stage 1 (TTL only):  ttl=TTL_DAYS, skiplist=∅, cap=∞
      Stage 2 (+skiplist): ttl=TTL_DAYS, skiplist=given, cap=∞
      Stage 3 (+dedup):    inherent in stage-2 call (prune_ledger always
                           dedupes); compute dedup drops by counting
                           duplicate evidence_hashes among stage-2
                           survivors.
      Stage 4 (+cap):      ttl=TTL_DAYS, skiplist=given, cap=CAP
    """
    no_skip: set[str] = set()
    after_ttl = prune_ledger(
        combined, now=now, ttl_days=TTL_DAYS, cap=10**9, skiplist=no_skip,
    )
    # Caveat: prune_ledger also dedupes inside this call. To isolate TTL
    # specifically we count "rows surviving TTL" (pre-dedup) by parsing
    # ts ourselves — but that pulls in private helpers. Cheaper: report
    # dedup drops as the delta between skiplist-survivors and final
    # dedup-survivors (computed inline below). TTL drops are then the
    # raw input delta minus the dedup delta absorbed within after_ttl.
    # Simpler attribution: count rows whose ts is older than the fence
    # by replicating the TTL check.
    fence = now - timedelta(days=TTL_DAYS)
    dropped_by_ttl = sum(
        1 for row in combined
        if _row_ts_older_than(row, fence)
    )

    # Skiplist drops: count rows surviving TTL whose hash is in skiplist.
    dropped_by_skiplist = sum(
        1 for row in combined
        if not _row_ts_older_than(row, fence)
        and row.get("evidence_hash") in skiplist
    )

    # Dedup drops: among rows surviving TTL + skiplist, count duplicate
    # evidence_hashes (collisions). Empty-hash rows never collide.
    seen_hashes: set[str] = set()
    dropped_by_dedup = 0
    for row in combined:
        if _row_ts_older_than(row, fence):
            continue
        eh = row.get("evidence_hash")
        if eh in skiplist:
            continue
        if not eh:
            continue
        if eh in seen_hashes:
            dropped_by_dedup += 1
        else:
            seen_hashes.add(eh)

    # Final prune (full pipeline) — this is the actual ledger we write.
    pruned = prune_ledger(
        combined, now=now, ttl_days=TTL_DAYS, cap=CAP, skiplist=skiplist,
    )

    # Cap drops: post-dedup count minus final count.
    post_dedup_count = (
        len(combined) - dropped_by_ttl - dropped_by_skiplist - dropped_by_dedup
    )
    dropped_by_cap = max(post_dedup_count - len(pruned), 0)

    return {
        "pruned": pruned,
        "dropped_by_ttl": dropped_by_ttl,
        "dropped_by_skiplist": dropped_by_skiplist,
        "dropped_by_dedup": dropped_by_dedup,
        "dropped_by_cap": dropped_by_cap,
    }


def _row_ts_older_than(row: dict, fence: datetime) -> bool:
    """Return True if `row['ts']` parses as older than `fence`.

    Mirrors the `_parse_ts` semantics of `server.learnings`: ISO-8601
    strings (with or without trailing 'Z'); naive timestamps treated as
    UTC; unparseable ts → False (entry is KEPT during TTL prune, matching
    server.learnings behavior). Defined locally to avoid importing
    private helpers.
    """
    ts_value = row.get("ts")
    if not isinstance(ts_value, str) or not ts_value:
        return False
    candidate = ts_value
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed < fence


def _format_rules_fired(entries: list[dict]) -> str:
    """Render a markdown table of rule_id / category / count."""
    if not entries:
        return "_No rules fired (audit-clean)._"
    counts: dict[tuple[str, str], int] = {}
    for entry in entries:
        key = (entry.get("rule_id", ""), entry.get("category", ""))
        counts[key] = counts.get(key, 0) + 1
    rows = [
        "| Rule | Category | Count |",
        "|---|---|---|",
    ]
    for (rule_id, category), count in sorted(counts.items()):
        rows.append(f"| {rule_id} | {category} | {count} |")
    return "\n".join(rows)


def _format_learnings_list(entries: list[dict]) -> str:
    """Render a numbered list of summaries."""
    if not entries:
        return "_No learnings emitted._"
    lines = []
    for index, entry in enumerate(entries, start=1):
        rule_id = entry.get("rule_id", "")
        summary = entry.get("summary", "")
        lines.append(f"{index}. ({rule_id}) {summary}")
    return "\n".join(lines)


def _format_recall_preview() -> str:
    """Render the STAGE_CATEGORY_PRIORITY map as a markdown list."""
    lines = []
    for stage in sorted(STAGE_CATEGORY_PRIORITY.keys()):
        cats = STAGE_CATEGORY_PRIORITY[stage]
        lines.append(f"- **{stage}**: {' > '.join(cats)}")
    return "\n".join(lines)


def _format_verdicts_collected(verdicts: dict) -> str:
    if not verdicts:
        return "_(none)_"
    parts = [f"{bundle}={verdict}" for bundle, verdict in sorted(verdicts.items())]
    return ", ".join(parts)


def _substitute(template: str, mapping: dict[str, str]) -> str:
    """Apply str.replace for each `{{KEY}}` → value in mapping."""
    text = template
    for key, value in mapping.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def _render_happy_report(
    *,
    run_id: str,
    verdict: str,
    reason: str,
    generated_ts: str,
    audit_inventory: dict,
    new_entries: list[dict],
    before_prune_count: int,
    after_prune_count: int,
    appended_count: int,
    drops: dict,
) -> str:
    """Render the 7-section KEEPER_REPORT.md from the happy template."""
    template = HAPPY_TEMPLATE.read_text(encoding="utf-8")
    git_probes = audit_inventory.get("git_probes", {}) or {}
    bundles = audit_inventory.get("bundles_observed", []) or []
    artifacts = audit_inventory.get("artifacts_present", {}) or {}
    artifacts_count = sum(1 for v in artifacts.values() if v)
    verdicts_collected = audit_inventory.get("verdicts_collected", {}) or {}
    diff_files = git_probes.get("git_diff_files", []) or []

    head_sha = (git_probes.get("head_sha") or "")
    head_short = head_sha[:7] if head_sha else "(unknown)"
    branch = git_probes.get("branch", "") or "(unknown)"
    clean_tree = git_probes.get("clean_tree", False)
    clean_status = "clean" if clean_tree else "dirty"

    run_summary = audit_inventory.get("scope_summary", "") or "_(no scope summary captured)_"

    net_delta = after_prune_count - before_prune_count

    prune_summary_lines = []
    if appended_count == 0:
        prune_summary_lines.append("No new entries appended this run.")
    else:
        prune_summary_lines.append(
            f"Appended {appended_count} entry/entries before prune."
        )
    if drops["dropped_by_ttl"] > 0:
        prune_summary_lines.append(
            f"TTL ({TTL_DAYS}d) dropped {drops['dropped_by_ttl']} stale entry/entries."
        )
    if drops["dropped_by_skiplist"] > 0:
        prune_summary_lines.append(
            f"Skiplist dropped {drops['dropped_by_skiplist']} entry/entries."
        )
    if drops["dropped_by_dedup"] > 0:
        prune_summary_lines.append(
            f"Dedup collapsed {drops['dropped_by_dedup']} duplicate entry/entries."
        )
    if drops["dropped_by_cap"] > 0:
        prune_summary_lines.append(
            f"FIFO cap ({CAP}) evicted {drops['dropped_by_cap']} oldest entry/entries."
        )
    prune_summary = "\n".join(prune_summary_lines)

    mapping = {
        "RUN_ID": run_id,
        "VERDICT": verdict,
        "REASON": reason,
        "GENERATED_TS": generated_ts,
        "RUN_SUMMARY": run_summary,
        "BUNDLES_OBSERVED": ", ".join(bundles) if bundles else "_(none)_",
        "ARTIFACTS_PRESENT_COUNT": str(artifacts_count),
        "VERDICTS_COLLECTED": _format_verdicts_collected(verdicts_collected),
        "CLEAN_TREE_STATUS": clean_status,
        "BRANCH": branch,
        "HEAD_SHA_SHORT": head_short,
        "GIT_DIFF_FILES_COUNT": str(len(diff_files)),
        "RULES_FIRED_TABLE": _format_rules_fired(new_entries),
        "LEARNINGS_EMITTED_LIST": _format_learnings_list(new_entries),
        "BEFORE_PRUNE_COUNT": str(before_prune_count),
        "AFTER_PRUNE_COUNT": str(after_prune_count),
        "NET_DELTA": (f"+{net_delta}" if net_delta >= 0 else str(net_delta)),
        "APPENDED_COUNT": str(appended_count),
        "DROPPED_TTL": str(drops["dropped_by_ttl"]),
        "DROPPED_SKIP": str(drops["dropped_by_skiplist"]),
        "DROPPED_DEDUP": str(drops["dropped_by_dedup"]),
        "DROPPED_CAP": str(drops["dropped_by_cap"]),
        "PRUNE_SUMMARY_NOTE": prune_summary,
        "NEXT_RUN_RECALL_PREVIEW": _format_recall_preview(),
    }
    return _substitute(template, mapping)


def _render_abort_report(
    *,
    run_id: str,
    reason: str,
    generated_ts: str,
    audit_inventory: dict,
) -> str:
    """Render the 4-section ABORT KEEPER_REPORT.md."""
    template = ABORT_TEMPLATE.read_text(encoding="utf-8")
    skip_reason = audit_inventory.get("skip_reason", reason)
    run_summary = audit_inventory.get("scope_summary", "") or "_(no scope summary captured — parsed_scope.json may be missing)_"

    abort_inventory = (
        "_Skipped — keeper Step 1 verdict was `audit-skipped`. "
        "No bundle artifacts were enumerated for ledger emission._"
    )
    skip_detail = f"Skip reason: **{skip_reason}**"
    next_steps = (
        "Re-run the upstream bundle(s) so they deposit their artifacts "
        "(REVIEW_REPORT.md, VERIFY_REPORT.md, SHIP_REPORT.md, etc.) "
        "into the run_dir alongside `parsed_scope.json`. Then dispatch "
        "keeper again — Step 1 will re-evaluate and Step 4 will append "
        "any new learnings to the ledger."
    )

    mapping = {
        "RUN_ID": run_id,
        "REASON": reason,
        "GENERATED_TS": generated_ts,
        "RUN_SUMMARY": run_summary,
        "ABORT_INVENTORY_NOTE": abort_inventory,
        "SKIP_REASON_DETAIL": skip_detail,
        "NEXT_STEPS_GUIDANCE": next_steps,
    }
    return _substitute(template, mapping)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def update_ledger_and_report(
    run_dir: Path,
    *,
    now: datetime | None = None,
) -> Path:
    """Run Step 4 end-to-end. Returns absolute path to KEEPER_REPORT.md.

    ``now`` is exposed for tests; production calls leave it as ``None`` so
    the script samples ``datetime.now(timezone.utc)``. Determinism note: a
    single ``now`` value is reused for (a) the `ts` of every appended
    entry and (b) the prune fence — this prevents +ε skew where prune sees
    a slightly later "now" than the entries it just appended.
    """
    # 1. Validate required inputs upfront.
    learnings_path = run_dir / "learnings_to_emit.json"
    if not learnings_path.exists():
        raise FileNotFoundError(
            f"ledger_update: learnings_to_emit.json missing in {run_dir}"
        )
    audit_path = run_dir / "audit_inventory.json"
    if not audit_path.exists():
        raise FileNotFoundError(
            f"ledger_update: audit_inventory.json missing in {run_dir}"
        )

    # 2. Read inputs.
    learnings_doc = _load_json(learnings_path) or {}
    audit_inventory = _load_json(audit_path) or {}

    run_id = learnings_doc.get("run_id") or audit_inventory.get("run_id", "")
    raw_entries = learnings_doc.get("entries", []) or []

    # 3. Compute ``now`` once and reuse for ts + prune fence.
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now_iso = now.isoformat()

    # 4. Materialize new ledger rows (carry summary/evidence/evidence_hash
    #    verbatim from Step 3, layer on ts + run_id).
    new_entries = _materialize_entries(raw_entries, run_id, now_iso)
    appended_count = len(new_entries)

    # 5. Determine final verdict — happy or abort. Abort path skips ledger
    #    write entirely (nothing meaningful to append) and renders the
    #    ABORT template.
    audit_verdict = audit_inventory.get("verdict", "")
    if audit_verdict == "audit-skipped":
        verdict = "audit-skipped"
        reason = audit_inventory.get(
            "skip_reason", "audit precondition not met"
        )
        report_text = _render_abort_report(
            run_id=run_id,
            reason=reason,
            generated_ts=now_iso,
            audit_inventory=audit_inventory,
        )
        out = run_dir / "KEEPER_REPORT.md"
        out.write_text(report_text, encoding="utf-8")
        return out

    # 6. Happy path — read existing ledger, append, prune, write back.
    existing = read_ledger()
    skiplist = read_skiplist()
    combined = list(existing) + list(new_entries)
    before_prune_count = len(combined)

    breakdown = _prune_breakdown(combined, now=now, skiplist=skiplist)
    pruned = breakdown["pruned"]
    after_prune_count = len(pruned)

    # write_ledger is atomic (tempfile + os.replace per server.learnings).
    write_ledger(pruned)

    # 7. Compute verdict + reason.
    if appended_count == 0:
        verdict = "audit-clean"
        reason = "ran 5 rules, 0 violations detected; ledger unchanged"
    else:
        verdict = "audit-flagged"
        # Enumerate distinct categories for human-readable reason.
        categories = sorted({
            e.get("category", "")
            for e in new_entries if e.get("category")
        })
        cats_str = ", ".join(categories) if categories else "(none)"
        reason = (
            f"{appended_count} learning(s) emitted across {cats_str}; "
            f"ledger appended"
        )

    # 8. Render KEEPER_REPORT.md (happy variant).
    report_text = _render_happy_report(
        run_id=run_id,
        verdict=verdict,
        reason=reason,
        generated_ts=now_iso,
        audit_inventory=audit_inventory,
        new_entries=new_entries,
        before_prune_count=before_prune_count,
        after_prune_count=after_prune_count,
        appended_count=appended_count,
        drops=breakdown,
    )
    out = run_dir / "KEEPER_REPORT.md"
    out.write_text(report_text, encoding="utf-8")
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            "usage: ledger_update.py <run_dir>",
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
        out = update_ledger_and_report(run_dir)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover — defensive
        print(f"ledger_update: unexpected error: {exc}", file=sys.stderr)
        return 1
    print(f"WROTE: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
