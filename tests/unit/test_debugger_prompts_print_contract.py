"""Phase C guard — every debugger sub-agent prompt's first paragraph
contains the canonical 'Print `WROTE: <absolute path>`' sentence.

Mirrors Spike III §C2 / tests/unit/test_prompts_print_contract.py."""

from pathlib import Path

ASSEMBLE = Path.home() / ".claude/skills/assemble"
SUBAGENT_DIR = ASSEMBLE / "bundled/debugger/prompts/subagent"

CANONICAL = "Print `WROTE: <absolute path>`"


def test_every_debugger_subagent_prompt_has_print_contract():
    missing: list[str] = []
    for prompt in SUBAGENT_DIR.glob("*.md"):
        # Skip placeholder .gitkeep files
        if prompt.name == ".gitkeep":
            continue
        first_para = prompt.read_text().split("\n\n", 1)[0]
        if CANONICAL not in first_para:
            missing.append(prompt.name)
    assert not missing, (
        f"debugger sub-agent prompts missing canonical print contract: "
        f"{missing}\nExpected first paragraph to contain: {CANONICAL!r}"
    )
