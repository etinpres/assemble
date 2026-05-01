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
