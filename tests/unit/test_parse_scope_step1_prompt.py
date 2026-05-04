"""B2 — parse_scope_step1.md body invariants.

Verifies that the reviewer Step 1 sub-agent prompt:
  1. imports the parse_scope_md helper instead of emitting inline parser logic
  2. no longer contains the old em-dash split rule
  3. documents the SCOPE.md grammar section
  4. documents the Korean+backtick freeform failure mode
  5. preserves the file identity (first non-blank line starts with '# reviewer Step 1')
  6. preserves the WROTE: discipline (orchestrator parsing contract)
  7. does NOT contain a ## Constraints section (removed in B2)
  8. did not rename the file (6 prompt files still present in the subagent dir)
"""

import re
from pathlib import Path

ASSEMBLE = Path.home() / ".claude/skills/assemble"
PROMPT_PATH = ASSEMBLE / "bundled/reviewer/prompts/subagent/parse_scope_step1.md"
SUBAGENT_DIR = ASSEMBLE / "bundled/reviewer/prompts/subagent"


def _body() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def test_prompt_imports_helper():
    """parse_scope_md helper import must appear in the prompt body."""
    body = _body()
    assert re.search(
        r"from server\.scope_parser import parse_scope_md", body
    ), "Expected 'from server.scope_parser import parse_scope_md' in prompt body"


def test_prompt_drops_inline_split_rule():
    """Old inline split logic (split … FIRST … —) must be absent."""
    body = _body()
    assert not re.search(
        r"split.*FIRST.*—", body, re.IGNORECASE
    ), "Old inline split rule should have been removed from prompt body"


def test_prompt_has_grammar_section():
    """## SCOPE.md grammar section must be present."""
    body = _body()
    assert "## SCOPE.md grammar" in body, (
        "Expected '## SCOPE.md grammar' section in prompt body"
    )


def test_prompt_has_korean_failure_mode_doc():
    """Grammar section must document the Korean+backtick failure mode."""
    body = _body()
    grammar_start = body.find("## SCOPE.md grammar")
    assert grammar_start != -1, "## SCOPE.md grammar section not found"
    grammar_section = body[grammar_start:]
    assert "한글" in grammar_section or "Korean" in grammar_section, (
        "Grammar section must reference Korean (한글 or 'Korean')"
    )
    assert "deny-entry" in grammar_section, (
        "Grammar section must mention 'deny-entry' error label for failure mode"
    )


def test_prompt_frontmatter_unchanged():
    """First non-blank line must still start with '# reviewer Step 1' (file identity)."""
    body = _body()
    first_non_blank = next(
        (line for line in body.splitlines() if line.strip()), ""
    )
    assert first_non_blank.startswith("# reviewer Step 1"), (
        f"File identity broken — first non-blank line is: {first_non_blank!r}"
    )


def test_prompt_wrote_discipline_preserved():
    """WROTE: discipline must remain (orchestrator parsing contract)."""
    body = _body()
    assert "WROTE:" in body, (
        "Expected 'WROTE:' discipline to be preserved in prompt body"
    )


def test_prompt_no_constraints_section():
    """## Constraints section must be absent (em-dash rule moved to helper)."""
    body = _body()
    assert "## Constraints" not in body, (
        "## Constraints section should have been removed in B2"
    )


def test_prompt_invokes_helper():
    body = PROMPT_PATH.read_text(encoding="utf-8")
    # B2 M3 fix: import alone is insufficient — verify the helper is invoked.
    assert "parse_scope_md(" in body, (
        "prompt body imports parse_scope_md but does not invoke it; "
        "regression risk — sub-agent could re-emit inline parser logic"
    )


def test_prompt_file_count_unchanged():
    """Exactly 6 prompt files must exist in subagent dir (rename guard)."""
    files = [p for p in SUBAGENT_DIR.glob("*.md") if p.name != ".gitkeep"]
    assert len(files) == 6, (
        f"Expected 6 reviewer subagent prompts, found {len(files)}: "
        f"{[p.name for p in files]}"
    )
