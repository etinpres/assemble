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
    # Anchor on the actual workflow section, not the role-mapping table —
    # B-1 retroactive review I2 caught this assertion passing on table-only
    # mentions.
    step23 = body[body.index("### Step 2 — PRD body draft"):
                  body.index("### Step 4")]
    assert "single message" in step23.lower()
    assert "2 Agent calls" in step23 or "two agent calls" in step23.lower()
    assert "AC bash" in step23 or "Acceptance Criteria" in step23


def test_workflow_step_3_explains_role_for_ac_bash():
    body = _body()
    # The AC bash bullet itself must name the role + fallback — not just
    # the count-twice heuristic, which passes on duplicate role-table rows
    # alone (B-1 retroactive review I2).
    step23 = body[body.index("### Step 2 — PRD body draft"):
                  body.index("### Step 4")]
    # The two parallel sub-tasks each carry the role + Plan fallback line.
    assert step23.count("plan-implementation") >= 2, (
        "Step 2/3 prose must reference plan-implementation role for both "
        "sub-tasks (PRD body + AC bash), not rely on the role-mapping table"
    )
    assert "Plan" in step23 and "general-purpose" in step23, (
        "Step 2/3 prose must spell out the Plan/general-purpose fallback "
        "chain inside the workflow section"
    )


def test_workflow_question_6_now_active():
    body = _body()
    # The Phase B-1 Task 4 note ("skipped in Phase B-1 Task 4") is removed
    # in this task — question 6 is now live.
    assert "skipped in Phase B-1 Task 4" not in body


def test_workflow_step_4_second_opinion_review():
    body = _body()
    assert "### Step 4 — consistency review" in body
    # Anchor to the Step 4 prose, not the whole file — Step 4b can satisfy
    # the bare "second-opinion" assertion via its own header (B-1 review I2).
    step4 = body[body.index("### Step 4 — consistency review"):
                 body.index("#### Step 4b")]
    assert "second-opinion" in step4
    # Review must explicitly demand flaws/rebuttals, not bare agreement.
    assert (
        "flaw" in step4.lower()
        or "rebut" in step4.lower()
        or "challenge" in step4.lower()
    )


def test_workflow_review_uses_role_mapping_fallback():
    body = _body()
    # second-opinion preferred agents must appear in the Step 4 workflow
    # prose (not just the role-mapping table at the top — B-1 review I2).
    step4 = body[body.index("### Step 4 — consistency review"):
                 body.index("#### Step 4b")]
    assert "codex:codex-rescue" in step4 or "code-reviewer" in step4, (
        "Step 4 prose must spell out preferred second-opinion agent — "
        "table-only mention would pass even on empty workflow text"
    )


def test_workflow_step_6_iteration_prompt():
    body = _body()
    step6 = body[body.index("### Step 6"):]
    # Anchor to Step 6 — bare "AskUserQuestion in body" is satisfied by
    # Step 1's interview (B-1 review I2).
    assert "iteration" in step6.lower()
    assert "AskUserQuestion" in step6
    # Phase B-1 covers exactly one iteration; counts of 3–7 are deferred.
    assert "one iteration" in step6.lower() or "1 iteration" in step6.lower()


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
    # Anchor to heading to avoid false-positive on role-table row "| 7 |"
    assert "### Step 7" in body
    step7 = body[body.index("### Step 7"):]
    assert "AskUserQuestion" in step7[:2000]
    # Gate B2.2 seeds: interview must ask about directory tree and data flow
    assert "directory" in step7[:2000].lower()
    assert "data flow" in step7[:2000].lower() or "data-flow" in step7[:2000].lower()


def test_workflow_step_8_arch_single_dispatch():
    body = _body()
    assert "Step 8" in body
    step8 = body[body.index("### Step 8"):]
    # Window 2500 covers fill pseudocode added after dogfood finding #1
    # (sub-agent output ↔ template heading collision).
    # Phase B spec §3: B-2 through B-4 are single-dispatch, not parallel
    assert "single" in step8[:2500].lower()
    assert "ARCHITECTURE.md" in step8[:2500]
    assert "wrap_with_preamble" in step8[:2500]
    assert "write_run_artifact" in step8[:2500]


def test_workflow_step_8_handles_sub_agent_headings():
    """Dogfood finding #1: sub-agent returns markdown with `## Stack`,
    `## Directory tree` etc. headings, but template already has them.
    Naive substitution would duplicate. Step 8 must show how to extract
    section bodies before substituting."""
    body = _body()
    step8 = body[body.index("### Step 8"):]
    fill_block = step8[:3000]
    # The pseudocode must include the section parser, not just a raw
    # `template.replace(..., a1)` map (which is what tripped this dogfood).
    assert "split_sections" in fill_block, (
        "Step 8 must show section-body extraction (dogfood finding #1). "
        "Naive .replace(...) of full sub-agent output would duplicate "
        "## headings already in the template."
    )


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
    # Window widened to 1200 — earlier 800-char slice landed exactly on
    # "flaws" boundary (codex review finding I2)
    assert "PRD" in step9[:1200]
    assert "ARCHITECTURE" in step9[:1200]
    # Must challenge, not merely agree (gate B2.3)
    assert (
        "flaw" in step9[:1200].lower()
        or "rebut" in step9[:1200].lower()
        or "challenge" in step9[:1200].lower()
        or "inconsisten" in step9[:1200].lower()
        or "gap" in step9[:1200].lower()
    )


def test_workflow_step_9_uses_second_opinion_role():
    body = _body()
    step9 = body[body.index("### Step 9"):]
    assert "second-opinion" in step9[:800]
    assert "wrap_with_preamble" in step9[:800]


def test_workflow_iteration_step_6_includes_arch():
    body = _body()
    step6 = body[body.index("### Step 6"):]
    # Window widened to 2500 to cover explicit write-order block
    # added after dogfood finding #3.
    # Iteration must re-run ARCH (Step 8) alongside PRD (Steps 2+3).
    # Bare "ARCH" was tautological — substring of "ARCHITECTURE.md".
    # Anchor on "Step 8" (the actual re-draft instruction).
    assert "Step 8" in step6[:2500]
    assert "ARCHITECTURE.md" in step6[:2500]
    assert "re-draft" in step6[:2500].lower() or "re-runs" in step6[:2500].lower()


def test_workflow_iteration_has_explicit_write_order():
    """Dogfood finding #3: iteration write order was implicit. Step 6
    yes-path must show numbered write-order steps so the main Claude
    follows a deterministic sequence."""
    body = _body()
    step6 = body[body.index("### Step 6"):]
    block = step6[:3500]
    assert "write order" in block.lower(), (
        "Step 6 yes-path must include explicit 'Iteration write order' "
        "block (dogfood finding #3)"
    )
    # Must reference Step 5 overwriting PRD and Step 8 overwriting ARCH
    assert "overwrites `PRD.md`" in block or "overwrite PRD.md" in block.lower()
    assert "overwrites `ARCHITECTURE.md`" in block or "overwrite ARCHITECTURE.md" in block.lower()


def test_workflow_iteration_step_6_no_force_arch():
    body = _body()
    step6 = body[body.index("### Step 6"):]
    # V4 identity rule: "no" must exit cleanly. Anchor on the semantic
    # phrase "exits the workflow" — the earlier "no —" anchor matched
    # the option label too, which would still pass even if the bullet
    # describing "no" was changed to keep a draft going.
    assert "exits the workflow" in step6[:800].lower()


def test_skill_description_mentions_adr():
    from server import parse_skill_frontmatter
    fm = parse_skill_frontmatter(SKILL)
    desc = (fm.get("description") or "").upper()
    assert "ADR" in desc, f"description does not mention ADR: {fm.get('description')}"


def test_workflow_step_10_adr_interview():
    body = _body()
    assert "Step 10" in body
    step10 = body[body.index("Step 10"):]
    assert "AskUserQuestion" in step10[:2000]
    # Gate B3.2 seeds: interview must surface decisions, alternatives, tradeoffs
    lower = step10[:2000].lower()
    assert "decision" in lower
    assert "alternative" in lower or "rejected" in lower
    assert "tradeoff" in lower or "trade-off" in lower


def test_workflow_step_11_adr_single_dispatch():
    body = _body()
    assert "Step 11" in body
    step11 = body[body.index("Step 11"):]
    # Phase B spec §3: B-2 through B-4 are single-dispatch, not parallel
    assert "single" in step11[:1000].lower()
    assert "ADR.md" in step11[:1000]
    assert "wrap_with_preamble" in step11[:1000]
    assert "write_run_artifact" in step11[:1000]
    # Decision count contract for gate B3.2
    assert "3" in step11[:1500] or "three" in step11[:1500].lower()


def test_workflow_step_9_includes_adr():
    body = _body()
    step9 = body[body.index("### Step 9"):]
    # The cross-doc review must now span ADR as well
    assert "ADR" in step9[:1500]
    assert "ADR.md" in step9[:1500] or "ADR.md" in body[body.index("### Step 9"):body.index("### Step 6")]


def test_workflow_step_9_three_way_consistency():
    body = _body()
    step9 = body[body.index("### Step 9"):]
    # Must explicitly cover ARCH↔ADR decision integrity (per phase-b.md §6 B-3)
    lower = step9[:1500].lower()
    assert "decision" in lower
    assert ("rationale" in lower or "reasoning" in lower or "missing" in lower)
    # All three pair labels must be present (matches dogfood gate B3.5 distribution)
    window = step9[:2000]
    assert "PRD ↔ ARCH" in window
    assert "ARCH ↔ ADR" in window
    assert "PRD ↔ ADR" in window


def test_workflow_iteration_step_6_includes_adr():
    body = _body()
    step6 = body[body.index("Step 6 —"):]
    # Iteration must now re-run ADR (Step 11) alongside PRD (Steps 2+3) and ARCH (Step 8)
    assert "Step 11" in step6[:2000] or "ADR" in step6[:2000]
    assert "ADR.md" in step6[:2000]


def test_workflow_iteration_write_order_explicit_adr():
    body = _body()
    step6 = body[body.index("Step 6 —"):]
    # Finding #3 from B-2: iteration write order must be explicit, not implicit.
    # Look for an enumerated step list mentioning ADR overwrite.
    assert "Iteration write order" in step6[:2000]
    overwrite_block = step6[:2500].lower()
    assert "overwrite" in overwrite_block
    assert "adr.md" in overwrite_block

def test_workflow_iteration_step_6_no_force():
    body = _body()
    step6 = body[body.index("Step 6 —"):]
    # V4 identity rule: "no" must exit cleanly, even after extension
    assert "exits the workflow" in step6[:1000].lower()


def test_skill_description_mentions_ui_guide():
    from server import parse_skill_frontmatter
    fm = parse_skill_frontmatter(SKILL)
    desc = (fm.get("description") or "").upper()
    assert "UI_GUIDE" in desc or "UI GUIDE" in desc, (
        f"description does not mention UI_GUIDE: {fm.get('description')}"
    )


def test_workflow_step_12_ui_interview():
    body = _body()
    assert "Step 12" in body
    step12 = body[body.index("Step 12"):]
    assert "AskUserQuestion" in step12[:2000]
    # Gate B4.1/B4.2 seeds: interview must surface visual identity, components, do/don't.
    lower = step12[:2000].lower()
    assert "visual" in lower or "tone" in lower or "aesthetic" in lower
    assert "component" in lower or "pattern" in lower
    assert "antipattern" in lower or "avoid" in lower or "don't" in lower or "do not" in lower


def test_workflow_step_13_ui_single_dispatch_inherits_plan_fix():
    body = _body()
    assert "Step 13" in body
    step13 = body[body.index("Step 13"):]
    # Phase B spec §3: B-2 through B-4 are single-dispatch, not parallel
    assert "single" in step13[:1200].lower()
    assert "UI_GUIDE.md" in step13[:1200]
    assert "wrap_with_preamble" in step13[:1200]
    assert "write_run_artifact" in step13[:1200]
    # B-3 Finding #3 fix carried into Step 13: general-purpose preferred, Plan fallback.
    # Locate the role-mapping table and assert the Step 13 row's preferred column is general-purpose.
    table = body[body.index("## Sub-agent role mapping"):body.index("## Workflow")]
    # The Step 13 row mentions UI_GUIDE.md draft and uses plan-implementation role.
    ui_row = [line for line in table.splitlines()
              if line.startswith("| 13 ") or "UI_GUIDE.md draft" in line]
    assert ui_row, f"no Step 13 row in role table; table=\n{table}"
    row_text = " ".join(ui_row).lower()
    assert "plan-implementation" in row_text
    # Preferred general-purpose, fallback Plan — same swap as Steps 2/3/8/11
    assert "general-purpose" in row_text
    # Plan still appears as the fallback column (case-sensitive `Plan`)
    assert "`Plan`" in " ".join(ui_row)


def test_workflow_step_9_includes_ui_guide():
    body = _body()
    step9 = body[body.index("Step 9 —"):]
    # The cross-doc review must now span UI_GUIDE as well
    assert "UI_GUIDE" in step9[:2000]
    assert "UI_GUIDE.md" in step9[:2500]


def test_workflow_step_9_four_way_includes_antipattern_audit():
    body = _body()
    step9 = body[body.index("Step 9 —"):]
    # Phase B-4 specific: Step 9 must call out the antipattern audit
    # (the cross-check between UI_GUIDE body and PRD `## Design direction`).
    lower = step9[:2500].lower()
    assert "antipattern" in lower or "anti-pattern" in lower
    assert "design direction" in lower
    # Must explicitly enumerate the new pair categories beyond the 3 from B-3
    assert "ui_guide" in lower or "ui guide" in lower
    # Audit must be either part of category 4/5/6 (new pair labels) or
    # called out as a dedicated antipattern category
    assert ("prd ↔ ui_guide" in lower or "arch ↔ ui_guide" in lower
            or "adr ↔ ui_guide" in lower or "audit" in lower)


def test_workflow_iteration_step_6_includes_ui_guide():
    body = _body()
    step6 = body[body.index("Step 6 —"):]
    # Iteration must now re-run UI_GUIDE (Step 13) alongside PRD (Steps 2+3),
    # ARCH (Step 8), and ADR (Step 11)
    assert "Step 13" in step6[:2500] or "UI_GUIDE" in step6[:2500]
    assert "UI_GUIDE.md" in step6[:2500]


def test_workflow_iteration_write_order_explicit_ui_guide():
    body = _body()
    step6 = body[body.index("Step 6 —"):]
    # Finding #3 from B-2 (carried into B-3, B-4): iteration write order must
    # be explicit, not implicit. Look for an enumerated step list mentioning
    # UI_GUIDE overwrite.
    assert "Iteration write order" in step6[:2500]
    overwrite_block = step6[:3000].lower()
    assert "overwrite" in overwrite_block
    assert "ui_guide.md" in overwrite_block


def test_workflow_iteration_step_6_quad_prompt_no_force():
    body = _body()
    step6 = body[body.index("Step 6 —"):]
    # V4 identity rule: "no" must exit cleanly, even after extension to 4 docs
    lower = step6[:1200].lower()
    assert ("no exits" in lower or "no →" in step6[:1200] or "no — done" in lower)
    # The yes-path option label must reflect the 4-doc surface
    assert ("all four" in lower or "four" in lower or "ui_guide" in lower)
