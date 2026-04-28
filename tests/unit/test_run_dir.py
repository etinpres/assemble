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
