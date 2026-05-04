"""Spike VI B8 — reviewer SKILL.md narrative checks."""
from pathlib import Path

ASSEMBLE = Path.home() / ".claude/skills/assemble"
SKILL = ASSEMBLE / "bundled/reviewer/SKILL.md"


def test_skill_md_has_required_sections():
    text = SKILL.read_text(encoding="utf-8")
    required = [
        "## When to invoke",
        "## Inputs",
        "## Artifacts",
        "## Verdict logic",
        "## CRITICAL — orchestrator-only enforcement",
        "## Step-by-step workflow",
        "## Iteration audit invariant",
        "## Sub-agent matrix",
        "## Identity guards",
    ]
    missing = [s for s in required if s not in text]
    assert not missing, f"reviewer SKILL.md missing sections: {missing}"


def test_skill_md_lists_all_six_subagent_prompts():
    text = SKILL.read_text(encoding="utf-8")
    prompts = [
        "parse_scope_step1.md",
        "diff_collect_step2.md",
        "classify_files_step3.md",
        "rule3_check_step4.md",
        "severity_assess_step5.md",
        "reviewer_report_step6.md",
    ]
    missing = [p for p in prompts if p not in text]
    assert not missing, f"reviewer SKILL.md missing prompt names: {missing}"


def test_skill_md_step_workflow_section_lists_step_0_through_7():
    text = SKILL.read_text(encoding="utf-8")
    for i in range(8):
        assert f"### Step {i} —" in text, f"missing '### Step {i} —' in workflow"
