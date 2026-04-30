import json
import threading

import pytest

from server.run_dir import (
    write_run_artifact,
    read_run_artifact,
    run_artifact_path,
    strip_bash_fence,
)


def test_write_creates_file_and_returns_path(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    p = write_run_artifact("20260428-000000-abcd", "PRD.md", "# hello\n")
    assert p.exists()
    assert p.read_text() == "# hello\n"
    expected = tmp_path / ".claude/channels/assemble/runs/20260428-000000-abcd/PRD.md"
    assert p == expected


def test_write_creates_missing_run_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    # No mkdir up front — helper must create the run dir itself.
    p = write_run_artifact("20260428-111111-aaaa", "PRD.md", "# x\n")
    assert p.parent.is_dir()


def test_run_artifact_path_does_not_create_anything(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    p = run_artifact_path("20260428-222222-bbbb", "PRD.md")
    assert not p.exists()
    assert not p.parent.exists()


def test_read_returns_none_for_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    assert read_run_artifact("nope", "PRD.md") is None


def test_read_returns_content_after_write(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    write_run_artifact("rid", "PRD.md", "body")
    assert read_run_artifact("rid", "PRD.md") == "body"


# --- path-traversal guards (B-1 retroactive review C1) ---

@pytest.mark.parametrize("bad_filename", [
    "/tmp/evil",                # absolute path
    "../evil",                  # parent traversal
    "../../etc/passwd",         # deeper traversal
    "subdir/file.md",           # nested filename
    ".hidden",                  # leading dot
    "",                         # empty
])
def test_rejects_unsafe_filename(tmp_path, monkeypatch, bad_filename):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    with pytest.raises(ValueError):
        write_run_artifact("rid", bad_filename, "x")


@pytest.mark.parametrize("bad_run_id", [
    "/tmp/evil",
    "../evil",
    "../../",
    "sub/dir",
    ".hidden-rid",
    "",
])
def test_rejects_unsafe_run_id(tmp_path, monkeypatch, bad_run_id):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    with pytest.raises(ValueError):
        write_run_artifact(bad_run_id, "PRD.md", "x")


def test_run_artifact_path_also_validates(tmp_path, monkeypatch):
    """Validation happens at path construction, not just at write time —
    so callers can't sneak past by computing the path themselves."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    with pytest.raises(ValueError):
        run_artifact_path("rid", "../evil")


# --- AC fence strip (B-1 retroactive review I1) ---

def test_strip_bash_fence_raw_command():
    assert strip_bash_fence("ls -la") == "ls -la"


def test_strip_bash_fence_with_bash_tag():
    assert strip_bash_fence("```bash\nls -la\n```") == "ls -la"


def test_strip_bash_fence_no_lang_tag():
    assert strip_bash_fence("```\nls -la\n```") == "ls -la"


def test_strip_bash_fence_with_trailing_newline():
    assert strip_bash_fence("```bash\nls -la\n```\n") == "ls -la"


def test_strip_bash_fence_with_surrounding_whitespace():
    assert strip_bash_fence("  ```bash\n  ls -la\n```  ") == "ls -la"


def test_concurrent_writes_dont_corrupt(tmp_path, monkeypatch):
    """Two threads writing the same artifact must yield exactly one of the
    two payloads — never a mid-write garble. Atomic-via-rename guarantees this.
    """
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    rid = "concurrent"
    payloads = ["A" * 4096, "B" * 4096]
    errors: list[Exception] = []

    def worker(content: str):
        try:
            write_run_artifact(rid, "PRD.md", content)
        except Exception as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(c,)) for c in payloads]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    final = read_run_artifact(rid, "PRD.md")
    assert final in payloads, f"got mid-write garble: {final!r}"


def test_update_iteration_state_creates_new_file(tmp_path, monkeypatch):
    """Spike II F15: 첫 호출 시 파일 신규 생성 + index=0."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    from server import update_iteration_state
    rid = "20260501-newfile"
    path = update_iteration_state(rid, {"resolved_pct": 0.5, "new_count": 1})
    assert path.exists()
    state = json.loads(path.read_text())
    assert state["iterations"] == [{"index": 0, "resolved_pct": 0.5, "new_count": 1}]


def test_update_iteration_state_appends_to_existing(tmp_path, monkeypatch):
    """기존 파일에 append + index auto-increment."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    from server import update_iteration_state
    rid = "20260501-append"
    update_iteration_state(rid, {"resolved_pct": 0.7})
    update_iteration_state(rid, {"resolved_pct": 0.85})
    path = update_iteration_state(rid, {"resolved_pct": 0.9, "stopped": True})
    state = json.loads(path.read_text())
    assert len(state["iterations"]) == 3
    assert state["iterations"][0]["index"] == 0
    assert state["iterations"][1]["index"] == 1
    assert state["iterations"][2]["index"] == 2
    assert state["iterations"][2]["stopped"] is True


def test_update_iteration_state_corrupt_file_resets(tmp_path, monkeypatch):
    """깨진 JSON 파일이면 fresh start, raise 안 함."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    from server import update_iteration_state, run_artifact_path
    rid = "20260501-corrupt"
    p = run_artifact_path(rid, "iteration_state.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{not valid json")
    path = update_iteration_state(rid, {"new_count": 0})
    state = json.loads(path.read_text())
    assert state["iterations"] == [{"index": 0, "new_count": 0}]


def test_update_iteration_state_unsafe_run_id_rejected(tmp_path, monkeypatch):
    """run_dir validation 재사용 — path traversal 거절."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    from server import update_iteration_state
    import pytest
    with pytest.raises(ValueError):
        update_iteration_state("../../etc", {"x": 1})
