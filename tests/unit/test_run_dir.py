import threading
from pathlib import Path
from server.run_dir import write_run_artifact, read_run_artifact, run_artifact_path


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
