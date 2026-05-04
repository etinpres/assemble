"""Phase B guard — `dispatch_and_record` composes dispatch_prompt +
record_dispatch atomically so the orchestrator cannot elide the audit
row in the iter1 4-way path (B-8 carryforward A).

Status field also covers the (no change) skip path (B-8 carryforward
B): main records `status="skipped"` instead of dispatching."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

import server


@pytest.fixture
def tmp_assemble(tmp_path, monkeypatch):
    """Redirect ASSEMBLE_HOME so write paths land in tmp."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    runs = tmp_path / ".claude/channels/assemble/runs/test-rid"
    runs.mkdir(parents=True, exist_ok=True)
    return tmp_path, "test-rid"


def test_dispatched_path_calls_both(tmp_assemble):
    """Spike X Phase D4: dispatched path now routes through
    `wrap_with_preamble_and_learnings` (was `dispatch_prompt`) so the
    [PRIOR LEARNINGS] fence can be spliced in when the global ledger has
    stage-relevant entries. Mocks updated accordingly — `_resolve_prompt_path`
    is the new file-loader hook, `wrap_with_preamble_and_learnings` is the
    new wrap+learnings hook. Behavior contract unchanged: dispatched path
    returns the wrapped prompt and `record_dispatch` is called once."""
    _, rid = tmp_assemble
    fake_path = type("FakePath", (), {"read_text": lambda self, encoding="utf-8": "BODY"})()
    with patch("server.harness._resolve_prompt_path", return_value=fake_path) as rp, \
         patch(
             "server.harness.wrap_with_preamble_and_learnings",
             return_value="WRAPPED",
         ) as wp, \
         patch("server.harness.record_dispatch") as rd:
        out = server.dispatch_and_record(
            rid,
            prompt_file="iter_emphasis.md",
            step="step6.iter1.PRD",
            subagent_type="general-purpose",
            description="iter1 PRD redraft",
        )
    assert out == "WRAPPED"
    rp.assert_called_once_with("iter_emphasis.md")
    wp.assert_called_once()
    # wrap_with_preamble_and_learnings receives raw body + run_id + stage
    wp_args, wp_kwargs = wp.call_args.args, wp.call_args.kwargs
    assert wp_args[0] == "BODY"
    assert wp_kwargs["run_id"] == rid
    assert wp_kwargs["stage"] == "plan"  # iter_emphasis.md → plan
    rd.assert_called_once()
    rd_kwargs = rd.call_args.kwargs
    assert rd_kwargs["prompt_file"] == "iter_emphasis.md"
    assert rd_kwargs["status"] == "dispatched"


def test_skipped_path_does_not_call_dispatch_prompt(tmp_assemble):
    _, rid = tmp_assemble
    with patch("server.harness.dispatch_prompt") as dp, \
         patch("server.harness.record_dispatch") as rd:
        out = server.dispatch_and_record(
            rid,
            prompt_file="iter_emphasis.md",
            step="step6.iter1.ARCH",
            status="skipped",
            note="user emphasis: (no change)",
        )
    assert out == ""
    dp.assert_not_called()
    rd.assert_called_once()
    rd_kwargs = rd.call_args.kwargs
    assert rd_kwargs["status"] == "skipped"
    assert rd_kwargs["note"] == "user emphasis: (no change)"


def test_unknown_status_raises():
    with pytest.raises(ValueError, match="unknown status"):
        server.dispatch_and_record(
            "rid",
            prompt_file="iter_emphasis.md",
            step="step6.iter1.PRD",
            status="bogus",
        )


def test_record_includes_status_field_on_disk(tmp_assemble, monkeypatch):
    """End-to-end — call dispatch_and_record without mocks and check the
    on-disk dispatches.jsonl row carries the status field."""
    monkeypatch.setenv("ASSEMBLE_DISPATCH_STRICT", "0")
    tmp, rid = tmp_assemble
    server.dispatch_and_record(
        rid,
        prompt_file="iter_emphasis.md",
        step="step6.iter1.UI",
        status="skipped",
        note="(no change)",
    )
    log = tmp / ".claude/channels/assemble/runs" / rid / "dispatches.jsonl"
    rows = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "skipped"
    assert row["note"] == "(no change)"
    assert row["prompt_file"] == "iter_emphasis.md"


def test_record_default_status_is_dispatched(tmp_assemble, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_DISPATCH_STRICT", "0")
    tmp, rid = tmp_assemble
    # Call record_dispatch directly (no dispatch_and_record) to verify
    # the schema extension is also visible at the lower-level API.
    server.harness.record_dispatch(
        rid,
        step="step6.iter1.PRD",
        prompt_text="dummy body",
        prompt_file="iter_emphasis.md",
    )
    log = tmp / ".claude/channels/assemble/runs" / rid / "dispatches.jsonl"
    row = json.loads(log.read_text().splitlines()[0])
    assert row["status"] == "dispatched"
    assert row["note"] is None
