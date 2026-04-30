"""Phase C2 guard — every sub-agent prompt's first paragraph contains the
exact 'Print `WROTE: <absolute path>`' phrase so the wording matches the
actual print(f'WROTE: {path}') mechanism."""

from pathlib import Path

PROMPTS = Path.home() / ".claude/skills/assemble/bundled/plan-pack/prompts"

SUBAGENT_FILES = [
    "prd_step2.md", "prd_step3.md", "prd_step4.md",
    "arch_step8.md", "adr_step11.md", "ui_step13.md",
    "cross_doc_step9.md",
]

CANONICAL = "Print `WROTE: <absolute path>`"


def _resolve(name: str) -> Path:
    """Find the file in flat or subagent/ subdir (post-C6)."""
    for sub in ("subagent", ""):
        p = PROMPTS / sub / name if sub else PROMPTS / name
        if p.exists():
            return p
    raise FileNotFoundError(name)


def test_every_subagent_prompt_carries_canonical_phrase():
    misses = []
    for name in SUBAGENT_FILES:
        text = _resolve(name).read_text(encoding="utf-8")
        # Must appear before the "## Inputs" or "## Required" heading
        head = text.split("## ")[0]
        if CANONICAL not in head:
            misses.append(f"{name}: missing canonical phrase in first paragraph")
    assert not misses, "\n".join(misses)
