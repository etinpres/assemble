"""Spike V.1 §4 — update_dispatch_status() lifecycle guard.

`record_dispatch` writes a row at status='dispatched'. The new helper
`update_dispatch_status` flips that same row in-place to 'completed' or
'failed' once the orchestrator has parsed the sub-agent's WROTE/ERROR.
"""

import json

import pytest

import server
import server.harness as h


def _read_rows(run_id, tmp_path):
    path = tmp_path / ".claude/channels/assemble/runs" / run_id / "dispatches.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_update_status_flips_dispatched_to_completed(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    h.record_dispatch("rid1", "step2", "wrapped\n[TASK]\nbody",
                      subagent_type="general-purpose",
                      prompt_file="scope_step2.md")
    rows = _read_rows("rid1", tmp_path)
    assert len(rows) == 1
    assert rows[0]["status"] == "dispatched"

    server.update_dispatch_status("rid1", "step2", "completed",
                                  wrote_path="/tmp/output.md")
    rows = _read_rows("rid1", tmp_path)
    assert len(rows) == 1, "row count must stay 1 (in-place update, not append)"
    assert rows[0]["status"] == "completed"
    assert rows[0]["wrote_path"] == "/tmp/output.md"


def test_update_status_flips_dispatched_to_failed(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    h.record_dispatch("rid1", "step5", "wrapped\n[TASK]\nbody",
                      subagent_type="general-purpose",
                      prompt_file="verify_step5.md")
    server.update_dispatch_status("rid1", "step5", "failed",
                                  note="ERROR: verifier failed; rc=1")
    rows = _read_rows("rid1", tmp_path)
    assert rows[0]["status"] == "failed"
    assert "verifier failed" in rows[0]["note"]


def test_update_status_idempotent_when_no_dispatched_row(tmp_path, monkeypatch):
    """Calling update on a non-existent run_id should not raise."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    # No record_dispatch call — file doesn't exist
    path = server.update_dispatch_status("nonexistent_rid", "step2", "completed")
    assert not path.exists()  # file still doesn't exist


def test_update_status_idempotent_when_already_completed(tmp_path, monkeypatch):
    """Calling update twice should not double-flip or error."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    h.record_dispatch("rid1", "step2", "wrapped\n[TASK]\nbody",
                      subagent_type="general-purpose",
                      prompt_file="scope_step2.md")
    server.update_dispatch_status("rid1", "step2", "completed",
                                  wrote_path="/tmp/a.md")
    # Second call — no matching dispatched row remains
    server.update_dispatch_status("rid1", "step2", "completed",
                                  wrote_path="/tmp/b.md")
    rows = _read_rows("rid1", tmp_path)
    assert len(rows) == 1
    assert rows[0]["wrote_path"] == "/tmp/a.md", (
        "second update must be no-op; first wrote_path stays"
    )


def test_update_status_only_targets_matching_step(tmp_path, monkeypatch):
    """Multiple steps in one run — update only the named step."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    h.record_dispatch("rid1", "step2", "p1", subagent_type="x", prompt_file="scope_step2.md")
    h.record_dispatch("rid1", "step3", "p2", subagent_type="x", prompt_file="test_step3.md")
    h.record_dispatch("rid1", "step4", "p3", subagent_type="x", prompt_file="impl_step4.md")

    server.update_dispatch_status("rid1", "step3", "completed", wrote_path="/tmp/x.md")
    rows = _read_rows("rid1", tmp_path)

    assert rows[0]["step"] == "step2" and rows[0]["status"] == "dispatched"
    assert rows[1]["step"] == "step3" and rows[1]["status"] == "completed"
    assert rows[2]["step"] == "step4" and rows[2]["status"] == "dispatched"


def test_update_status_targets_last_dispatched_for_repeated_step(tmp_path, monkeypatch):
    """If a step was dispatched twice (retry pattern), update walks
    backwards and flips the most recent dispatched row only."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    h.record_dispatch("rid1", "step5", "first attempt", subagent_type="x", prompt_file="verify_step5.md")
    server.update_dispatch_status("rid1", "step5", "failed", note="retry needed")
    h.record_dispatch("rid1", "step5", "retry", subagent_type="x", prompt_file="verify_step5.md")

    server.update_dispatch_status("rid1", "step5", "completed", wrote_path="/tmp/ok.md")
    rows = _read_rows("rid1", tmp_path)

    assert len(rows) == 2
    assert rows[0]["status"] == "failed"
    assert rows[1]["status"] == "completed"


def test_update_status_rejects_initial_states():
    """new_status must be 'completed' or 'failed' — not 'dispatched'/'skipped'."""
    with pytest.raises(ValueError, match="not allowed for transition"):
        server.update_dispatch_status("rid1", "step2", "dispatched")
    with pytest.raises(ValueError, match="not allowed for transition"):
        server.update_dispatch_status("rid1", "step2", "skipped")


def test_record_dispatch_accepts_completed_status(tmp_path, monkeypatch):
    """Spike V.1 §4 also extended record_dispatch's allowed status set to
    include 'completed' — so that callers who construct rows directly
    (e.g. backfill scripts) can write completed rows."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    h.record_dispatch("rid1", "step2", "p", subagent_type="x",
                      prompt_file="scope_step2.md", status="completed")
    rows = _read_rows("rid1", tmp_path)
    assert rows[0]["status"] == "completed"
