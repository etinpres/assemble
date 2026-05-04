"""End-to-end integration tests for the keeper bundle pipeline
(V4 Spike X, Phase F1).

The keeper bundle is a 4-step pipeline:

    Step 1  audit_inventory.json     (Python; logic-only, mirrored here)
    Step 2  learning_candidates.json (extract_rules.py — script invoked
                                      via subprocess)
    Step 3  learnings_to_emit.json   (deterministic templates; logic
                                      mirrored here from the Step 3
                                      prompt's save block)
    Step 4  KEEPER_REPORT.md +
            ledger.jsonl append      (ledger_update.py — script invoked
                                      via subprocess)

The actual sub-agent dispatch chain (`dispatch_and_record` calling the
Agent tool) cannot run inside pytest, so these integration tests
substitute by invoking the bundled scripts directly. Step 1 + Step 3 are
template-driven and pure — we replay their logic here so each test
exercises the same data flow the real keeper would, end-to-end.

Filesystem isolation: every test seeds a fresh ``tmp_path`` run_dir and
uses ``ASSEMBLE_HOME`` monkeypatching to redirect the global ledger to
``tmp_path/.claude/channels/assemble/learnings.jsonl``. R4's git probe is
exercised against a real git fixture repo so the rule's
``git diff --unified=0 HEAD~..HEAD`` invocation runs end-to-end.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ASSEMBLE_ROOT = Path(__file__).resolve().parents[2]
EXTRACT_RULES = ASSEMBLE_ROOT / "bundled" / "keeper" / "scripts" / "extract_rules.py"
LEDGER_UPDATE = ASSEMBLE_ROOT / "bundled" / "keeper" / "scripts" / "ledger_update.py"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """Redirect ``~/.claude/...`` to tmp_path so the ledger writes go to a
    sandbox per test. Mirrors `test_keeper_ledger_update_script.py`.
    """
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def run_dir(tmp_path):
    """A fresh run_dir for each test. Distinct from ``isolated_home`` so
    that artifact seeding doesn't pollute the ledger sandbox.
    """
    rd = tmp_path / "run_dir"
    rd.mkdir()
    return rd


# ---------------------------------------------------------------------------
# Step 1 logic — mirrored from
#   bundled/keeper/prompts/subagent/keeper_audit_step1.md
# (the prompt's save block, simplified to the inputs we care about for
# integration tests). Runs in-process so we don't need to dispatch a
# sub-agent. The logic is pure and deterministic.
# ---------------------------------------------------------------------------

def write_audit_inventory(
    rd: Path,
    *,
    run_id: str,
    bundles_observed: list[str] | None = None,
    artifacts_present: dict[str, bool] | None = None,
    verdicts_collected: dict[str, str] | None = None,
    git_diff_files: list[str] | None = None,
    scope_summary: str = "integration test scope",
    verdict: str = "audit-ready",
    skip_reason: str | None = None,
) -> Path:
    """Build + write ``audit_inventory.json``.

    Mirrors Step 1 prompt's save block. Tests may construct any verdict
    (audit-ready or audit-skipped) and seed the inputs that downstream
    rules consume (``git_diff_files`` for R2; ``bundles_observed`` /
    ``artifacts_present`` for the report renderer).
    """
    inv = {
        "run_id": run_id,
        "verdict": verdict,
        "bundles_observed": bundles_observed or [],
        "artifacts_present": artifacts_present or {
            "parsed_scope.json": True,
        },
        "dispatch_row_count": 0,
        "verdicts_collected": verdicts_collected or {},
        "git_probes": {
            "clean_tree": True,
            "dirty_files": [],
            "head_sha": "abc123def4567890",
            "branch": "master",
            "git_diff_files": git_diff_files or [],
        },
        "scope_summary": scope_summary,
        "errors": [],
    }
    if skip_reason is not None:
        inv["skip_reason"] = skip_reason
    out = rd / "audit_inventory.json"
    out.write_text(
        json.dumps(inv, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    return out


def write_parsed_scope(
    rd: Path,
    *,
    deny: list | None = None,
    task_summary: str = "integration test",
) -> Path:
    """Write parsed_scope.json with deny entries (object-form preferred,
    matching the production parser's emission shape — see Codex F1).
    """
    scope = {"task_summary": task_summary, "deny": deny or []}
    out = rd / "parsed_scope.json"
    out.write_text(json.dumps(scope), encoding="utf-8")
    return out


def write_dispatches(rd: Path, rows: list[dict]) -> Path:
    """Write dispatches.jsonl (one row per line)."""
    out = rd / "dispatches.jsonl"
    lines = [json.dumps(r) for r in rows]
    out.write_text(
        "\n".join(lines) + ("\n" if lines else ""),
        encoding="utf-8",
    )
    return out


def write_verify_result(rd: Path, payload: dict) -> Path:
    out = rd / "verify_result.json"
    out.write_text(json.dumps(payload), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Step 3 logic — mirrored from
#   bundled/keeper/prompts/subagent/keeper_summarize_step3.md
# (the prompt's save block).  Reads learning_candidates.json (Step 2's
# output) + parsed_scope.json (for language detection) and emits
# learnings_to_emit.json.
# ---------------------------------------------------------------------------

_TEMPLATES_EN = {
    "R1": "Dispatch failure at step '{step}': {note}",
    "R2": "Edited '{file}' matches deny pattern '{deny_pattern}' — extract helper outside denied tree.",
    "R3": "Verify command exited fail: {reason} (cmd: {command}).",
    "R4": "New {marker} marker added in diff: {line_excerpt}",
    "R5": "{failed_count} dispatch step(s) failed: {steps}",
}
_TEMPLATES_KO = {
    "R1": "디스패치 실패 ({step}): {note}",
    "R2": "'{file}' 편집이 deny 패턴 '{deny_pattern}'에 매칭됨 — denied 영역 바깥으로 helper 분리 권장.",
    "R3": "검증 명령 fail: {reason} (cmd: {command}).",
    "R4": "diff에 새 {marker} 마커 추가: {line_excerpt}",
    "R5": "{failed_count}개 디스패치 단계 실패: {steps}",
}


def _render_summary(rule_id: str, evidence: dict, language: str) -> str:
    templates = _TEMPLATES_KO if language == "ko" else _TEMPLATES_EN
    fallback_note = "(메모 없음)" if language == "ko" else "(no note)"
    tmpl = templates.get(rule_id)
    if tmpl is None:
        return f"[{rule_id}] (no template registered)"
    if rule_id == "R1":
        note = evidence.get("note") or fallback_note
        text = tmpl.format(step=evidence.get("step", ""), note=note)
    elif rule_id == "R2":
        text = tmpl.format(
            file=evidence.get("file", ""),
            deny_pattern=evidence.get("deny_pattern", ""),
        )
    elif rule_id == "R3":
        text = tmpl.format(
            reason=evidence.get("reason", ""),
            command=evidence.get("command", ""),
        )
    elif rule_id == "R4":
        text = tmpl.format(
            marker=evidence.get("marker", ""),
            line_excerpt=evidence.get("line_excerpt", ""),
        )
    elif rule_id == "R5":
        steps = (evidence.get("steps", []) or [])[:3]
        text = tmpl.format(
            failed_count=evidence.get("failed_count", 0), steps=steps,
        )
    else:
        text = f"[{rule_id}] (unhandled)"
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    if len(text) > 200:
        text = text[:197] + "…"
    return text


def write_learnings_to_emit(rd: Path) -> Path:
    """Replay Step 3 logic: read learning_candidates.json + parsed_scope.json,
    emit learnings_to_emit.json.
    """
    candidates_path = rd / "learning_candidates.json"
    candidates_doc = json.loads(candidates_path.read_text(encoding="utf-8"))
    run_id = candidates_doc.get("run_id", "")
    candidates = candidates_doc.get("candidates", []) or []

    # Language detection (Hangul scan over task_summary).
    language = "en"
    scope_path = rd / "parsed_scope.json"
    if scope_path.exists():
        try:
            scope = json.loads(scope_path.read_text(encoding="utf-8"))
            ts = scope.get("task_summary", "") or ""
            if any(0xAC00 <= ord(ch) <= 0xD7A3 for ch in ts):
                language = "ko"
        except (json.JSONDecodeError, OSError):
            pass

    entries = []
    for cand in candidates:
        rule_id = cand.get("rule_id", "")
        category = cand.get("category", "")
        evidence = cand.get("evidence", {}) or {}
        evidence_hash = cand.get("evidence_hash", "")
        summary = _render_summary(rule_id, evidence, language)
        entries.append({
            "rule_id": rule_id,
            "category": category,
            "summary": summary,
            "evidence": evidence,
            "evidence_hash": evidence_hash,
        })

    out = rd / "learnings_to_emit.json"
    out.write_text(
        json.dumps(
            {"run_id": run_id, "language": language, "entries": entries},
            indent=2, sort_keys=True, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return out


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------

def run_extract_rules(
    rd: Path,
    *,
    cwd: Path | None = None,
    isolated_home: Path | None = None,
) -> subprocess.CompletedProcess:
    """Invoke extract_rules.py as a subprocess.

    ``cwd`` controls the working directory the script's R4 git probe runs
    against. Tests that exercise R4 should pass a real git fixture repo;
    tests that don't care can pass any non-git path so R4 returns [].
    """
    env = {**os.environ, "PYTHONPATH": str(ASSEMBLE_ROOT)}
    if isolated_home is not None:
        env["ASSEMBLE_HOME"] = str(isolated_home)
    return subprocess.run(
        [sys.executable, str(EXTRACT_RULES), str(rd)],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd is not None else None,
        env=env,
    )


def run_ledger_update(
    rd: Path,
    *,
    isolated_home: Path,
) -> subprocess.CompletedProcess:
    """Invoke ledger_update.py as a subprocess.

    ASSEMBLE_HOME is mandatory — the script writes to the global ledger
    under ``$ASSEMBLE_HOME/.claude/channels/assemble/learnings.jsonl``.
    """
    env = {
        **os.environ,
        "PYTHONPATH": str(ASSEMBLE_ROOT),
        "ASSEMBLE_HOME": str(isolated_home),
    }
    return subprocess.run(
        [sys.executable, str(LEDGER_UPDATE), str(rd)],
        capture_output=True,
        text=True,
        env=env,
    )


def ledger_lines(isolated_home: Path) -> list[dict]:
    """Read the global ledger as a list of dicts (one per row).
    Returns ``[]`` if the file is missing — pre-first-write state.
    """
    path = (
        isolated_home
        / ".claude" / "channels" / "assemble" / "learnings.jsonl"
    )
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# ---------------------------------------------------------------------------
# Git fixture helper for R4
# ---------------------------------------------------------------------------

def make_git_repo_with_todo(repo: Path) -> None:
    """Create a real two-commit git repo where the second commit adds a
    line containing TODO. R4's ``git diff HEAD~..HEAD`` will see exactly
    one added marker line.
    """
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True,
    )
    (repo / "f.py").write_text(
        "def hello():\n    return 1\n", encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial"], cwd=repo, check=True,
    )
    (repo / "f.py").write_text(
        "def hello():\n    return 1\n    # TODO: clean this up\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "add marker"], cwd=repo, check=True,
    )


# ---------------------------------------------------------------------------
# 1. Clean path — audit-skipped, ledger unchanged
# ---------------------------------------------------------------------------

def test_clean_path_audit_clean_no_ledger_change(
    run_dir, isolated_home, tmp_path
):
    """Step 1 verdict = audit-skipped (parsed_scope only, no other bundle
    artifacts). Pipeline still runs, but ledger_update writes the
    KEEPER_REPORT_ABORT variant (4 sections) and the global ledger file
    is never created.
    """
    write_parsed_scope(run_dir)
    write_audit_inventory(
        run_dir,
        run_id="run-clean",
        verdict="audit-skipped",
        skip_reason="no bundle artifacts present in run_dir",
    )

    non_git = tmp_path / "non-git"
    non_git.mkdir()

    p1 = run_extract_rules(run_dir, cwd=non_git, isolated_home=isolated_home)
    assert p1.returncode == 0, p1.stderr
    candidates = json.loads(
        (run_dir / "learning_candidates.json").read_text(encoding="utf-8")
    )
    assert candidates["candidates"] == []

    write_learnings_to_emit(run_dir)
    p2 = run_ledger_update(run_dir, isolated_home=isolated_home)
    assert p2.returncode == 0, p2.stderr

    report = (run_dir / "KEEPER_REPORT.md").read_text(encoding="utf-8")
    assert "ABORTED" in report
    assert "audit-skipped" in report
    # Abort variant — exactly 4 H2 sections.
    assert report.count("\n## ") == 4

    # Ledger NOT touched (file does not exist).
    ledger_path = (
        isolated_home
        / ".claude" / "channels" / "assemble" / "learnings.jsonl"
    )
    assert not ledger_path.exists()


# ---------------------------------------------------------------------------
# 2. R2 — scope deviation seeded
# ---------------------------------------------------------------------------

def test_scope_deviation_seeded_R2_emits_one_entry(
    run_dir, isolated_home, tmp_path
):
    """parsed_scope.deny lists an object-form entry overlapping
    audit_inventory.git_diff_files → R2 fires once. Ledger gains exactly
    one row whose category is ``scope-deviation``.
    """
    write_parsed_scope(
        run_dir,
        deny=[{"path": "src/auth.py", "note": "core auth code"}],
    )
    write_audit_inventory(
        run_dir,
        run_id="run-r2",
        bundles_observed=["reviewer"],
        artifacts_present={
            "parsed_scope.json": True,
            "REVIEW_REPORT.md": True,
        },
        git_diff_files=["src/auth.py"],
    )

    non_git = tmp_path / "non-git"
    non_git.mkdir()

    p1 = run_extract_rules(run_dir, cwd=non_git, isolated_home=isolated_home)
    assert p1.returncode == 0, p1.stderr
    cands = json.loads(
        (run_dir / "learning_candidates.json").read_text(encoding="utf-8")
    )["candidates"]
    r2 = [c for c in cands if c["rule_id"] == "R2"]
    assert len(r2) == 1

    write_learnings_to_emit(run_dir)
    p2 = run_ledger_update(run_dir, isolated_home=isolated_home)
    assert p2.returncode == 0, p2.stderr

    rows = ledger_lines(isolated_home)
    assert len(rows) == 1
    assert rows[0]["rule_id"] == "R2"
    assert rows[0]["category"] == "scope-deviation"

    report = (run_dir / "KEEPER_REPORT.md").read_text(encoding="utf-8")
    # Happy variant — exactly 7 H2 sections.
    assert report.count("\n## ") == 7
    assert "audit-flagged" in report


# ---------------------------------------------------------------------------
# 3. R3 — verify_result.verdict == fail
# ---------------------------------------------------------------------------

def test_verify_fail_seeded_R3_emits_entry(run_dir, isolated_home, tmp_path):
    """verify_result.verdict == "fail" → R3 fires once. Ledger +1 row,
    category ``ac-failure``.
    """
    write_parsed_scope(run_dir)
    write_audit_inventory(
        run_dir,
        run_id="run-r3",
        bundles_observed=["verifier"],
        artifacts_present={
            "parsed_scope.json": True,
            "verify_result.json": True,
        },
    )
    write_verify_result(
        run_dir,
        {
            "verdict": "fail",
            "command_executed": "pytest -q",
            "reason": "exit 1 — 3 failures",
        },
    )

    non_git = tmp_path / "non-git"
    non_git.mkdir()

    p1 = run_extract_rules(run_dir, cwd=non_git, isolated_home=isolated_home)
    assert p1.returncode == 0, p1.stderr
    write_learnings_to_emit(run_dir)
    p2 = run_ledger_update(run_dir, isolated_home=isolated_home)
    assert p2.returncode == 0, p2.stderr

    rows = ledger_lines(isolated_home)
    assert len(rows) == 1
    assert rows[0]["rule_id"] == "R3"
    assert rows[0]["category"] == "ac-failure"


# ---------------------------------------------------------------------------
# 4. R5 — dispatch failure aggregate
# ---------------------------------------------------------------------------

def test_dispatch_failure_seeded_R5_aggregates(
    run_dir, isolated_home, tmp_path
):
    """3 failed dispatch rows → R1 fires 3x (per-row) + R5 once
    (aggregate). Ledger should grow by 4 rows (3 R1 + 1 R5) — but the
    spec for this test is "R5 aggregates". Verify both: R5 entry count
    is 1, R1 entry count is 3.
    """
    write_parsed_scope(run_dir)
    write_audit_inventory(
        run_dir,
        run_id="run-r5",
        bundles_observed=["dispatch-traces"],
        artifacts_present={
            "parsed_scope.json": True,
            "dispatches.jsonl": True,
        },
    )
    write_dispatches(run_dir, [
        {"step": "step1", "subagent_type": "general-purpose",
         "status": "failed", "note": "boom"},
        {"step": "step2", "subagent_type": "general-purpose",
         "status": "failed", "note": "kapow"},
        {"step": "step3", "subagent_type": "general-purpose",
         "status": "failed", "note": "splat"},
    ])

    non_git = tmp_path / "non-git"
    non_git.mkdir()

    p1 = run_extract_rules(run_dir, cwd=non_git, isolated_home=isolated_home)
    assert p1.returncode == 0, p1.stderr
    write_learnings_to_emit(run_dir)
    p2 = run_ledger_update(run_dir, isolated_home=isolated_home)
    assert p2.returncode == 0, p2.stderr

    rows = ledger_lines(isolated_home)
    r1_rows = [r for r in rows if r["rule_id"] == "R1"]
    r5_rows = [r for r in rows if r["rule_id"] == "R5"]
    assert len(r1_rows) == 3
    assert len(r5_rows) == 1, "R5 must aggregate (single row, not per-row)"
    assert r5_rows[0]["category"] == "dispatch-failure"
    # R5 evidence lists all 3 failed steps.
    assert r5_rows[0]["evidence"]["failed_count"] == 3


# ---------------------------------------------------------------------------
# 5. R4 — TODO leakage (real git fixture)
# ---------------------------------------------------------------------------

def test_todo_leakage_seeded_R4_emits_entry(
    run_dir, isolated_home, tmp_path
):
    """Use a real git fixture: init + commit + add-TODO commit. R4's
    ``git diff --unified=0 HEAD~..HEAD`` probe sees exactly one added
    line containing TODO → R4 fires once. Ledger +1 row, category
    ``todo-leakage``.
    """
    write_parsed_scope(run_dir)
    write_audit_inventory(
        run_dir,
        run_id="run-r4",
        bundles_observed=["dispatch-traces"],
        artifacts_present={
            "parsed_scope.json": True,
            "dispatches.jsonl": True,
        },
    )

    repo = tmp_path / "fixture-repo"
    repo.mkdir()
    make_git_repo_with_todo(repo)

    p1 = run_extract_rules(run_dir, cwd=repo, isolated_home=isolated_home)
    assert p1.returncode == 0, p1.stderr
    write_learnings_to_emit(run_dir)
    p2 = run_ledger_update(run_dir, isolated_home=isolated_home)
    assert p2.returncode == 0, p2.stderr

    rows = ledger_lines(isolated_home)
    r4_rows = [r for r in rows if r["rule_id"] == "R4"]
    assert len(r4_rows) >= 1
    assert r4_rows[0]["category"] == "todo-leakage"
    assert r4_rows[0]["evidence"]["marker"] == "TODO"


# ---------------------------------------------------------------------------
# 6. All 5 rules combined — multi-rule combo
# ---------------------------------------------------------------------------

def test_multiple_rules_fire_combo(run_dir, isolated_home, tmp_path):
    """Seed conditions for all 5 rules simultaneously. Pipeline emits
    ≥ 5 ledger rows: at least one of each R1-R5 category fires.

    R1 + R5 combo: 1 failed dispatch row → 1 R1 + 1 R5 (aggregate of 1).
    R2: 1 deny match.
    R3: verify_result fail.
    R4: real git repo with one TODO addition.
    """
    write_parsed_scope(
        run_dir,
        deny=[{"path": "src/auth.py", "note": "auth"}],
    )
    write_audit_inventory(
        run_dir,
        run_id="run-combo",
        bundles_observed=["reviewer", "verifier", "dispatch-traces"],
        artifacts_present={
            "parsed_scope.json": True,
            "REVIEW_REPORT.md": True,
            "verify_result.json": True,
            "dispatches.jsonl": True,
        },
        git_diff_files=["src/auth.py"],
    )
    write_dispatches(run_dir, [
        {"step": "step.x", "subagent_type": "general-purpose",
         "status": "failed", "note": "boom"},
    ])
    write_verify_result(
        run_dir,
        {
            "verdict": "fail",
            "command_executed": "pytest -q",
            "reason": "exit 1",
        },
    )

    repo = tmp_path / "fixture-repo"
    repo.mkdir()
    make_git_repo_with_todo(repo)

    p1 = run_extract_rules(run_dir, cwd=repo, isolated_home=isolated_home)
    assert p1.returncode == 0, p1.stderr
    write_learnings_to_emit(run_dir)
    p2 = run_ledger_update(run_dir, isolated_home=isolated_home)
    assert p2.returncode == 0, p2.stderr

    rows = ledger_lines(isolated_home)
    rule_ids = {r["rule_id"] for r in rows}
    # All 5 rules must have fired at least once.
    assert {"R1", "R2", "R3", "R4", "R5"}.issubset(rule_ids), (
        f"missing rules; got {sorted(rule_ids)}"
    )
    # Total entries ≥ 5.
    assert len(rows) >= 5
