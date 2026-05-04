"""Unit tests for `bundled/keeper/prompts/orchestrator/keeper_iter_revisit.md`
(V4 Spike X, Task B6).

This is an **orchestrator helper**, NOT a subagent prompt:

  * Lives under `prompts/orchestrator/`, NOT `prompts/subagent/`.
  * Read directly by main Claude when re-keeping is requested — NOT
    loaded via `dispatch_prompt`.
  * Tools inherit from main Claude's access — no `Bash tool access GRANTED`
    marker (helpers do not grant tools — they inherit).
  * Will be registered in `ORCHESTRATOR_ONLY_PROMPTS` at Phase D2 (NOT in
    this task's scope). The allowlist roundtrip already enforces the
    inverse via `ORCHESTRATOR_ONLY_PROMPTS` exemption.

Grep-gate tests on the helper body — these lock in the structural
contracts:

  * Helper file exists at the correct path under `prompts/orchestrator/`.
  * NO `## Bash tool access GRANTED` heading (orchestrator helpers
    don't grant tools — they inherit from main Claude).
  * Body contains the canonical "orchestrator helper, NOT a subagent
    prompt" disambiguation marker.
  * Required sections present: `## Decision tree`, `## Iteration semantics`.
  * Body explicitly cites all four keeper subagent prompt filenames so
    the helper itself documents the dispatch chain.
"""

from pathlib import Path

import pytest

PROMPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "bundled"
    / "keeper"
    / "prompts"
    / "orchestrator"
    / "keeper_iter_revisit.md"
)


@pytest.fixture(scope="module")
def prompt_body() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def test_orchestrator_helper_exists():
    """File must live at `bundled/keeper/prompts/orchestrator/keeper_iter_revisit.md`."""
    assert PROMPT_PATH.exists(), (
        f"keeper_iter_revisit.md not found at {PROMPT_PATH} — "
        f"orchestrator helpers must live under prompts/orchestrator/, "
        f"NOT prompts/subagent/"
    )
    assert PROMPT_PATH.is_file()


def test_no_bash_grant_heading(prompt_body: str):
    """Orchestrator helpers do NOT grant tools — they inherit from main
    Claude's access. The presence of `## Bash tool access GRANTED` would
    be a category error (only subagent prompts dispatched via
    `dispatch_prompt` carry that marker).
    """
    assert "## Bash tool access GRANTED" not in prompt_body, (
        "orchestrator helpers must not contain `## Bash tool access GRANTED` "
        "— that heading is reserved for subagent prompts dispatched via "
        "dispatch_prompt; helpers inherit main Claude's tools"
    )


def test_note_marks_as_orchestrator_helper(prompt_body: str):
    """Body must contain the canonical disambiguation marker so any
    reader (human or grep) immediately recognizes this as an orchestrator
    helper rather than a subagent prompt.
    """
    assert "orchestrator helper, NOT a subagent prompt" in prompt_body, (
        "helper body must include the canonical 'orchestrator helper, NOT "
        "a subagent prompt' marker (case-sensitive)"
    )


def test_decision_tree_section_present(prompt_body: str):
    """The §Decision tree section codifies the main-Claude control flow
    for iteration revisit — required for orchestrator usability.
    """
    assert "## Decision tree" in prompt_body, (
        "helper body must contain `## Decision tree` section"
    )


def test_iteration_semantics_table_present(prompt_body: str):
    """The §Iteration semantics table documents per-step re-run
    conditions and dispatches.jsonl row counts — required for audit-trail
    invariants.
    """
    assert "## Iteration semantics" in prompt_body, (
        "helper body must contain `## Iteration semantics` section"
    )


def test_lists_4_subagent_prompts(prompt_body: str):
    """Helper must explicitly cite the 4 keeper subagent prompt
    filenames so the dispatch chain is documented in-file.
    """
    expected = (
        "keeper_audit_step1.md",
        "keeper_extract_step2.md",
        "keeper_summarize_step3.md",
        "keeper_ledger_step4.md",
    )
    missing = [name for name in expected if name not in prompt_body]
    assert not missing, (
        f"helper body must cite all 4 keeper subagent prompt filenames; "
        f"missing: {missing}"
    )
