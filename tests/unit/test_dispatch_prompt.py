"""Phase B guard — server.dispatch_prompt enforces allowlist + substitutes
all placeholders + wraps with harness preamble."""

import os
import pytest
from pathlib import Path

import server
import server.harness as h


ASSEMBLE = Path.home() / ".claude/skills/assemble"


def test_allowed_prompt_files_is_eight():
    # 7 sub-agent + 1 orchestrator-facing iter_emphasis
    assert len(server.ALLOWED_PROMPT_FILES) == 8
    expected = {
        "prd_step2.md", "prd_step3.md", "prd_step4.md",
        "arch_step8.md", "adr_step11.md", "ui_step13.md",
        "cross_doc_step9.md", "iter_emphasis.md",
    }
    assert set(server.ALLOWED_PROMPT_FILES) == expected


def test_dispatch_prompt_unknown_file_raises():
    with pytest.raises(ValueError, match=r"prompt_file.*not allowed"):
        server.dispatch_prompt("evil.md", RUN_ID="x", TASK="y")


def test_dispatch_prompt_substitutes_all_placeholders():
    out = server.dispatch_prompt(
        "prd_step2.md",
        RUN_ID="r1",
        TASK="build a thing",
        INTERVIEW_ANSWERS="Q1 ... Q8 ...",
    )
    # Harness preamble must be prepended (rule 7 is the canonical sentinel).
    # Real rule 7: "다른 스킬의 인프라 코드(...) read·grep 금지" — match the
    # distinctive trailing phrase that uniquely identifies rule 7.
    assert "read·grep 금지" in out
    # All declared placeholders substituted
    assert "{{RUN_ID}}" not in out
    assert "{{TASK}}" not in out
    assert "{{INTERVIEW_ANSWERS}}" not in out
    # User content lands in the body
    assert "build a thing" in out
    assert "r1" in out


def test_dispatch_prompt_unknown_placeholder_raises():
    """Typo in caller surfaces immediately, not at sub-agent runtime."""
    with pytest.raises(KeyError, match=r"BOGUS"):
        server.dispatch_prompt(
            "prd_step2.md",
            RUN_ID="r1",
            TASK="t",
            INTERVIEW_ANSWERS="a",
            BOGUS="x",
        )


def test_record_dispatch_strict_mode_rejects_unknown_prompt_file(
    tmp_path, monkeypatch
):
    """ASSEMBLE_DISPATCH_STRICT=1 turns soft-warn into ValueError."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    monkeypatch.setenv("ASSEMBLE_DISPATCH_STRICT", "1")
    with pytest.raises(ValueError, match=r"§CRITICAL"):
        h.record_dispatch(
            "rid1", "step.x", "wrapped prompt",
            subagent_type="general-purpose",
            prompt_file="evil.md",
        )


def test_record_dispatch_soft_warn_default(tmp_path, monkeypatch, capsys):
    """Default mode (no strict env) only warns to stderr, does not raise."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    monkeypatch.delenv("ASSEMBLE_DISPATCH_STRICT", raising=False)
    out_path = h.record_dispatch(
        "rid1", "step.x", "wrapped prompt",
        subagent_type="general-purpose",
        prompt_file="evil.md",
    )
    assert out_path.exists()
    captured = capsys.readouterr()
    assert "evil.md" in captured.err
    assert "ALLOWED_PROMPT_FILES" in captured.err
