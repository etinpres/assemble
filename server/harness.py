"""Harness-preamble prepend helper.

Bundled SKILLs prepend a fixed 4-rule "harness preamble" to every dispatched
sub-agent prompt so subagents inherit the rules even when they cannot read
the SKILL.md text. The preamble lives at
`~/.claude/skills/assemble/bundled/_shared/harness-preamble.md` and is
loaded once per process (lru_cache).
"""

import os
import sys
from functools import lru_cache
from pathlib import Path


_PREAMBLE_REL = ".claude/skills/assemble/bundled/_shared/harness-preamble.md"


def _preamble_path() -> Path:
    base = Path(os.environ.get("ASSEMBLE_HOME", str(Path.home())))
    return base / _PREAMBLE_REL


@lru_cache(maxsize=1)
def _load_preamble() -> str | None:
    p = _preamble_path()
    if not p.exists():
        print(f"[harness] missing preamble at {p}; "
              "wrap_with_preamble will return prompts unchanged.",
              file=sys.stderr)
        return None
    return p.read_text().rstrip() + "\n"


def wrap_with_preamble(prompt: str) -> str:
    """Return `prompt` wrapped so the harness preamble runs before it.

    Format:
        <preamble>

        [TASK]
        <prompt>

    If the preamble file is missing, the prompt is returned unchanged and a
    one-line warning is printed to stderr (no exception — bundled SKILLs
    should still function in degraded mode).
    """
    pre = _load_preamble()
    if pre is None:
        return prompt
    return f"{pre}\n[TASK]\n{prompt}"
