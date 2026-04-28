import importlib
from pathlib import Path

import pytest


def _reload_harness():
    """Force the lru_cache on _load_preamble() to drop after env edits."""
    import server.harness as h
    importlib.reload(h)
    return h


def _stub_preamble(home: Path, body: str):
    p = home / ".claude/skills/assemble/bundled/_shared/harness-preamble.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def test_wraps_with_preamble(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _stub_preamble(tmp_path, "[HARNESS]\n1. rule\n")
    h = _reload_harness()
    out = h.wrap_with_preamble("do the thing")
    assert "[HARNESS]" in out
    assert "1. rule" in out
    assert "[TASK]" in out
    assert "do the thing" in out
    # Preamble must come before [TASK]
    assert out.index("[HARNESS]") < out.index("[TASK]")
    assert out.index("[TASK]") < out.index("do the thing")


def test_empty_prompt_still_wraps(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _stub_preamble(tmp_path, "[HARNESS]\n1. rule\n")
    h = _reload_harness()
    out = h.wrap_with_preamble("")
    assert "[HARNESS]" in out
    assert "[TASK]" in out


def test_missing_preamble_returns_prompt_unchanged_with_warning(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    # Do NOT create the preamble file.
    h = _reload_harness()
    out = h.wrap_with_preamble("hello")
    assert out == "hello"
    err = capsys.readouterr().err
    assert "harness-preamble.md" in err


def test_preamble_loaded_once_per_process(tmp_path, monkeypatch):
    """The lru_cache on _load_preamble means changing the file mid-process
    has no effect — that's intentional (single source of truth per run)."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _stub_preamble(tmp_path, "[HARNESS]\nA\n")
    h = _reload_harness()
    first = h.wrap_with_preamble("x")
    _stub_preamble(tmp_path, "[HARNESS]\nB\n")  # mutate on disk
    second = h.wrap_with_preamble("x")
    # Cached load means second still says "A"
    assert "A" in second
    assert "B" not in second
    assert first == second
