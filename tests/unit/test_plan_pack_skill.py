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
    # Phase B-1 Task 4 lands single dispatch only; "parallel" is added in Task 5.
    assert "single dispatch" in body.lower() or "1 Agent call" in body
    assert "PRD body" in body or "PRD draft" in body


def test_workflow_writes_to_run_dir():
    body = _body()
    assert "PRD.md" in body
    assert "<run_dir>" in body or "runs/<rid>" in body
