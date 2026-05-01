"""Phase C guard — no bare '...' line inside any debugger save-block
body (Spike III §C1 carryforward applied to the new bundle)."""

import re
from pathlib import Path

ASSEMBLE = Path.home() / ".claude/skills/assemble"
DEBUGGER_PROMPTS = ASSEMBLE / "bundled/debugger/prompts"

# Match a save block: ```python ... ```
SAVE_BLOCK_RE = re.compile(
    r"```python\n(.*?)\n```",
    re.DOTALL,
)
BARE_ELLIPSIS_LINE_RE = re.compile(r"^\s*\.\.\.\s*$", re.MULTILINE)


def test_no_bare_ellipsis_in_debugger_save_blocks():
    offenders: list[tuple[str, int]] = []
    for prompt in DEBUGGER_PROMPTS.rglob("*.md"):
        text = prompt.read_text()
        for match in SAVE_BLOCK_RE.finditer(text):
            body = match.group(1)
            for ell in BARE_ELLIPSIS_LINE_RE.finditer(body):
                line_no = text[: match.start() + match.group(0).find(ell.group(0))].count("\n") + 1
                offenders.append((str(prompt), line_no))
    assert not offenders, (
        "Bare '...' lines inside save blocks (use '<TBD: …>' instead):\n"
        + "\n".join(f"{p}:{ln}" for p, ln in offenders)
    )
