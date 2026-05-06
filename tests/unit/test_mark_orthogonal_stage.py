import json

import pytest

from server.progress import (
    VALID_ORTHOGONAL_STAGES,
    _progress_path,
    create_run,
    mark_orthogonal_stage,
    mark_stage,
)
from server.state_store import write_json_atomic


def test_mark_orthogonal_safety_creates_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    rid = create_run(task="t", sequence=["plan", "execute"])

    mark_orthogonal_stage(rid, "safety", "in_progress")
    body = json.loads(_progress_path(rid).read_text())
    assert "orthogonal_stages" in body
    assert "safety" in body["orthogonal_stages"]
    entry = body["orthogonal_stages"]["safety"]
    assert entry["status"] == "in_progress"
    assert entry["started_at"] is not None
    assert entry["ended_at"] is None
    # per spec: tool_used only stamped on TERMINAL_STATUS transitions
    assert entry["tool_used"] is None

    mark_orthogonal_stage(rid, "safety", "done", tool_used="guardian")
    body = json.loads(_progress_path(rid).read_text())
    entry = body["orthogonal_stages"]["safety"]
    assert entry["status"] == "done"
    assert entry["started_at"] is not None
    assert entry["ended_at"] is not None
    assert entry["tool_used"] == "guardian"


def test_mark_orthogonal_meta_creates_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    rid = create_run(task="t", sequence=["plan", "execute"])

    mark_orthogonal_stage(rid, "meta", "in_progress", tool_used="keeper")
    mark_orthogonal_stage(rid, "meta", "done", tool_used="keeper", notes="wrap-up")
    body = json.loads(_progress_path(rid).read_text())
    assert "meta" in body["orthogonal_stages"]
    entry = body["orthogonal_stages"]["meta"]
    assert entry["status"] == "done"
    assert entry["started_at"] is not None
    assert entry["ended_at"] is not None
    assert entry["tool_used"] == "keeper"
    assert entry["notes"] == "wrap-up"


def test_mark_orthogonal_unknown_stage_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    rid = create_run(task="t", sequence=["plan", "execute"])

    with pytest.raises(ValueError) as ei:
        mark_orthogonal_stage(rid, "foo", "done")
    msg = str(ei.value)
    assert "orthogonal stage must be one of" in msg
    # VALID_ORTHOGONAL_STAGES set members must appear in the error text
    for s in VALID_ORTHOGONAL_STAGES:
        assert s in msg


def test_mark_stage_safety_auto_routes_to_orthogonal(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    rid = create_run(task="t", sequence=["plan", "execute"])

    # Should NOT raise "stage not in sequence" — auto-route to orthogonal
    mark_stage(rid, "safety", "done", tool_used="guardian")

    body = json.loads(_progress_path(rid).read_text())
    assert "orthogonal_stages" in body
    assert "safety" in body["orthogonal_stages"]
    assert body["orthogonal_stages"]["safety"]["status"] == "done"
    assert body["orthogonal_stages"]["safety"]["tool_used"] == "guardian"
    # main sequence untouched
    assert [s["stage"] for s in body["stages"]] == ["plan", "execute"]
    assert body["stages"][0]["status"] == "pending"


def test_legacy_progress_json_without_orthogonal_field_loads_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    rid = create_run(task="t", sequence=["plan", "execute"])

    # Simulate a legacy progress.json (pre-Spike XIV) without orthogonal_stages
    path = _progress_path(rid)
    body = json.loads(path.read_text())
    body.pop("orthogonal_stages", None)
    write_json_atomic(path, body)
    assert "orthogonal_stages" not in json.loads(path.read_text())

    # Should not raise — _ensure_orthogonal_field auto-creates the field
    mark_orthogonal_stage(rid, "safety", "done", tool_used="guardian")

    body = json.loads(path.read_text())
    assert "orthogonal_stages" in body
    assert body["orthogonal_stages"]["safety"]["status"] == "done"


def test_mark_orthogonal_back_status_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    rid = create_run(task="t", sequence=["plan", "execute"])

    with pytest.raises(ValueError) as ei:
        mark_orthogonal_stage(rid, "safety", "back")
    assert "sequence-only" in str(ei.value)
