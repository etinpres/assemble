"""Spike VI B1 — reviewer ★ bundle inventory contract."""
from pathlib import Path

import yaml

ASSEMBLE = Path.home() / ".claude/skills/assemble"
REVIEWER = ASSEMBLE / "bundled/reviewer"


def test_reviewer_skill_md_exists():
    skill = REVIEWER / "SKILL.md"
    assert skill.exists(), f"missing {skill.relative_to(ASSEMBLE)}"


def test_reviewer_skill_frontmatter_declares_review_stage():
    skill = REVIEWER / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    assert text.startswith("---\n"), "no frontmatter delimiter"
    end = text.find("\n---", 4)
    fm = yaml.safe_load(text[4:end + 1])
    assert fm.get("name") == "reviewer"
    stages = fm.get("stages") or []
    assert "review" in stages, f"reviewer must declare stages: [review], got {stages}"


def test_reviewer_in_harness_bundles():
    """harness.py _BUNDLES tuple includes 'reviewer' for prompt path resolution."""
    from server import harness

    bundles = getattr(harness, "_BUNDLES", None)
    assert bundles is not None, "harness._BUNDLES tuple missing"
    assert "reviewer" in bundles, f"reviewer not in _BUNDLES: {bundles}"


def test_reviewer_subagent_dir_exists():
    d = REVIEWER / "prompts/subagent"
    assert d.is_dir(), f"missing {d.relative_to(ASSEMBLE)}"


def test_reviewer_orchestrator_dir_exists():
    d = REVIEWER / "prompts/orchestrator"
    assert d.is_dir(), f"missing {d.relative_to(ASSEMBLE)}"


def test_reviewer_templates_dir_exists():
    d = REVIEWER / "templates"
    assert d.is_dir(), f"missing {d.relative_to(ASSEMBLE)}"
