"""Spike V Phase B — builder SKILL.md structural guards."""
from pathlib import Path

ASSEMBLE = Path.home() / ".claude/skills/assemble"
SKILL = ASSEMBLE / "bundled/builder/SKILL.md"
SUBAGENT_DIR = ASSEMBLE / "bundled/builder/prompts/subagent"
ORCHESTRATOR_DIR = ASSEMBLE / "bundled/builder/prompts/orchestrator"


def test_builder_allowlist_size_7():
    """SKILL.md anti-bypass section must reference 7-file allowlist."""
    text = SKILL.read_text()
    # Count distinct .md filenames mentioned in the allowlist block
    import re
    names = re.findall(r"`([a-z0-9_]+\.md)`", text)
    builder_names = {
        "scope_step2.md", "test_step3.md", "impl_step4.md",
        "verify_step5.md", "review_step6.md", "report_step7.md",
        "builder_iter_revisit.md",
    }
    found = set(names) & builder_names
    assert len(found) == 7, (
        f"SKILL.md allowlist should reference 7 builder files, found {len(found)}: {found}"
    )


def test_builder_skill_md_not_stub():
    """SKILL.md must not be the B1 stub."""
    text = SKILL.read_text()
    assert "[STUB" not in text, "SKILL.md is still the B1 stub — replace with full content"
