"""Spike VIII A3 — verifier_execute_step2.md body invariant tests.

Pure file-read + substring/regex checks. No execution.
"""
from pathlib import Path

import pytest

ASSEMBLE = Path.home() / ".claude/skills/assemble"
PROMPT_FILE = (
    ASSEMBLE / "bundled/verifier/prompts/subagent/verifier_execute_step2.md"
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


def test_prompt_writes_execution_result_json(prompt_text):
    """Prompt must reference the output file execution_result.json."""
    assert "execution_result.json" in prompt_text


def test_prompt_grants_bash_tool(prompt_text):
    """Security-critical marker — A8 Codex retro will grep for this exact phrase."""
    assert "Bash tool access GRANTED" in prompt_text, (
        "missing 'Bash tool access GRANTED' marker — required for A8 Codex retro"
    )


def test_prompt_has_subprocess_run(prompt_text):
    """Python code block must use subprocess.run with timeout=30."""
    assert "subprocess.run" in prompt_text, "missing subprocess.run"
    assert "timeout=30" in prompt_text, "missing timeout=30"


def test_prompt_has_output_cap(prompt_text):
    """100KB output cap must be documented (100_000 literal)."""
    assert "100_000" in prompt_text, "missing 100_000 output cap"


def test_prompt_has_truncated_field(prompt_text):
    """Output JSON shape must include truncated field."""
    assert "truncated" in prompt_text


def test_prompt_has_timed_out_field(prompt_text):
    """Output JSON shape must include timed_out field."""
    assert "timed_out" in prompt_text


def test_prompt_has_skipped_field(prompt_text):
    """Skip-on-extract-errors flow must be documented (skipped field)."""
    assert "skipped" in prompt_text


def test_prompt_wrote_discipline_preserved(prompt_text):
    """WROTE: discipline must be present for orchestrator regex parsing."""
    assert "WROTE:" in prompt_text


def test_prompt_filename_matches_allowlist():
    """File basename must be verifier_execute_step2.md and present in ALLOWED_PROMPT_FILES."""
    assert PROMPT_FILE.name == "verifier_execute_step2.md", (
        f"unexpected filename: {PROMPT_FILE.name}"
    )
    assert PROMPT_FILE.name in ALLOWED_PROMPT_FILES, (
        f"{PROMPT_FILE.name!r} not found in ALLOWED_PROMPT_FILES — "
        "rename guard: sync harness.py if you rename this file"
    )


def test_prompt_has_security_section(prompt_text):
    """Prompt must contain ## Security model section."""
    assert "## Security model" in prompt_text


def test_prompt_pins_security_mitigation_count(prompt_text):
    """All three numeric caps/limits must appear in canonical forms."""
    # Tightened from raw "30"/"500" to canonical forms — substring "30" matches noise.
    assert "100_000" in prompt_text, "missing 100KB output cap literal"
    assert "timeout=30" in prompt_text, "missing subprocess.run timeout=30 literal"
    assert "≤500" in prompt_text or "<= 500" in prompt_text or "len <= 500" in prompt_text or "(500)" in prompt_text, (
        "missing length cap reference (expected ≤500 / <= 500 / len <= 500 / (500))"
    )


def test_prompt_includes_skip_reasons_array(prompt_text):
    """I2 fix: skip_reasons array and skip_reason convenience scalar must both be present."""
    assert "skip_reasons" in prompt_text, "missing skip_reasons array (I2 fix from A3 review)"
    assert "skip_reason" in prompt_text, "missing skip_reason convenience scalar"


# ---------------------------------------------------------------------------
# Codex retro A8b — F2 process-group kill invariants
# ---------------------------------------------------------------------------

def test_prompt_uses_process_group_kill(prompt_text):
    """Codex retro F2: start_new_session=True + os.killpg + signal.SIGKILL must ALL be present."""
    assert "start_new_session=True" in prompt_text, (
        "missing start_new_session=True — Codex retro F2 requires process-group isolation"
    )
    assert "os.killpg" in prompt_text, (
        "missing os.killpg — Codex retro F2 requires process-group kill on timeout"
    )
    assert "signal.SIGKILL" in prompt_text, (
        "missing signal.SIGKILL — Codex retro F2 requires SIGKILL for process-group kill"
    )


def test_prompt_uses_popen_not_run(prompt_text):
    """Codex retro F2: subprocess.Popen must be present; subprocess.run must be ABSENT in the primary recipe."""
    assert "subprocess.Popen" in prompt_text, (
        "missing subprocess.Popen — Codex retro F2 switched from subprocess.run to Popen"
    )
    # subprocess.run must not appear as the primary invocation recipe.
    # It may appear in comments or documentation but not as an active call in the code block.
    # We check that the primary recipe uses Popen by verifying Popen is present and
    # that any mention of subprocess.run is not an active invocation (not followed by '(').
    import re
    # Find all occurrences of subprocess.run( — if any exist it means the old recipe is still active
    active_run_calls = re.findall(r"subprocess\.run\s*\(", prompt_text)
    assert len(active_run_calls) == 0, (
        f"subprocess.run( found {len(active_run_calls)} time(s) — should be replaced by subprocess.Popen (Codex retro F2)"
    )
