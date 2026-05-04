"""Phase D4 — `dispatch_and_record` routes through the new
`wrap_with_preamble_and_learnings` wrapper instead of `dispatch_prompt`.

Empty-ledger byte-equivalence is the regression-safety guarantee: a clean
machine with no `learnings.jsonl` MUST produce identical dispatches.jsonl
rows compared to the pre-Spike-X path.
"""

import hashlib
import json
from pathlib import Path

import pytest

import server
import server.harness as h
from server.harness import canonical_preamble_sha256, wrap_with_preamble


def _seed_ledger(tmp_path, entries):
    ledger = tmp_path / ".claude/channels/assemble/learnings.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return ledger


def _entry(rule_id="R1", category="scope-deviation",
           summary="default", ts="2026-05-04T12:00:00Z"):
    return {
        "ts": ts,
        "rule_id": rule_id,
        "category": category,
        "summary": summary,
        "evidence_hash": hashlib.sha256(
            (rule_id + summary).encode()
        ).hexdigest(),
    }


@pytest.fixture
def tmp_assemble(tmp_path, monkeypatch):
    """Stage real bundled tree under tmp ASSEMBLE_HOME via symlink so prompt
    resolution + canonical preamble work, but learnings.jsonl + runs/ stay
    isolated under tmp."""
    real_home = Path.home()
    bundled_link = tmp_path / ".claude/skills/assemble"
    bundled_link.parent.mkdir(parents=True, exist_ok=True)
    bundled_link.symlink_to(real_home / ".claude/skills/assemble")
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    h._CACHED_PREAMBLE.clear()
    runs = tmp_path / ".claude/channels/assemble/runs/test-rid"
    runs.mkdir(parents=True, exist_ok=True)
    yield tmp_path, "test-rid"
    h._CACHED_PREAMBLE.clear()


def test_dispatch_and_record_byte_equal_with_empty_ledger(tmp_assemble):
    """Empty ledger → dispatch_and_record returns the same wrapped text
    as `wrap_with_preamble(<raw body>)` (the pre-Spike-X path)."""
    _, rid = tmp_assemble
    out = server.dispatch_and_record(
        rid,
        prompt_file="iter_emphasis.md",
        step="step.empty",
        subagent_type="general-purpose",
    )
    # Load the body text directly to compute the expected wrap.
    body = h._resolve_prompt_path("iter_emphasis.md").read_text(encoding="utf-8")
    expected = wrap_with_preamble(body)
    assert out == expected


def test_dispatch_and_record_records_canonical_preamble_sha(tmp_assemble):
    """Both empty-ledger and non-empty-ledger paths produce a recorded
    preamble_sha256 == canonical_preamble_sha256."""
    tmp, rid = tmp_assemble
    canonical = canonical_preamble_sha256()
    # First: empty ledger
    server.dispatch_and_record(
        rid,
        prompt_file="iter_emphasis.md",
        step="step.empty",
        subagent_type="general-purpose",
    )
    # Then: seed and dispatch again
    _seed_ledger(tmp, [_entry()])
    server.dispatch_and_record(
        rid,
        prompt_file="iter_emphasis.md",
        step="step.with-learnings",
        subagent_type="general-purpose",
    )
    log = tmp / ".claude/channels/assemble/runs" / rid / "dispatches.jsonl"
    rows = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    assert len(rows) == 2
    for row in rows:
        assert row["preamble_sha256"] == canonical
    # Verify chain still green
    audit = server.verify_dispatches(rid)
    assert audit["ok"] is True


def test_dispatch_and_record_status_skipped_no_dispatch(tmp_assemble):
    """status='skipped' MUST NOT load the prompt file or invoke the wrapper —
    audit row only, no actual prompt text. Uses ASSEMBLE_DISPATCH_STRICT=0
    soft-warn for the prompt_file allowlist check at record time."""
    tmp, rid = tmp_assemble
    out = server.dispatch_and_record(
        rid,
        prompt_file="iter_emphasis.md",
        step="step.skipped",
        status="skipped",
        note="(no change)",
    )
    assert out == ""
    log = tmp / ".claude/channels/assemble/runs" / rid / "dispatches.jsonl"
    rows = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    assert rows[0]["status"] == "skipped"
    assert rows[0]["body_bytes"] == 0


def test_dispatch_and_record_status_failed_unchanged(tmp_assemble):
    """status='failed' is recorded the same way it was pre-Spike-X."""
    tmp, rid = tmp_assemble
    server.dispatch_and_record(
        rid,
        prompt_file="iter_emphasis.md",
        step="step.failed",
        status="failed",
        note="subagent ERROR'd",
    )
    log = tmp / ".claude/channels/assemble/runs" / rid / "dispatches.jsonl"
    rows = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    assert rows[0]["status"] == "failed"
    assert rows[0]["note"] == "subagent ERROR'd"


def test_dispatch_and_record_unknown_prompt_raises_valueerror(tmp_assemble):
    """The duplicated allowlist check inside dispatch_and_record (D4) MUST
    raise ValueError on unknown prompts — same contract as `dispatch_prompt`."""
    _, rid = tmp_assemble
    with pytest.raises(ValueError, match=r"prompt_file.*not allowed"):
        server.dispatch_and_record(
            rid,
            prompt_file="evil.md",
            step="step.x",
            subagent_type="general-purpose",
        )


def test_dispatch_and_record_with_non_empty_ledger_includes_fence(tmp_assemble):
    """Seed the ledger; iter_emphasis.md (plan stage) now ships with a
    [PRIOR LEARNINGS] fence as part of the body."""
    tmp, rid = tmp_assemble
    _seed_ledger(tmp, [_entry(
        rule_id="R9",
        category="scope-deviation",
        summary="Plan-stage learning",
    )])
    out = server.dispatch_and_record(
        rid,
        prompt_file="iter_emphasis.md",
        step="step.fenced",
        subagent_type="general-purpose",
    )
    assert "[PRIOR LEARNINGS — 우선 회피]" in out
    assert "(R9) Plan-stage learning" in out


def test_dispatch_and_record_unknown_stage_falls_back_gracefully(
    tmp_assemble, monkeypatch
):
    """If a prompt is in ALLOWED_PROMPT_FILES but missing from
    `_PROMPT_TO_STAGE` (forward-compat scenario — shouldn't happen in
    practice, enforced by `test_prompt_to_stage_covers_all_allowed`),
    the dispatch path still works: stage=None → wrap_with_preamble path,
    no fence injection."""
    tmp, rid = tmp_assemble
    # Temporarily delete a mapping
    saved = h._PROMPT_TO_STAGE.pop("iter_emphasis.md")
    try:
        _seed_ledger(tmp, [_entry()])
        out = server.dispatch_and_record(
            rid,
            prompt_file="iter_emphasis.md",
            step="step.unmapped",
            subagent_type="general-purpose",
        )
        # No fence (stage was None)
        assert "[PRIOR LEARNINGS" not in out
        body = h._resolve_prompt_path("iter_emphasis.md").read_text(encoding="utf-8")
        assert out == wrap_with_preamble(body)
    finally:
        h._PROMPT_TO_STAGE["iter_emphasis.md"] = saved


def test_existing_dispatch_chain_byte_compat(tmp_assemble):
    """End-to-end on the empty-ledger path: dispatched prompt text equals
    `wrap_with_preamble(text)`, recorded preamble matches canonical, and
    verify_dispatches is green. This pins the Spike X → pre-Spike-X
    byte-compat invariant for any test that previously exercised the
    `dispatch_prompt → record_dispatch` chain."""
    tmp, rid = tmp_assemble
    out = server.dispatch_and_record(
        rid,
        prompt_file="prd_step2.md",
        step="step.compat",
        subagent_type="general-purpose",
    )
    body = h._resolve_prompt_path("prd_step2.md").read_text(encoding="utf-8")
    assert out == wrap_with_preamble(body)
    audit = server.verify_dispatches(rid)
    assert audit["ok"] is True
