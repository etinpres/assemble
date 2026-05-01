"""Spike V Phase B — every {{KEY}} in builder templates appears as a
.replace("{{KEY}}", ...) in some builder prompt file.
Mirrors test_debugger_template_placeholder_match.py; skip until 6 prompts exist."""
import re
from pathlib import Path

import pytest

ASSEMBLE = Path.home() / ".claude/skills/assemble"
TEMPLATES_DIR = ASSEMBLE / "bundled/builder/templates"
PROMPTS_DIR = ASSEMBLE / "bundled/builder/prompts"

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")
REPLACE_LITERAL_RE = re.compile(r'\.replace\(\s*["\'](\{\{[A-Z_]+\}\})["\']\s*,')


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


def test_builder_templates_all_replaced():
    subagent_prompts = list((PROMPTS_DIR / "subagent").glob("*.md"))
    if len(subagent_prompts) < 6:
        pytest.skip(
            f"only {len(subagent_prompts)} of 6 sub-agent prompts exist yet "
            "— placeholder coverage becomes a contract at full bundle completion"
        )
    missing = _all_template_placeholders() - _all_prompt_replaces()
    assert not missing, (
        f"builder template placeholders never replaced: {sorted(missing)}"
    )
