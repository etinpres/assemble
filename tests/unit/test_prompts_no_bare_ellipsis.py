"""Phase C1 guard — no bare `...` line inside a triple-quoted save-block
body. Bare ellipsis is fragile sentinel; replace with `<TBD: ...>`."""

import re
from pathlib import Path

PROMPTS_DIR = (
    Path.home() / ".claude/skills/assemble/bundled/plan-pack/prompts"
)

# Match a triple-quoted block, then check each interior line.
# Regex catches whitespace-padded `...`, dash-prefixed `- ...`, and
# bullet-prefixed `* ...` — all common bare-sentinel forms a contributor
# might re-introduce inside a save-block list.
TRIPLE_QUOTED_RE = re.compile(r'"""(.*?)"""', re.DOTALL)
BARE_ELLIPSIS_LINE_RE = re.compile(r"^\s*[-*]?\s*\.\.\.\s*$")


def _all_prompts() -> list[Path]:
    return list(PROMPTS_DIR.rglob("*.md"))


def test_no_bare_ellipsis_in_save_blocks():
    offenders = []
    for path in _all_prompts():
        text = path.read_text(encoding="utf-8")
        for m in TRIPLE_QUOTED_RE.finditer(text):
            block = m.group(1)
            for lineno, line in enumerate(block.splitlines(), start=1):
                if BARE_ELLIPSIS_LINE_RE.match(line):
                    offenders.append(f"{path.name}: bare `...` in triple-quoted block")
                    break
    assert not offenders, "\n".join(offenders)
