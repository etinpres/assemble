"""Spike V Phase B — every builder sub-agent prompt's first paragraph
contains the canonical 'Print `WROTE: <absolute path>`' sentence.
Mirrors test_debugger_prompts_print_contract.py."""
from pathlib import Path

ASSEMBLE = Path.home() / ".claude/skills/assemble"
SUBAGENT_DIR = ASSEMBLE / "bundled/builder/prompts/subagent"
CANONICAL = "Print `WROTE: <absolute path>`"


def test_every_builder_subagent_prompt_has_print_contract():
    prompts = [p for p in SUBAGENT_DIR.glob("*.md") if p.name != ".gitkeep"]
    if not prompts:
        import pytest; pytest.skip("no builder sub-agent prompts yet")
    missing = [
        p.name for p in prompts
        if CANONICAL not in p.read_text().split("\n\n", 1)[0]
    ]
    assert not missing, (
        f"builder sub-agent prompts missing canonical print contract: {missing}"
    )
