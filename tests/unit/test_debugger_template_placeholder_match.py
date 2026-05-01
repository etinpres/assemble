"""Phase C guard — every {{...}} in debugger templates appears as a
literal .replace("{{...}}", ...) call in some debugger prompt file.

Mirrors tests/unit/test_prd_template_placeholder_match.py (Spike III
A1) but scans across all 3 debugger templates."""

import re
from pathlib import Path

import pytest

ASSEMBLE = Path.home() / ".claude/skills/assemble"
TEMPLATES_DIR = ASSEMBLE / "bundled/debugger/templates"
PROMPTS_DIR = ASSEMBLE / "bundled/debugger/prompts"

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")
REPLACE_LITERAL_RE = re.compile(
    r'\.replace\(\s*["\'](\{\{[A-Z_]+\}\})["\']\s*,'
)


def _all_template_placeholders() -> set[str]:
    out: set[str] = set()
    for tmpl in TEMPLATES_DIR.glob("*.template"):
        out |= set(PLACEHOLDER_RE.findall(tmpl.read_text()))
    return out


def _all_prompt_replaces() -> set[str]:
    out: set[str] = set()
    for prompt in PROMPTS_DIR.rglob("*.md"):
        out |= set(REPLACE_LITERAL_RE.findall(prompt.read_text()))
    return out


def test_debugger_templates_all_replaced():
    """Once all 6 sub-agent prompts exist (C7+), every {{KEY}} in
    templates must appear as a `.replace(...)` literal somewhere.
    Until then, the test skip-passes — incremental coverage only
    becomes a contract at full bundle completion."""
    SUBAGENT_PROMPTS = list((PROMPTS_DIR / "subagent").glob("*.md"))
    if len(SUBAGENT_PROMPTS) < 5:
        pytest.skip(
            f"only {len(SUBAGENT_PROMPTS)} of 5 sub-agent prompts exist "
            "yet — placeholder coverage gains teeth at C7"
        )
    missing = _all_template_placeholders() - _all_prompt_replaces()
    assert not missing, (
        f"debugger template placeholders never replaced: {sorted(missing)}"
    )
