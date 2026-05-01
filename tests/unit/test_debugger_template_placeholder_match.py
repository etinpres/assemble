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
    """If no prompt files exist yet, the test passes trivially.
    The assertion gains teeth as C3-C7 add prompt files with
    `.replace("{{KEY}}", ...)` literals."""
    if not list(PROMPTS_DIR.rglob("*.md")):
        # Empty dir — no prompts exist yet (C2 baseline). Skip with a
        # visible reason so future contributors reading `pytest -rs`
        # output see why the assertion isn't running. Gains teeth as
        # C3-C7 add prompt files with `.replace(...)` literals.
        pytest.skip(
            "debugger prompts/ has no .md files yet — assertion "
            "gains teeth as C3-C7 add prompt files"
        )
    missing = _all_template_placeholders() - _all_prompt_replaces()
    assert not missing, (
        f"debugger template placeholders never replaced: {sorted(missing)}"
    )
