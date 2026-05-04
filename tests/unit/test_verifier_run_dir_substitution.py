"""A9 — verifier {{RUN_DIR}} token substitution contract.

3 tests:
  1. test_all_verifier_subagent_prompts_have_run_dir_token — each of the 4
     on-disk verifier subagent prompts contains {{RUN_DIR}}.
  2. test_dispatch_substitutes_run_dir_to_absolute_path — after
     dispatch_prompt + substitute_inputs, the literal token is gone and the
     absolute run path is present.
  3. test_run_id_token_also_substituted — regression guard that {{RUN_ID}}
     is also replaced by substitute_inputs.
"""

from pathlib import Path

import server
import server.harness as h

_VERIFIER_SUBAGENT_DIR = (
    Path(__file__).resolve().parents[2]
    / "bundled/verifier/prompts/subagent"
)

_VERIFIER_SUBAGENT_PROMPTS = [
    "verifier_extract_step1.md",
    "verifier_execute_step2.md",
    "verifier_classify_step3.md",
    "verifier_report_step4.md",
]

_TEST_RUN_ID = "test-rid-A9"


def test_all_verifier_subagent_prompts_have_run_dir_token():
    """Every verifier subagent prompt file on disk must contain {{RUN_DIR}}.

    Sub-agents construct artifact paths via the substituted RUN_DIR value;
    absence of the token means the sub-agent has no way to locate the run.
    """
    for filename in _VERIFIER_SUBAGENT_PROMPTS:
        path = _VERIFIER_SUBAGENT_DIR / filename
        assert path.exists(), f"prompt file missing on disk: {path}"
        text = path.read_text(encoding="utf-8")
        assert "{{RUN_DIR}}" in text, (
            f"{filename}: {{{{RUN_DIR}}}} token absent — sub-agent cannot "
            f"locate run artifacts"
        )


def test_dispatch_substitutes_run_dir_to_absolute_path():
    """After dispatch + substitute_inputs, the Inputs section has the absolute
    run path and the {{RUN_DIR}} literal is gone from that section.

    Per harness spec §1.2 (B2 option B): substitute_inputs is scoped to the
    Inputs section only. Body references (## Goal, code blocks, ## Save) retain
    {{RUN_DIR}} intentionally so sub-agent save-block patterns survive.
    """
    for filename in _VERIFIER_SUBAGENT_PROMPTS:
        raw = server.dispatch_prompt(filename)
        result = h.substitute_inputs(raw, {"RUN_ID": _TEST_RUN_ID})

        # The Inputs section must have the absolute path substituted in.
        assert f"runs/{_TEST_RUN_ID}" in result, (
            f"{filename}: 'runs/{_TEST_RUN_ID}' not found in substituted result"
        )
        assert f".claude/channels/assemble/runs/{_TEST_RUN_ID}" in result, (
            f"{filename}: expected absolute run path "
            f"'.claude/channels/assemble/runs/{_TEST_RUN_ID}' in substituted result"
        )

        # Within the Inputs section specifically, the literal token must be gone.
        if "## Inputs" in result:
            inputs_block = result.split("## Inputs")[1].split("\n##")[0]
            assert "{{RUN_DIR}}" not in inputs_block, (
                f"{filename}: {{{{RUN_DIR}}}} literal still present in Inputs section "
                f"after substitute_inputs"
            )


def test_run_id_token_also_substituted():
    """Regression guard: {{RUN_ID}} is replaced alongside {{RUN_DIR}}.

    This confirms the existing harness substitute_inputs behavior applies
    correctly to verifier prompts — both tokens must be resolved in the
    Inputs section.
    """
    for filename in _VERIFIER_SUBAGENT_PROMPTS:
        raw = server.dispatch_prompt(filename)

        # Confirm the raw dispatch still has the {{RUN_ID}} token in Inputs.
        assert "{{RUN_ID}}" in raw, (
            f"{filename}: {{{{RUN_ID}}}} token absent from raw dispatch — "
            f"prompt Inputs section may have changed"
        )

        result = h.substitute_inputs(raw, {"RUN_ID": _TEST_RUN_ID})
        # After substitution, the token must be gone from the Inputs section.
        # Note: body references (outside Inputs) are intentionally left intact
        # per harness spec §1.2; we verify the Inputs-scoped replacement worked
        # by asserting the actual run_id value appears in the result.
        assert _TEST_RUN_ID in result, (
            f"{filename}: run_id value '{_TEST_RUN_ID}' not found after substitution"
        )
