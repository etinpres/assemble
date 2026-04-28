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


def test_workflow_step_6_iteration_prompt():
    body = _body()
    assert "Step 6" in body
    assert "iteration" in body.lower()
    # Iteration must be opt-in (not forced) — V4 identity rule.
    assert "AskUserQuestion" in body
    # Phase B-1 covers exactly one iteration; counts of 3–7 are deferred.
    assert "one iteration" in body.lower() or "1 iteration" in body.lower()


def test_workflow_iteration_does_not_force_loop():
    body = _body()
    # Hard prohibition from spec section 10: never force the user into
    # multiple iterations. The workflow must mention that "no" exits.
    assert "no exits" in body.lower() or "no → " in body or "user can exit" in body.lower()


def test_workflow_iteration_hard_caps_at_one():
    """Step 6 must explicitly state the post-iteration exit policy. Without
    this contract, second-yes behavior is unbounded."""
    body = _body()
    assert "exits unconditionally" in body or "iteration cap reached" in body


def test_skill_description_mentions_arch():
    from server import parse_skill_frontmatter
    fm = parse_skill_frontmatter(SKILL)
    desc = (fm.get("description") or "").upper()
    assert "ARCH" in desc, f"description does not mention ARCH: {fm.get('description')}"


def test_workflow_step_7_arch_interview():
    body = _body()
    assert "Step 7" in body
    step7 = body[body.index("Step 7"):]
    assert "AskUserQuestion" in step7[:2000]
    # Gate B2.2 seeds: interview must ask about directory tree and data flow
    assert "directory" in step7[:2000].lower()
    assert "data flow" in step7[:2000].lower() or "data-flow" in step7[:2000].lower()


def test_workflow_step_8_arch_single_dispatch():
    body = _body()
    assert "Step 8" in body
    step8 = body[body.index("### Step 8"):]
    # Phase B spec §3: B-2 through B-4 are single-dispatch, not parallel
    assert "single" in step8[:1000].lower()
    assert "ARCHITECTURE.md" in step8[:1000]
    assert "wrap_with_preamble" in step8[:1000]
    assert "write_run_artifact" in step8[:1000]


def test_skill_preamble_matches_shared_file():
    """The 4 harness rules appear both in plan-pack/SKILL.md (as a
    documentation backup) and in bundled/_shared/harness-preamble.md
    (the runtime source loaded by server.harness). They must stay in
    sync — runtime uses the file, the SKILL copy is for human readers
    who may never see the dispatched prompt.
    """
    shared = Path.home() / ".claude/skills/assemble/bundled/_shared/harness-preamble.md"
    if not shared.exists():
        pytest.skip("shared preamble file missing; covered by e2e existence test")
    shared_body = shared.read_text().strip()
    skill_body = _body()
    # Each non-blank line of the shared preamble must appear in SKILL.md
    for line in shared_body.splitlines():
        line = line.strip()
        if not line:
            continue
        assert line in skill_body, (
            f"preamble line missing from SKILL.md: {line!r}"
        )


def test_workflow_step_9_cross_doc_review():
    body = _body()
    assert "Step 9" in body
    step9 = body[body.index("### Step 9"):]
    # Must reference both documents
    assert "PRD" in step9[:800]
    assert "ARCHITECTURE" in step9[:800]
    # Must challenge, not merely agree (gate B2.3)
    assert (
        "flaw" in step9[:800].lower()
        or "rebut" in step9[:800].lower()
        or "challenge" in step9[:800].lower()
        or "inconsisten" in step9[:800].lower()
        or "gap" in step9[:800].lower()
    )


def test_workflow_step_9_uses_second_opinion_role():
    body = _body()
    step9 = body[body.index("### Step 9"):]
    assert "second-opinion" in step9[:800]
    assert "wrap_with_preamble" in step9[:800]
