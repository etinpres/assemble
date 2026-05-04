"""Spike VIII A5 — verifier_classify_step3.md body invariant tests.

Pure file-read + substring/regex checks. No execution.
"""
from pathlib import Path

import pytest

ASSEMBLE = Path.home() / ".claude/skills/assemble"
PROMPT_FILE = (
    ASSEMBLE / "bundled/verifier/prompts/subagent/verifier_classify_step3.md"
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


def test_prompt_writes_verify_result_json(prompt_text):
    """Prompt must reference the output file verify_result.json."""
    assert "verify_result.json" in prompt_text


def test_prompt_no_bash_tool_marker(prompt_text):
    """Step 3 must NOT grant Bash tool access — 'Bash tool access' marker absent."""
    assert "Bash tool access" not in prompt_text, (
        "Step 3 must not grant Bash tool access — only Step 2 receives Bash"
    )


def test_prompt_has_verdict_invariant(prompt_text):
    """Verdict invariant section must document pass condition."""
    assert 'verdict == "pass"' in prompt_text, (
        "missing verdict invariant — expected 'verdict == \"pass\"' substring"
    )


def test_prompt_pins_verdict_logic(prompt_text):
    """All three deterministic conditions must appear: exit_code==0, timed_out, skipped."""
    assert "exit_code == 0" in prompt_text, "missing exit_code == 0 condition"
    assert "timed_out" in prompt_text, "missing timed_out condition"
    assert "skipped" in prompt_text, "missing skipped condition"


def test_prompt_handles_skip_reasons_array(prompt_text):
    """A3 schema upgrade: skip_reasons array must be referenced."""
    assert "skip_reasons" in prompt_text, (
        "missing skip_reasons array — required for A3 I2 schema upgrade compatibility"
    )


def test_prompt_truncated_does_not_fail(prompt_text):
    """Prompt must explicitly state that Truncated output does NOT auto-fail."""
    assert "Truncated" in prompt_text or "truncated" in prompt_text, (
        "missing 'truncated' field reference"
    )
    assert "NOT auto-fail" in prompt_text or "does NOT auto-fail" in prompt_text or "not a verdict input" in prompt_text, (
        "prompt must explicitly state truncated output does NOT auto-fail"
    )


def test_prompt_wrote_discipline_preserved(prompt_text):
    """WROTE: discipline must be present for orchestrator regex parsing."""
    assert "WROTE:" in prompt_text


def test_prompt_filename_matches_allowlist():
    """File basename must be verifier_classify_step3.md and present in ALLOWED_PROMPT_FILES."""
    assert PROMPT_FILE.name == "verifier_classify_step3.md", (
        f"unexpected filename: {PROMPT_FILE.name}"
    )
    assert PROMPT_FILE.name in ALLOWED_PROMPT_FILES, (
        f"{PROMPT_FILE.name!r} not found in ALLOWED_PROMPT_FILES — "
        "rename guard: sync harness.py if you rename this file"
    )


def test_prompt_pins_verdict_labels(prompt_text):
    """Canonical verdict labels 'pass' and 'fail' must be present (not 'success'/'failure')."""
    assert '"pass"' in prompt_text, "missing canonical 'pass' label"
    assert '"fail"' in prompt_text, "missing canonical 'fail' label"
    assert "success" not in prompt_text or "False" in prompt_text, (
        "non-canonical verdict label 'success' found — use 'pass' instead"
    )
