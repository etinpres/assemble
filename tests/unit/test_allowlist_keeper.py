"""Phase D1 — keeper ★ subagent prompts join `ALLOWED_PROMPT_FILES`.

After Spike X Phase D1, the four keeper subagent prompts (audit/extract/
summarize/ledger) are dispatchable through the same allowlist gate as
every other ★ bundle. The orchestrator helper `keeper_iter_revisit.md`
is NOT in this list — it's covered by D2 (`ORCHESTRATOR_ONLY_PROMPTS`).
"""

import pytest

import server
import server.harness as h


KEEPER_SUBAGENT_PROMPTS = (
    "keeper_audit_step1.md",
    "keeper_extract_step2.md",
    "keeper_summarize_step3.md",
    "keeper_ledger_step4.md",
)


def test_keeper_4_prompts_in_allowlist():
    """All four keeper subagent prompts MUST be in `ALLOWED_PROMPT_FILES`."""
    for prompt in KEEPER_SUBAGENT_PROMPTS:
        assert prompt in server.ALLOWED_PROMPT_FILES, (
            f"keeper prompt {prompt!r} missing from ALLOWED_PROMPT_FILES"
        )


def test_keeper_audit_step1_dispatchable():
    """`dispatch_prompt(keeper_audit_step1.md)` resolves without raising."""
    out = server.dispatch_prompt("keeper_audit_step1.md")
    assert isinstance(out, str)
    assert len(out) > 0


def test_keeper_extract_step2_dispatchable():
    out = server.dispatch_prompt("keeper_extract_step2.md")
    assert isinstance(out, str)
    assert len(out) > 0


def test_keeper_summarize_step3_dispatchable():
    out = server.dispatch_prompt("keeper_summarize_step3.md")
    assert isinstance(out, str)
    assert len(out) > 0


def test_keeper_ledger_step4_dispatchable():
    out = server.dispatch_prompt("keeper_ledger_step4.md")
    assert isinstance(out, str)
    assert len(out) > 0


def test_unknown_keeper_prompt_rejected():
    """Bogus keeper-named prompts still hit the allowlist gate."""
    with pytest.raises(ValueError, match=r"prompt_file.*not allowed"):
        server.dispatch_prompt("keeper_nonexistent.md")
