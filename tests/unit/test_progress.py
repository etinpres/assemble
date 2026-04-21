from server.progress import (
    create_run, load_progress, mark_stage,
    list_runs, find_resumable,
)


def test_create_run_writes_skeleton(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    rid = create_run(task="iOS calculator", sequence=["plan","execute","ship"])
    assert rid.startswith("20")
    p = load_progress(rid)
    assert p["task"] == "iOS calculator"
    assert p["sequence"] == ["plan","execute","ship"]
    assert p["current_stage_index"] == 0
    assert [s["status"] for s in p["stages"]] == ["pending","pending","pending"]


def test_mark_stage_updates_status_and_index(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    rid = create_run(task="t", sequence=["plan","execute"])
    mark_stage(rid, "plan", status="done", tool_used="writing-plans")
    p = load_progress(rid)
    assert p["stages"][0]["status"] == "done"
    assert p["stages"][0]["tool_used"] == "writing-plans"
    assert p["current_stage_index"] == 1


def test_mark_stage_back_decrements_index(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    rid = create_run(task="t", sequence=["plan","design","execute"])
    mark_stage(rid, "plan", status="done", tool_used="writing-plans")
    mark_stage(rid, "design", status="back")
    p = load_progress(rid)
    assert p["current_stage_index"] == 0


def test_find_resumable_picks_latest_unfinished(tmp_path, monkeypatch):
    import time
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    r1 = create_run(task="a", sequence=["plan"])
    mark_stage(r1, "plan", status="done", tool_used="writing-plans")
    time.sleep(0.05)
    r2 = create_run(task="b", sequence=["plan","execute"])
    mark_stage(r2, "plan", status="done", tool_used="writing-plans")
    found = find_resumable()
    assert found == [r2]


def test_find_resumable_excludes_old_runs(tmp_path, monkeypatch):
    import os, time
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    rid = create_run(task="old", sequence=["plan","execute"])
    p = (tmp_path / ".claude/channels/assemble/runs" / rid / "progress.json")
    eight_days_ago = time.time() - 8 * 24 * 3600
    os.utime(p, (eight_days_ago, eight_days_ago))
    assert find_resumable() == []
