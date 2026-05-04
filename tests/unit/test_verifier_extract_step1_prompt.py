"""Spike VIII A2 — verifier_extract_step1.md body invariant tests.

Pure file-read + substring/regex checks. No execution.
"""
from pathlib import Path

import pytest

ASSEMBLE = Path.home() / ".claude/skills/assemble"
PROMPT_FILE = (
    ASSEMBLE / "bundled/verifier/prompts/subagent/verifier_extract_step1.md"
)

# Mirror the allowlist from server/harness.py for rename-guard test
ALLOWED_PROMPT_FILES = (
    "verifier_extract_step1.md",
    "verifier_execute_step2.md",
    "verifier_classify_step3.md",
    "verifier_report_step4.md",
)


@pytest.fixture(scope="module")
def prompt_text():
    return PROMPT_FILE.read_text(encoding="utf-8")


def test_prompt_has_run_dir_placeholder(prompt_text):
    """Both {{RUN_DIR}} and {{RUN_ID}} must be present."""
    assert "{{RUN_DIR}}" in prompt_text, "missing {{RUN_DIR}} placeholder"
    assert "{{RUN_ID}}" in prompt_text, "missing {{RUN_ID}} placeholder"


def test_prompt_writes_extracted_completion_json(prompt_text):
    """Prompt must reference the output file extracted_completion.json."""
    assert "extracted_completion.json" in prompt_text


def test_prompt_no_bash_tool_marker(prompt_text):
    """Step 1 is pure Python I/O — no Bash tool access.

    'Bash' may appear as 'NO Bash' instruction, but 'Bash tool' or
    'Bash tool access' must NOT appear (those phrases indicate shell dispatch).
    """
    assert "Bash" in prompt_text, (
        "'Bash' should appear at least once (as 'NO Bash' instruction)"
    )
    assert "Bash tool" not in prompt_text, (
        "prompt must not mention 'Bash tool' — Step 1 has no shell access"
    )
    assert "Bash tool access" not in prompt_text, (
        "prompt must not mention 'Bash tool access'"
    )


def test_prompt_has_length_cap_rule(prompt_text):
    """Security length cap of 500 characters must be documented."""
    assert "500" in prompt_text, "missing length cap rule (500)"


def test_prompt_wrote_discipline_preserved(prompt_text):
    """WROTE: discipline must be present for orchestrator regex parsing."""
    assert "WROTE:" in prompt_text


def test_prompt_invokes_json_load(prompt_text):
    """Python code block must describe json.loads (read) and json.dumps (write)."""
    assert "json.loads" in prompt_text, "missing json.loads"
    assert "json.dumps" in prompt_text, "missing json.dumps"


def test_prompt_has_validation_rules_section(prompt_text):
    """Prompt must contain a ## Validation rules section."""
    assert "## Validation rules" in prompt_text


def test_prompt_filename_matches_allowlist():
    """File basename must be verifier_extract_step1.md and present in ALLOWED_PROMPT_FILES."""
    assert PROMPT_FILE.name == "verifier_extract_step1.md", (
        f"unexpected filename: {PROMPT_FILE.name}"
    )
    assert PROMPT_FILE.name in ALLOWED_PROMPT_FILES, (
        f"{PROMPT_FILE.name!r} not found in ALLOWED_PROMPT_FILES — "
        "rename guard: sync harness.py if you rename this file"
    )


def test_prompt_pins_error_labels():
    """Prevent typos in error labels — downstream pattern-matches these literals."""
    body = PROMPT_FILE.read_text(encoding="utf-8")
    expected = [
        "parsed-scope-missing",
        "parsed-scope-malformed",
        "completion-non-string",
        "completion-empty",
        "completion-too-long",
        "completion-multiline",
    ]
    for label in expected:
        assert label in body, f"missing error label: {label}"
