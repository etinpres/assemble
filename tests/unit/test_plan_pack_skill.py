"""Text-shape regression for bundled/plan-pack/SKILL.md.

The SKILL.md is *instructions for the main Claude*, not code. We can't
unit-test runtime orchestration here. We *can* assert that the document
contains the workflow stages we promised — every Task 4–7 commit lands one
new stage, and these grep checks lock the contract.
"""
from pathlib import Path

import pytest


SKILL = Path.home() / ".claude/skills/assemble/bundled/plan-pack/SKILL.md"


def _body() -> str:
    return SKILL.read_text()


def test_skill_lives_at_expected_path():
    assert SKILL.exists(), f"missing: {SKILL}"


def test_skill_is_orchestrator_only():
    body = _body()
    assert "orchestrator-only" in body.lower()


def test_skill_references_run_dir_helper():
    body = _body()
    assert "write_run_artifact" in body


def test_skill_references_harness_wrapper():
    body = _body()
    assert "wrap_with_preamble" in body


def test_workflow_step_1_interview_eight_questions():
    body = _body()
    assert "## Workflow" in body
    # Step 1 must mention the 8-question interview by AskUserQuestion.
    assert "AskUserQuestion" in body
    assert "8 questions" in body


def test_workflow_step_2_single_dispatch_for_prd_body():
    body = _body()
    # Task 5 supersedes Task 4: the workflow now dispatches via the
    # plan-implementation role for the PRD body. The "single dispatch" phrase
    # is gone (replaced by parallel) — what we still assert is that PRD body
    # work is mapped to a sub-agent, not done by main Claude inline.
    assert "PRD body" in body or "PRD draft" in body
    assert "plan-implementation" in body


def test_workflow_writes_to_run_dir():
    body = _body()
    assert "PRD.md" in body
    assert "<run_dir>" in body or "runs/<rid>" in body


def test_workflow_step_3_parallel_dispatch_for_ac_bash():
    body = _body()
    # Task 5 changes the contract — single dispatch is replaced by parallel.
    assert "single message" in body.lower()
    assert "2 Agent calls" in body or "two agent calls" in body.lower()
    assert "AC bash" in body or "Acceptance Criteria" in body


def test_workflow_step_3_explains_role_for_ac_bash():
    body = _body()
    # AC bash dispatch uses the same role mapping (plan-implementation/Plan).
    # Verify the phrase appears at least twice — once for Step 2 PRD body,
    # once for Step 3 AC bash.
    occurrences = body.lower().count("plan-implementation")
    assert occurrences >= 2, f"plan-implementation mentioned {occurrences} times"


def test_workflow_question_6_now_active():
    body = _body()
    # The Phase B-1 Task 4 note ("skipped in Phase B-1 Task 4") is removed
    # in this task — question 6 is now live.
    assert "skipped in Phase B-1 Task 4" not in body


def test_workflow_step_4_second_opinion_review():
    body = _body()
    assert "Step 4" in body
    assert "second-opinion" in body
    # Review must explicitly demand flaws/rebuttals, not bare agreement.
    assert "flaw" in body.lower() or "rebut" in body.lower() or "challenge" in body.lower()


def test_workflow_review_uses_role_mapping_fallback():
    body = _body()
    # second-opinion preferred agents listed in the role-mapping table must
    # be referenced again in the workflow's Step 4 (so a fresh reader
    # doesn't have to scroll up).
    assert "codex:codex-rescue" in body or "code-reviewer" in body
