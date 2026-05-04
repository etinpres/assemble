"""A9 — verifier dispatch path: allowlist, preamble, RUN_DIR substitution.

3 tests:
  1. test_verifier_step_prompts_dispatchable — all 4 verifier subagent prompts
     are dispatchable, preamble is prepended, RUN_DIR token is substituted.
  2. test_non_allowlisted_verifier_prompt_raises — allowlist gate raises for
     an unknown verifier-prefixed filename.
  3. test_iter_revisit_helper_not_dispatchable — verifier_iter_revisit.md is
     an orchestrator helper, not in the subagent allowlist; raises ValueError.
"""

import pytest
from pathlib import Path

import server
import server.harness as h

# Canonical v3 preamble fragment — presence confirms preamble was prepended.
_PREAMBLE_MARKER = "read·grep 금지"

# The 4 verifier subagent prompt files in allowlist order.
_VERIFIER_SUBAGENT_PROMPTS = [
    "verifier_extract_step1.md",
    "verifier_execute_step2.md",
    "verifier_classify_step3.md",
    "verifier_report_step4.md",
]

_TEST_RUN_ID = "test-rid"


def test_verifier_step_prompts_dispatchable():
    """All 4 verifier subagent prompts dispatch successfully.

    For each prompt:
      - dispatch_prompt returns a non-empty string
      - preamble marker is present (preamble prepended)
      - after substitute_inputs, {{RUN_DIR}} is replaced with a path
        containing runs/<run_id>
      - prompt body marker (step heading) is present
    """
    body_markers = {
        "verifier_extract_step1.md": "# verifier Step 1",
        "verifier_execute_step2.md": "# verifier Step 2",
        "verifier_classify_step3.md": "# verifier Step 3",
        "verifier_report_step4.md": "# verifier Step 4",
    }

    for prompt_file in _VERIFIER_SUBAGENT_PROMPTS:
        raw = server.dispatch_prompt(prompt_file)
        assert isinstance(raw, str) and raw, (
            f"{prompt_file}: dispatch_prompt returned empty"
        )
        assert _PREAMBLE_MARKER in raw, (
            f"{prompt_file}: v3 preamble marker missing after dispatch"
        )

        substituted = h.substitute_inputs(raw, {"RUN_ID": _TEST_RUN_ID})
        # Inputs section: the literal {{RUN_DIR}} token must be gone from the
        # Inputs block (everything before ## Goal/## Constraints/## Save).
        inputs_section = substituted.split("## Inputs")[1].split("\n##")[0] if "## Inputs" in substituted else ""
        assert "{{RUN_DIR}}" not in inputs_section, (
            f"{prompt_file}: {{{{RUN_DIR}}}} literal survived in Inputs section"
        )
        # The substituted absolute path must appear in the result.
        assert f"runs/{_TEST_RUN_ID}" in substituted, (
            f"{prompt_file}: expected 'runs/{_TEST_RUN_ID}' in substituted result"
        )
        assert ".claude/channels/assemble/runs/" + _TEST_RUN_ID in substituted, (
            f"{prompt_file}: expected absolute run path in substituted result"
        )

        assert body_markers[prompt_file] in raw, (
            f"{prompt_file}: body heading marker missing"
        )


def test_non_allowlisted_verifier_prompt_raises():
    """A verifier-prefixed filename not in ALLOWED_PROMPT_FILES raises ValueError."""
    with pytest.raises(ValueError, match=r"not allowed"):
        server.dispatch_prompt("verifier_unknown.md")


def test_iter_revisit_helper_not_dispatchable():
    """verifier_iter_revisit.md is an orchestrator helper, not a subagent prompt.

    It must NOT appear in ALLOWED_PROMPT_FILES (main Claude reads it directly),
    and dispatch_prompt must raise when given this filename.
    """
    assert "verifier_iter_revisit.md" not in server.ALLOWED_PROMPT_FILES, (
        "verifier_iter_revisit.md must remain outside ALLOWED_PROMPT_FILES "
        "(orchestrator-only, never dispatched via harness)"
    )
    with pytest.raises(ValueError, match=r"not allowed"):
        server.dispatch_prompt("verifier_iter_revisit.md")
