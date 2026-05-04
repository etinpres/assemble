"""Unit tests for `bundled/keeper/scripts/ledger_update.py`
(V4 Spike X, Tasks B5+B7).

The script imports `server.learnings` (the SOLE allowed `server.*` import
for Step 4) so tests run with PYTHONPATH set to the assemble repo root —
matching the production invocation contract (sub-agent runs from
``~/.claude/skills/assemble/``).

Filesystem isolation: every test seeds artifacts under tmp_path/run_dir
and uses ASSEMBLE_HOME monkeypatching to redirect the ledger jsonl.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Module loading — script lives outside the importable `server.*` tree.
# We import it as a stand-alone module by file path so tests can call its
# helpers directly (rather than only via subprocess).
# ---------------------------------------------------------------------------

ASSEMBLE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ASSEMBLE_ROOT / "bundled" / "keeper" / "scripts" / "ledger_update.py"
)


def _load_module():
    # Ensure server.learnings is importable for the script's `from
    # server.learnings import ...` line.
    if str(ASSEMBLE_ROOT) not in sys.path:
        sys.path.insert(0, str(ASSEMBLE_ROOT))
    spec = importlib.util.spec_from_file_location(
        "keeper_ledger_update", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def ledger_update():
    return _load_module()


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _seed_audit_inventory(
    run_dir: Path,
    *,
    run_id: str = "run-test",
    verdict: str = "audit-ready",
    skip_reason: str | None = None,
    git_diff_files: list[str] | None = None,
) -> None:
    inv = {
        "run_id": run_id,
        "verdict": verdict,
        "bundles_observed": ["reviewer"] if verdict == "audit-ready" else [],
        "artifacts_present": {
            "parsed_scope.json": True,
            "REVIEW_REPORT.md": verdict == "audit-ready",
        },
        "dispatch_row_count": 0,
        "verdicts_collected": (
            {"reviewer": "merge-ready"} if verdict == "audit-ready" else {}
        ),
        "git_probes": {
            "clean_tree": True,
            "dirty_files": [],
            "head_sha": "abc123def4567890",
            "branch": "master",
            "git_diff_files": git_diff_files or [],
        },
        "scope_summary": "test scope",
        "errors": [],
    }
    if skip_reason is not None:
        inv["skip_reason"] = skip_reason
    (run_dir / "audit_inventory.json").write_text(
        json.dumps(inv, sort_keys=True), encoding="utf-8"
    )


def _seed_learnings_to_emit(
    run_dir: Path,
    *,
    run_id: str = "run-test",
    entries: list[dict] | None = None,
    language: str = "en",
) -> None:
    doc = {
        "run_id": run_id,
        "language": language,
        "entries": entries or [],
    }
    (run_dir / "learnings_to_emit.json").write_text(
        json.dumps(doc, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )


def _make_entry(
    rule_id: str = "R3",
    category: str = "ac-failure",
    summary: str = "Verify command exited fail.",
    evidence_hash: str = "deadbeef" * 8,  # 64 hex chars
    evidence: dict | None = None,
) -> dict:
    return {
        "rule_id": rule_id,
        "category": category,
        "summary": summary,
        "evidence_hash": evidence_hash,
        "evidence": evidence or {"command": "pytest -q", "reason": "fail"},
    }


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """Redirect `~/.claude/...` to tmp_path so the ledger writes go to
    a sandbox per test. server.learnings honors ASSEMBLE_HOME the same
    way server.run_dir does.
    """
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# 1 — missing learnings_to_emit.json → exit 1
# ---------------------------------------------------------------------------

def test_missing_learnings_to_emit_exits_1(tmp_path, isolated_home):
    """Script must exit 1 + emit no WROTE line when Step 3's artifact
    is absent. Step 3 is REQUIRED upstream.
    """
    _seed_audit_inventory(tmp_path)
    # No learnings_to_emit.json
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(tmp_path)],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(ASSEMBLE_ROOT),
             "ASSEMBLE_HOME": str(isolated_home)},
    )
    assert proc.returncode == 1
    assert "WROTE:" not in proc.stdout
    assert "learnings_to_emit.json" in proc.stderr


# ---------------------------------------------------------------------------
# 2 — missing audit_inventory.json → exit 1
# ---------------------------------------------------------------------------

def test_missing_audit_inventory_exits_1(tmp_path, isolated_home):
    """Script must exit 1 + emit no WROTE line when Step 1's artifact
    is absent. Step 1 is REQUIRED upstream.
    """
    _seed_learnings_to_emit(tmp_path)
    # No audit_inventory.json
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(tmp_path)],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(ASSEMBLE_ROOT),
             "ASSEMBLE_HOME": str(isolated_home)},
    )
    assert proc.returncode == 1
    assert "WROTE:" not in proc.stdout
    assert "audit_inventory.json" in proc.stderr


# ---------------------------------------------------------------------------
# 3 — empty entries writes audit-clean report
# ---------------------------------------------------------------------------

def test_empty_entries_writes_audit_clean_report(
    ledger_update, tmp_path, isolated_home
):
    """Step 3 wrote zero entries (Step 2 found no candidates) — Step 4
    must still produce a happy-variant KEEPER_REPORT.md with verdict
    `audit-clean`. Ledger is read+pruned+written but unchanged.
    """
    _seed_audit_inventory(tmp_path)
    _seed_learnings_to_emit(tmp_path, entries=[])

    out = ledger_update.update_ledger_and_report(tmp_path)
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "audit-clean" in body
    assert "Verdict**: audit-clean" in body
    # Happy variant — 7 H2 sections.
    assert body.count("\n## ") == 7


# ---------------------------------------------------------------------------
# 4 — one entry appended → audit-flagged report + ledger row
# ---------------------------------------------------------------------------

def test_one_entry_appended_and_summarized(
    ledger_update, tmp_path, isolated_home
):
    """One entry from Step 3 → ledger gains one row, KEEPER_REPORT
    shows verdict `audit-flagged` and the entry's summary.
    """
    _seed_audit_inventory(tmp_path)
    _seed_learnings_to_emit(
        tmp_path,
        entries=[_make_entry(summary="Verify command exited fail: boom")],
    )

    out = ledger_update.update_ledger_and_report(tmp_path)
    body = out.read_text(encoding="utf-8")
    assert "audit-flagged" in body
    assert "Verify command exited fail: boom" in body

    # Ledger now has exactly one entry.
    ledger_path = isolated_home / ".claude" / "channels" / "assemble" / "learnings.jsonl"
    assert ledger_path.exists()
    lines = [l for l in ledger_path.read_text().splitlines() if l.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["rule_id"] == "R3"
    assert row["category"] == "ac-failure"
    assert "ts" in row and row["ts"]
    assert row["run_id"] == "run-test"


# ---------------------------------------------------------------------------
# 5 — audit-skipped uses abort template (4 sections)
# ---------------------------------------------------------------------------

def test_audit_skipped_writes_abort_template(
    ledger_update, tmp_path, isolated_home
):
    """audit_inventory.verdict == "audit-skipped" → 4-section abort
    KEEPER_REPORT, ledger NOT touched.
    """
    _seed_audit_inventory(
        tmp_path,
        verdict="audit-skipped",
        skip_reason="parsed_scope.json not readable",
    )
    _seed_learnings_to_emit(tmp_path, entries=[])

    out = ledger_update.update_ledger_and_report(tmp_path)
    body = out.read_text(encoding="utf-8")
    assert "audit-skipped" in body
    assert "ABORTED" in body  # title stamp
    # Abort variant — 4 H2 sections.
    assert body.count("\n## ") == 4

    # Ledger should NOT have been touched on the abort path.
    ledger_path = isolated_home / ".claude" / "channels" / "assemble" / "learnings.jsonl"
    assert not ledger_path.exists(), (
        "ledger must NOT be written on the abort path"
    )


# ---------------------------------------------------------------------------
# 6 — ledger byte count grows by N
# ---------------------------------------------------------------------------

def test_ledger_byte_count_grows_by_n(
    ledger_update, tmp_path, isolated_home
):
    """N entries → ledger grows by N rows (each row a separate jsonl line)."""
    _seed_audit_inventory(tmp_path)
    entries = [
        _make_entry(rule_id="R1", category="rule-violation",
                    evidence_hash="aa" * 32,
                    evidence={"step": "s1", "note": "n1"}),
        _make_entry(rule_id="R2", category="scope-deviation",
                    evidence_hash="bb" * 32,
                    evidence={"file": "auth.py", "deny_pattern": "auth/*"}),
        _make_entry(rule_id="R3", category="ac-failure",
                    evidence_hash="cc" * 32),
    ]
    _seed_learnings_to_emit(tmp_path, entries=entries)

    ledger_update.update_ledger_and_report(tmp_path)
    ledger_path = isolated_home / ".claude" / "channels" / "assemble" / "learnings.jsonl"
    lines = [l for l in ledger_path.read_text().splitlines() if l.strip()]
    assert len(lines) == 3


# ---------------------------------------------------------------------------
# 7 — dedup collapses repeat evidence_hash
# ---------------------------------------------------------------------------

def test_dedup_collapses_repeat_evidence_hash(
    ledger_update, tmp_path, isolated_home
):
    """Seed an existing ledger with a row carrying evidence_hash X. New
    entry from Step 3 carries the same X. After Step 4: ledger still has
    one row for X (newest wins).
    """
    # Pre-seed ledger with an old row carrying the same evidence_hash.
    ledger_dir = isolated_home / ".claude" / "channels" / "assemble"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = ledger_dir / "learnings.jsonl"
    old_ts = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    old_row = {
        "ts": old_ts,
        "run_id": "run-old",
        "rule_id": "R3",
        "category": "ac-failure",
        "summary": "old summary",
        "evidence_hash": "ee" * 32,
        "evidence": {"command": "old", "reason": "old"},
    }
    ledger_path.write_text(json.dumps(old_row) + "\n", encoding="utf-8")

    # Now seed Step 3 with an entry carrying the same evidence_hash.
    _seed_audit_inventory(tmp_path)
    _seed_learnings_to_emit(
        tmp_path,
        entries=[_make_entry(
            summary="new summary",
            evidence_hash="ee" * 32,
        )],
    )
    ledger_update.update_ledger_and_report(tmp_path)

    lines = [l for l in ledger_path.read_text().splitlines() if l.strip()]
    assert len(lines) == 1, (
        f"dedup should have collapsed to 1 row, got {len(lines)}"
    )
    row = json.loads(lines[0])
    assert row["summary"] == "new summary", (
        "dedup must keep the newer row (by ts)"
    )


# ---------------------------------------------------------------------------
# 8 — cap evicts oldest
# ---------------------------------------------------------------------------

def test_cap_evicts_oldest(ledger_update, tmp_path, isolated_home):
    """Seed ledger with 99 entries, append 5 new → after FIFO cap (100),
    final count is 100 (NOT 104). Oldest 4 evicted.
    """
    ledger_dir = isolated_home / ".claude" / "channels" / "assemble"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = ledger_dir / "learnings.jsonl"
    base = datetime.now(timezone.utc) - timedelta(days=1)
    rows = []
    for i in range(99):
        rows.append({
            "ts": (base + timedelta(seconds=i)).isoformat(),
            "run_id": f"old-{i}",
            "rule_id": "R1",
            "category": "rule-violation",
            "summary": f"summary {i}",
            "evidence_hash": f"{i:064d}",  # unique 64-char hash
            "evidence": {"i": i},
        })
    ledger_path.write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )

    _seed_audit_inventory(tmp_path)
    new_entries = [
        _make_entry(rule_id="R1", category="rule-violation",
                    evidence_hash=f"new{j:061d}",  # 64 chars
                    evidence={"j": j})
        for j in range(5)
    ]
    _seed_learnings_to_emit(tmp_path, entries=new_entries)

    ledger_update.update_ledger_and_report(tmp_path)
    lines = [l for l in ledger_path.read_text().splitlines() if l.strip()]
    assert len(lines) == 100, f"FIFO cap → 100, got {len(lines)}"


# ---------------------------------------------------------------------------
# 9 — skiplist drops matching evidence_hash
# ---------------------------------------------------------------------------

def test_skiplist_drops_matching_evidence_hash(
    ledger_update, tmp_path, isolated_home
):
    """User adds an evidence_hash to learnings.skip. Step 4's prune drops
    any matching entry — even brand-new ones from this run.
    """
    skip_dir = isolated_home / ".claude" / "channels" / "assemble"
    skip_dir.mkdir(parents=True, exist_ok=True)
    skip_path = skip_dir / "learnings.skip"
    skipped_hash = "ff" * 32
    skip_path.write_text(f"# user veto\n{skipped_hash}\n", encoding="utf-8")

    _seed_audit_inventory(tmp_path)
    _seed_learnings_to_emit(
        tmp_path,
        entries=[
            _make_entry(rule_id="R1", evidence_hash=skipped_hash,
                        evidence={"step": "skipped"}),
            _make_entry(rule_id="R2", evidence_hash="aa" * 32,
                        evidence={"file": "kept.py", "deny_pattern": "*.py"}),
        ],
    )
    ledger_update.update_ledger_and_report(tmp_path)

    ledger_path = skip_dir / "learnings.jsonl"
    lines = [l for l in ledger_path.read_text().splitlines() if l.strip()]
    hashes = [json.loads(l)["evidence_hash"] for l in lines]
    assert skipped_hash not in hashes, (
        "skiplisted evidence_hash must be dropped during prune"
    )
    assert "aa" * 32 in hashes, "non-skipped entry must survive"


# ---------------------------------------------------------------------------
# 10 — KEEPER_REPORT 7 H2 sections on happy path
# ---------------------------------------------------------------------------

def test_keeper_report_7_h2_sections_on_happy_path(
    ledger_update, tmp_path, isolated_home
):
    _seed_audit_inventory(tmp_path)
    _seed_learnings_to_emit(tmp_path, entries=[_make_entry()])
    out = ledger_update.update_ledger_and_report(tmp_path)
    body = out.read_text(encoding="utf-8")
    h2_count = sum(1 for line in body.splitlines() if line.startswith("## "))
    assert h2_count == 7


# ---------------------------------------------------------------------------
# 11 — KEEPER_REPORT 4 H2 sections on abort
# ---------------------------------------------------------------------------

def test_keeper_report_4_h2_sections_on_abort(
    ledger_update, tmp_path, isolated_home
):
    _seed_audit_inventory(
        tmp_path, verdict="audit-skipped",
        skip_reason="no bundle artifacts present in run_dir",
    )
    _seed_learnings_to_emit(tmp_path, entries=[])
    out = ledger_update.update_ledger_and_report(tmp_path)
    body = out.read_text(encoding="utf-8")
    h2_count = sum(1 for line in body.splitlines() if line.startswith("## "))
    assert h2_count == 4


# ---------------------------------------------------------------------------
# 12 — all placeholders substituted (no `{{` left in output)
# ---------------------------------------------------------------------------

def test_all_placeholders_substituted(
    ledger_update, tmp_path, isolated_home
):
    """Every `{{...}}` placeholder must be substituted by ledger_update —
    a leftover token implies a bug in the substitution map.
    """
    _seed_audit_inventory(tmp_path)
    _seed_learnings_to_emit(tmp_path, entries=[_make_entry()])
    out = ledger_update.update_ledger_and_report(tmp_path)
    body = out.read_text(encoding="utf-8")
    assert "{{" not in body, (
        "rendered KEEPER_REPORT must not contain `{{` placeholder tokens — "
        "all placeholders must be substituted"
    )

    # Same on the abort path.
    abort_dir = tmp_path / "abort_run"
    abort_dir.mkdir()
    _seed_audit_inventory(
        abort_dir, verdict="audit-skipped", skip_reason="missing scope",
    )
    _seed_learnings_to_emit(abort_dir, entries=[])
    out_abort = ledger_update.update_ledger_and_report(abort_dir)
    abort_body = out_abort.read_text(encoding="utf-8")
    assert "{{" not in abort_body


# ---------------------------------------------------------------------------
# 13 — idempotent when run twice with same `now`
# ---------------------------------------------------------------------------

def test_idempotent_when_run_twice_with_same_now(
    ledger_update, tmp_path, isolated_home
):
    """Two runs of the script with identical inputs + identical `now`
    produce the same ledger byte count: the second run's identical
    entries dedupe against the first run's fresh appends.
    """
    _seed_audit_inventory(tmp_path)
    entries = [
        _make_entry(rule_id="R3", evidence_hash="11" * 32),
        _make_entry(rule_id="R1", evidence_hash="22" * 32,
                    category="rule-violation",
                    evidence={"step": "s1", "note": "n1"}),
    ]
    _seed_learnings_to_emit(tmp_path, entries=entries)

    fixed_now = datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)
    ledger_update.update_ledger_and_report(tmp_path, now=fixed_now)
    ledger_path = isolated_home / ".claude" / "channels" / "assemble" / "learnings.jsonl"
    bytes_after_run1 = ledger_path.read_bytes()

    ledger_update.update_ledger_and_report(tmp_path, now=fixed_now)
    bytes_after_run2 = ledger_path.read_bytes()

    assert bytes_after_run1 == bytes_after_run2, (
        "ledger must be byte-identical after running twice with same `now` — "
        "dedup absorbs the second run's identical entries"
    )
