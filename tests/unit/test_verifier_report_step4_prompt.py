"""Spike VIII A6 — verifier_report_step4.md body + VERIFY_REPORT.md.template invariant tests.

Pure file-read + substring/regex checks. No execution.
"""
import re
from pathlib import Path

import pytest

ASSEMBLE = Path.home() / ".claude/skills/assemble"
PROMPT_FILE = (
    ASSEMBLE / "bundled/verifier/prompts/subagent/verifier_report_step4.md"
)
TEMPLATE_FILE = (
    ASSEMBLE / "bundled/verifier/templates/VERIFY_REPORT.md.template"
)

# Mirror the allowlist from server/harness.py for rename-guard test
ALLOWED_PROMPT_FILES = (
    "verifier_extract_step1.md",
    "verifier_execute_step2.md",
    "verifier_classify_step3.md",
    "verifier_report_step4.md",
)

# Expected 7-section titles in order
EXPECTED_SECTIONS = [
    (1, "Summary"),
    (2, "Completion command"),
    (3, "Execution result"),
    (4, "Stdout sample"),
    (5, "Stderr sample"),
    (6, "Verdict reasoning"),
    (7, "Recommendations"),
]


@pytest.fixture(scope="module")
def prompt_text():
    return PROMPT_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def template_text():
    return TEMPLATE_FILE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# PROMPT body invariants (tests 1–8)
# ---------------------------------------------------------------------------

def test_prompt_has_run_dir_placeholder(prompt_text):
    """Both {{RUN_DIR}} and {{RUN_ID}} must be present."""
    assert "{{RUN_DIR}}" in prompt_text, "missing {{RUN_DIR}} placeholder"
    assert "{{RUN_ID}}" in prompt_text, "missing {{RUN_ID}} placeholder"


def test_prompt_writes_verify_report_md(prompt_text):
    """Prompt must reference the output file VERIFY_REPORT.md."""
    assert "VERIFY_REPORT.md" in prompt_text, (
        "missing VERIFY_REPORT.md output file reference"
    )


def test_prompt_no_bash_tool_marker(prompt_text):
    """Step 4 must NOT grant Bash tool access — 'Bash tool' marker absent."""
    assert "Bash tool" not in prompt_text, (
        "Step 4 must not reference 'Bash tool' — only Step 2 receives Bash tool access"
    )
    assert "Bash tool access" not in prompt_text, (
        "Step 4 must not grant Bash tool access"
    )


def test_prompt_uses_str_replace_not_jinja(prompt_text):
    """Substitution must use str.replace (not Jinja). body.replace present; jinja2 import absent."""
    assert ("str.replace" in prompt_text or "body.replace(" in prompt_text), (
        "missing str.replace / body.replace — Step 4 must use str.replace, not Jinja"
    )
    # "Jinja" may appear as a negation ("NOT Jinja", "NO Jinja") — check no actual import
    assert "import jinja2" not in prompt_text, "jinja2 import must NOT be present (use str.replace)"
    assert "from jinja2" not in prompt_text, "jinja2 import must NOT be present (use str.replace)"


def test_prompt_reads_three_json_inputs(prompt_text):
    """All three input JSON files must be referenced."""
    assert "extracted_completion.json" in prompt_text, "missing extracted_completion.json reference"
    assert "execution_result.json" in prompt_text, "missing execution_result.json reference"
    assert "verify_result.json" in prompt_text, "missing verify_result.json reference"


def test_prompt_references_template_path(prompt_text):
    """Prompt must reference the canonical template path."""
    assert "VERIFY_REPORT.md.template" in prompt_text, (
        "missing VERIFY_REPORT.md.template reference"
    )


def test_prompt_wrote_discipline_preserved(prompt_text):
    """WROTE: discipline must be present for orchestrator regex parsing."""
    assert "WROTE:" in prompt_text, "missing WROTE: output discipline"


def test_prompt_filename_matches_allowlist():
    """File basename must be verifier_report_step4.md and present in ALLOWED_PROMPT_FILES."""
    assert PROMPT_FILE.name == "verifier_report_step4.md", (
        f"unexpected filename: {PROMPT_FILE.name}"
    )
    assert PROMPT_FILE.name in ALLOWED_PROMPT_FILES, (
        f"{PROMPT_FILE.name!r} not found in ALLOWED_PROMPT_FILES — "
        "rename guard: sync harness.py if you rename this file"
    )


# ---------------------------------------------------------------------------
# TEMPLATE invariants (tests 9–12)
# ---------------------------------------------------------------------------

def test_template_has_seven_sections(template_text):
    """All 7 canonical H2 section headers must be present in the template."""
    for num, title in EXPECTED_SECTIONS:
        header = f"## {num}. {title}"
        assert header in template_text, (
            f"missing section header: {header!r}"
        )


def test_template_uses_curly_placeholders(template_text):
    """Key {{...}} placeholders must all be present in the template."""
    required_placeholders = [
        "{{VERDICT}}",
        "{{REASON}}",
        "{{EXIT_CODE}}",
        "{{DURATION_MS}}",
        "{{COMPLETION}}",
    ]
    for placeholder in required_placeholders:
        assert placeholder in template_text, (
            f"missing placeholder {placeholder!r} in VERIFY_REPORT.md.template"
        )


def test_template_present_at_canonical_path():
    """Template must exist at bundled/verifier/templates/VERIFY_REPORT.md.template."""
    canonical = ASSEMBLE / "bundled/verifier/templates/VERIFY_REPORT.md.template"
    assert canonical.exists(), (
        f"template not found at canonical path: {canonical}"
    )


def test_template_pins_seven_sections_order(template_text):
    """Sections must appear in numeric order 1-7 with correct titles."""
    pattern = re.compile(r"^## (\d+)\. (.+)$", re.MULTILINE)
    matches = pattern.findall(template_text)
    # Filter to numeric sections only
    numeric_sections = [(int(n), title) for n, title in matches]
    assert len(numeric_sections) >= 7, (
        f"expected at least 7 numbered sections, found {len(numeric_sections)}: {numeric_sections}"
    )
    # Take the first 7 and verify they match expected order + titles
    for i, (expected_num, expected_title) in enumerate(EXPECTED_SECTIONS):
        actual_num, actual_title = numeric_sections[i]
        assert actual_num == expected_num, (
            f"section {i+1}: expected number {expected_num}, got {actual_num}"
        )
        assert actual_title == expected_title, (
            f"section {i+1}: expected title {expected_title!r}, got {actual_title!r}"
        )
