"""Phase B guard — server.dispatch_prompt enforces allowlist + load + wrap.

Post-B1 fix (option B): substitution removed from dispatch_prompt; the
caller (orchestrator) now owns placeholder substitution. See spec §1.2
(B2 option B) for rationale.
"""

import pytest
from pathlib import Path

import server
import server.harness as h


ASSEMBLE = Path.home() / ".claude/skills/assemble"


def test_allowed_prompt_files_size_matches_bundles():
    # plan-pack: 7 sub-agent + 1 orchestrator-facing iter_emphasis (8 files)
    # debugger ★: grows incrementally C3 → C7 (1 → 6 files)
    expected = {
        # plan-pack ★ (Spike I-III, 8 files)
        "prd_step2.md", "prd_step3.md", "prd_step4.md",
        "arch_step8.md", "adr_step11.md", "ui_step13.md",
        "cross_doc_step9.md", "iter_emphasis.md",
        # debugger ★ (Spike IV, C3+)
        "repro_step2.md",
        "hypothesis_step3.md",
        "root_cause_step4.md",
    }
    assert set(server.ALLOWED_PROMPT_FILES) == expected
    assert len(server.ALLOWED_PROMPT_FILES) == len(expected)


def test_dispatch_prompt_unknown_file_raises():
    with pytest.raises(ValueError, match=r"prompt_file.*not allowed"):
        server.dispatch_prompt("evil.md")


def test_dispatch_prompt_returns_wrapped_prompt_with_placeholders_intact():
    """option B: dispatch_prompt loads + wraps only. Substitution is the
    caller's responsibility — `{{KEY}}` tokens MUST survive intact so the
    caller can route them itself (orchestrator-only inputs vs. sub-agent's
    own .replace instructions). See spec §1.2 (B2 option B)."""
    out = server.dispatch_prompt("prd_step2.md")
    # Harness preamble must be prepended
    assert "read·grep 금지" in out
    # All declared placeholders must survive intact
    assert "{{RUN_ID}}" in out
    assert "{{TASK}}" in out
    assert "{{INTERVIEW_ANSWERS}}" in out
    # Body content from the on-disk prompt must be present
    assert "PRD body sub-agent" in out  # opening paragraph


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
