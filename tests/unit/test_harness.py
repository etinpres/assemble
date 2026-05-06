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
    has no effect — that's intentional (single source of truth per run).

    Spike XIV Phase A: ASSEMBLE_HOME is set so wrap_with_preamble injects
    a `[ENV]` line into the body. The cache invariant is checked against
    the *preamble portion* (split via _split_preamble_body) so the body's
    [ENV] line — which contains "sub-agent" with the letter 'B' — does
    not interfere with the "A" vs "B" preamble-content assertion.
    """
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _stub_preamble(tmp_path, "[HARNESS]\nA\n")
    h = _reload_harness()
    first = h.wrap_with_preamble("x")
    _stub_preamble(tmp_path, "[HARNESS]\nB\n")  # mutate on disk
    second = h.wrap_with_preamble("x")
    # Cached load means second's preamble still says "A"
    pre_first, _ = h._split_preamble_body(first)
    pre_second, _ = h._split_preamble_body(second)
    assert "A" in pre_second
    assert "B" not in pre_second
    assert pre_first == pre_second
    assert first == second


def test_wrap_format_is_pinned_exactly(tmp_path, monkeypatch):
    """The on-the-wire format `<preamble>\n\n[TASK]\n<body>` is part of the
    contract. Tasks 4–7 will call wrap_with_preamble from multiple workflow
    steps; if the format shifts silently, dispatched sub-agent prompts
    change in non-obvious ways. Pin the exact bytes here.

    Spike XIV Phase A: when ASSEMBLE_HOME is set, the body gains a leading
    `[ENV]` line. This test pins the exact bytes for the env-set path.
    """
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _stub_preamble(tmp_path, "[HARNESS]\n1. rule\n")
    h = _reload_harness()
    out = h.wrap_with_preamble("do the thing")
    expected_env_line = (
        f"[ENV] 이 dispatch는 ASSEMBLE_HOME={tmp_path} 환경에서 실행됨. "
        f"sub-agent가 server.* 모듈을 import 할 때 메인과 동일 home 보장. "
        f"코드에서 `os.environ['ASSEMBLE_HOME']` 또는 Path 조립 시 이 값 우선."
    )
    assert out == (
        f"[HARNESS]\n1. rule\n\n[TASK]\n{expected_env_line}\n\ndo the thing"
    )
