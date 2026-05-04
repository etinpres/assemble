# tests/unit/test_run_dir_path.py
import os
from pathlib import Path
import pytest
from server.run_dir import run_dir_path


def test_returns_absolute_path_under_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    p = run_dir_path("20260504-test-abcd")
    expected = tmp_path / ".claude/channels/assemble/runs/20260504-test-abcd"
    assert p == expected
    # path is absolute even though run dir is not yet created
    assert p.is_absolute()


def test_does_not_create_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    p = run_dir_path("20260504-test-abcd")
    assert not p.exists()


@pytest.mark.parametrize("bad", ["", "..", ".", "with/slash", "with\\back",
                                  ".hidden", "a/b/c"])
def test_rejects_unsafe_run_id(bad, monkeypatch, tmp_path):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    with pytest.raises(ValueError, match="unsafe run_id"):
        run_dir_path(bad)


def test_accepts_normal_run_id(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    # canonical assemble run_id formats
    for rid in ["20260504-spikevii-b12", "20260501-133444-035a",
                "abc123", "x-y-z"]:
        p = run_dir_path(rid)
        assert p.name == rid
