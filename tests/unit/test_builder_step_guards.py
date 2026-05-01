"""Spike V Phase B — step-specific guard assertions for builder prompts."""
from pathlib import Path

ASSEMBLE = Path.home() / ".claude/skills/assemble"
SUBAGENT = ASSEMBLE / "bundled/builder/prompts/subagent"


def _read(name: str) -> str:
    return (SUBAGENT / name).read_text()


def test_test_step3_exit_nonzero_guard():
    """test_step3.md must ERROR when test_first.sh exits 0 (already passing)."""
    text = _read("test_step3.md")
    assert "ERROR: test already passes" in text


def test_test_step3_no_implementation():
    """test_step3.md must not own implementation — Step 4 does."""
    text = _read("test_step3.md")
    assert "Step 4 owns implementation" in text or "Do NOT begin implementation" in text


def test_impl_step4_scope_creep_guard():
    """impl_step4.md must ERROR when patch touches file not in allow-list."""
    text = _read("impl_step4.md")
    assert "ERROR: scope creep" in text


def test_impl_step4_no_test_run():
    """impl_step4.md must not run tests — Step 5 owns verification."""
    text = _read("impl_step4.md")
    assert "Step 5 owns verification" in text or "Do NOT run tests" in text


def test_verify_step5_exit0_guard():
    """verify_step5.md must ERROR when verifier exits non-zero."""
    text = _read("verify_step5.md")
    assert "ERROR: verifier failed" in text


def test_verify_step5_behavioral_cue():
    """verify_step5.md must prefer behavioral over static checks."""
    text = _read("verify_step5.md")
    assert "behavioral" in text


def test_review_step6_scope_diff_mention():
    """review_step6.md must reference SCOPE comparison (Allow list / Deny list)."""
    text = _read("review_step6.md")
    assert "Allow list" in text or "allow-list" in text.lower()
    assert "Deny list" in text or "deny-list" in text.lower()


def test_review_step6_no_auto_fix():
    """review_step6.md must NOT auto-fix violations — report only."""
    text = _read("review_step6.md")
    assert "do NOT auto-fix" in text or "Report violations" in text or "not auto-fix" in text.lower()
