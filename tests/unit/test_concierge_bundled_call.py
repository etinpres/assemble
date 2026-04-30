"""V3 Concierge SKILL.md must instruct main on how to invoke ★ bundled options.

Spike II F1: B-6 dogfood (run 20260430-120552-6aad) showed main calling
`Skill(plan-pack)` → `Unknown skill` error → Read fallback. Root cause:
SKILL.md §9 only said "the Skill tool actually invokes it", which doesn't
distinguish slash-skills from bundled bundles. This grep test pins the
explicit instruction so future edits don't regress.
"""

from pathlib import Path

SKILL_PATH = Path.home() / ".claude/skills/assemble/SKILL.md"


def test_v3_skill_md_documents_bundled_read_invocation():
    text = SKILL_PATH.read_text(encoding="utf-8")
    # Must contain the explicit Read-not-Skill instruction
    assert "★-prefixed bundled options are NOT slash-skill registry entries" in text
    assert "Read`" in text and "tool_path" in text
    # Must mention the actual error main hits without this guidance
    assert "Unknown skill" in text


def test_v3_skill_md_lazy_load_paragraph_intact():
    """Original §9 lazy-load paragraph must still be present (don't replace, append)."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert "build_stage_options()" in text
    assert "## 9. Internals: lazy-load policy" in text
