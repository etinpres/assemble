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


def _section(body: str, heading: str) -> str:
    """Return the body block from `heading` through the next sibling-or-shallower heading line.

    `heading` must include leading hash markers, e.g. ``"### Step 6"``. The
    function locates the heading, then scans forward and stops at the first
    heading line of equal-or-shallower depth (so a ``### Step 6`` slice ends
    on the next ``### ``, ``## ``, or ``# `` heading — whichever comes
    first). All tests in this file use this helper instead of ``body[:N]``
    window slices (Item C — test anchoring brittleness, B-4 retro #1,
    refactored to full coverage in v4-quality-pass-c-d). See
    ``docs/contributing/test-anchoring.md`` for the contributor convention.
    """
    start = body.index(heading)
    depth = len(heading) - len(heading.lstrip("#"))
    nl = body.find("\n", start)
    if nl == -1:
        return body[start:]
    cursor = nl + 1
    while cursor < len(body):
        next_nl = body.find("\n", cursor)
        line_end = next_nl if next_nl != -1 else len(body)
        line = body[cursor:line_end]
        if line.startswith("#"):
            line_depth = len(line) - len(line.lstrip("#"))
            if line_depth <= depth and not line.startswith(heading):
                return body[start:cursor]
        if next_nl == -1:
            break
        cursor = next_nl + 1
    return body[start:]


def test_skill_lives_at_expected_path():
    assert SKILL.exists(), f"missing: {SKILL}"


def test_skill_is_orchestrator_only():
    body = _body()
    assert "orchestrator-only" in body.lower()


def test_skill_step_5_is_deleted():
    """Spike I §8.2 카테고리 1: Step 5 (main-write artifact assembly) is
    deleted in Spike I — sub-agents now write directly via the lifecycle
    hook. The orchestrator no longer assembles or writes artifacts."""
    body = _body()
    assert "### Step 5" not in body, "Step 5 should be deleted in Spike I"


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
    # Spike I rewrite (commit 02d2237 + 9532dfa) compressed Steps 2/3 prose:
    # "single message" + "2 Agent calls" verbatim phrases collapsed into
    # "Fired in the same parallel message as Step 3 (true 2-way parallel...)"
    # — anchor on the surviving phrase that still proves parallel dispatch.
    step23 = body[body.index("### Step 2 — PRD body draft"):
                  body.index("### Step 4")]
    assert "parallel" in step23.lower()
    assert "2-way" in step23 or "two agent" in step23.lower()
    assert "AC bash" in step23 or "Acceptance Criteria" in step23


def test_workflow_step_3_explains_role_for_ac_bash():
    body = _body()
    # The AC bash bullet itself must name the role + fallback — not just
    # the count-twice heuristic, which passes on duplicate role-table rows
    # alone (B-1 retroactive review I2).
    # Spike I rewrite collapsed per-step role/fallback prose into a single
    # `## Sub-agent role mapping` table at the top of SKILL.md. The role
    # contract still exists; it just lives in the table now. Anchor on
    # the table presence + Step 2/3 rows referring to plan-implementation.
    table = body[body.index("## Sub-agent role mapping"):body.index("## Workflow")]
    assert table.count("plan-implementation") >= 2, (
        "Role table must reference plan-implementation for Steps 2 and 3"
    )
    # Plan/general-purpose fallback chain — surviving in the role mapping
    # block intro line ("All dispatches use `general-purpose`...") rather
    # than per-step prose.
    role_block = body[body.index("## Sub-agent role mapping"):body.index("## Workflow execution sequence")]
    assert "general-purpose" in role_block, (
        "Role mapping block must spell out general-purpose dispatch type"
    )


def test_workflow_question_6_now_active():
    body = _body()
    # The Phase B-1 Task 4 note ("skipped in Phase B-1 Task 4") is removed
    # in this task — question 6 is now live.
    assert "skipped in Phase B-1 Task 4" not in body


def test_workflow_step_4_second_opinion_review():
    body = _body()
    # Spike I rewrite renamed heading to "### Step 4 — PRD consistency review
    # (second-opinion)" and dropped the separate "#### Step 4b" sub-heading
    # (the verify-before-appending protocol survives as inline prose
    # references "Step 4b verify-before-appending protocol"). Use the
    # _section helper to slice the Step 4 block.
    assert "### Step 4 — PRD consistency review" in body
    step4 = _section(body, "### Step 4")
    assert "second-opinion" in step4
    # Review must explicitly demand flaws/rebuttals/triage, not bare
    # agreement. Compressed form references "triages each critique" —
    # treat triage as the surviving anchor.
    assert (
        "flaw" in step4.lower()
        or "rebut" in step4.lower()
        or "challenge" in step4.lower()
        or "critique" in step4.lower()
        or "triage" in step4.lower()
    )


def test_workflow_review_uses_role_mapping_fallback():
    # OBSOLETE-ANCHOR: Spike I rewrite removed the per-step preferred-agent
    # prose. The role mapping table at the top of SKILL.md is now the
    # single source of truth ("All dispatches use general-purpose"). The
    # Step 4 row in that table names `second-opinion` role. Verify the
    # contract via the role mapping table.
    body = _body()
    table = body[body.index("## Sub-agent role mapping"):body.index("## Workflow")]
    # Step 4 row carries the second-opinion role mapping
    step4_rows = [line for line in table.splitlines()
                  if line.startswith("| 4 ") or "prd_step4.md" in line]
    assert step4_rows, f"no Step 4 row in role table; table=\n{table}"
    assert "second-opinion" in " ".join(step4_rows), (
        "Step 4 row in role mapping table must name second-opinion"
    )


def test_workflow_step_6_iteration_prompt():
    body = _body()
    # Spike I rewrite split Step 6 into a parent `## Step 6 — iteration
    # round-trip` block (the user prompt + entry policy) and a child
    # `### Step 6 yes-path detail` block (the 5-step yes-path procedure).
    # Slice from `## Step 6` to capture both — _section helper would only
    # return the yes-path detail since `### Step 6 yes-path detail`
    # appears before the `## Step 6` header in body.index() lookup.
    step6 = _section(body, "## Step 6 — iteration round-trip")
    assert "iteration" in step6.lower()
    assert "AskUserQuestion" in step6
    # B-5 multi-iteration loop superseded the "one iteration" cap. The
    # iteration entry prompt is now the yes/no question — surviving
    # anchor is the iteration_count == 0 entry condition.
    assert "iteration_count == 0" in step6 or "한 차례 반복" in step6


def test_workflow_iteration_does_not_force_loop():
    body = _body()
    # Hard prohibition from spec section 10: never force the user into
    # multiple iterations. The workflow must mention that "no" exits.
    assert "no exits" in body.lower() or "no → " in body or "user can exit" in body.lower()


def test_workflow_iteration_has_exit_policy():
    """Step 6 must explicitly state the post-iteration exit policy. Without
    this contract, iteration behavior is unbounded.

    B-5: superseded the B-4 hard cap=1 ("exits unconditionally") with a
    multi-iteration loop. The contract now requires either the new cap
    phrase ('iteration cap (7)') or the canonical stop-state token
    ('cap-reached') to appear in body — both come from the multi-iteration
    loop block.
    """
    body = _body()
    assert "iteration cap (7)" in body or "cap-reached" in body


def test_skill_description_mentions_arch():
    from server import parse_skill_frontmatter
    fm = parse_skill_frontmatter(SKILL)
    desc = (fm.get("description") or "").upper()
    assert "ARCH" in desc, f"description does not mention ARCH: {fm.get('description')}"


def test_workflow_step_7_arch_interview():
    body = _body()
    # Anchor to heading to avoid false-positive on role-table row "| 7 |"
    assert "### Step 7" in body
    step7 = _section(body, "### Step 7")
    assert "AskUserQuestion" in step7
    # Gate B2.2 seeds: interview must ask about directory tree and data flow
    assert "directory" in step7.lower()
    assert "data flow" in step7.lower() or "data-flow" in step7.lower()


def test_workflow_step_8_arch_single_dispatch():
    body = _body()
    assert "Step 8" in body
    step8 = _section(body, "### Step 8")
    # Phase B spec §3: B-2 through B-4 are single-dispatch, not parallel.
    # Spike I rewrite collapsed the per-step "single dispatch" wording
    # into the role-mapping section ("Steps 8/11/13 are single-dispatch
    # first-pass"). The single-dispatch contract still exists but lives
    # outside the per-step section now — assert it via the role-mapping
    # block intro lines.
    role_block = body[body.index("## Sub-agent role mapping"):
                      body.index("## Workflow execution sequence")]
    assert "single-dispatch" in role_block, (
        "Role-mapping block must mark Steps 8/11/13 as "
        "single-dispatch first-pass"
    )
    assert "ARCHITECTURE.md" in step8
    # Spike I §8.2 카테고리 1: orchestrator dispatches sub-agent prompt
    # file; sub-agent writes the artifact and returns `WROTE:` on stdout.
    assert "prompts/arch_step8.md" in step8


def test_workflow_step_8_uses_subagent_wrote_convention():
    """Spike I §8.2 카테고리 1: With sub-agent path-only contract, the
    sub-agent writes the artifact directly (no main-Claude template
    substitution). The SKILL must document the `WROTE:` stdout
    convention as the dispatch contract for Step 8 (and all other
    dispatch steps).

    The convention lives in the central `### Step dispatch contract`
    block (Steps 2/3/4/8/11/13/9), not duplicated per step — assert
    that contract block exists and explicitly enumerates Step 8."""
    body = _body()
    contract = _section(body, "### Step dispatch contract")
    assert "WROTE:" in contract, (
        "Dispatch contract section missing `WROTE:` stdout convention "
        "(Spike I sub-agent return contract — replaces dogfood finding #1 "
        "split_sections logic now that sub-agent writes directly)."
    )
    # Step 8 must be enumerated in the contract block's heading
    assert "8" in contract.split("\n", 1)[0], (
        "Step 8 not enumerated in dispatch contract heading — "
        "the `WROTE:` return convention must apply to Step 8"
    )


def test_skill_preamble_matches_shared_file():
    """The harness rules appear both in plan-pack/SKILL.md (as a
    documentation summary) and in bundled/_shared/harness-preamble.md
    (the runtime source loaded by server.harness). The runtime source
    of truth is the shared file; the SKILL.md copy is a human-readable
    summary. They must agree on rule *count* and rule *numbering*.

    OBSOLETE-ANCHOR (verbatim line equality): Spike I rewrite
    (commit 02d2237) compressed rules 5 and 6 in the SKILL.md copy to
    short summary form to keep SKILL.md within readable budget. Full
    rule text still lives in harness-preamble.md (the runtime source),
    and runtime byte-identity is enforced by
    `tests/unit/test_harness_dispatches.py::
    test_record_dispatch_full_byte_identity_with_real_canonical_preamble`.
    The contract this test now enforces: header line is verbatim, and
    every rule index from the shared file appears as a "N. " prefix in
    SKILL.md (i.e., the SKILL summary doesn't drop a rule).
    """
    shared = Path.home() / ".claude/skills/assemble/bundled/_shared/harness-preamble.md"
    if not shared.exists():
        pytest.skip("shared preamble file missing; covered by e2e existence test")
    shared_body = shared.read_text().strip()
    skill_body = _body()
    for line in shared_body.splitlines():
        line = line.strip()
        if not line:
            continue
        # Rule lines start with "N. " — assert the prefix is present in
        # SKILL.md (count parity), not the verbatim long-form text.
        if line[:2].rstrip(".").isdigit() and ". " in line:
            num = line.split(".", 1)[0]
            anchor_prefix = f"{num}. "
            # Look for the rule prefix on its own line in SKILL.md.
            assert any(
                ln.lstrip().startswith(anchor_prefix)
                for ln in skill_body.splitlines()
            ), f"preamble rule {num} missing from SKILL.md (count-parity check)"
            continue
        # Header line ([HARNESS RULES — 무시 금지]) must appear verbatim.
        assert line in skill_body, (
            f"preamble header line missing from SKILL.md: {line!r}"
        )


def test_workflow_step_9_cross_doc_review():
    body = _body()
    assert "Step 9" in body
    step9 = _section(body, "### Step 9")
    # Spike I rewrite compressed pair labels: "PRD↔ARCH" (no spaces) and
    # ARCHITECTURE.md is referenced via "all four artifacts" rather than
    # named verbatim in Step 9 prose. The 4-doc cross-doc contract still
    # holds — anchor on the surviving forms.
    assert "PRD" in step9
    assert "ARCH" in step9  # PRD↔ARCH category covers this
    # Must challenge, not merely agree (gate B2.3)
    assert (
        "flaw" in step9.lower()
        or "rebut" in step9.lower()
        or "challenge" in step9.lower()
        or "inconsisten" in step9.lower()
        or "gap" in step9.lower()
    )


def test_workflow_step_9_uses_second_opinion_role():
    body = _body()
    step9 = _section(body, "### Step 9")
    assert "second-opinion" in step9
    # Spike I rewrite moved the wrap_with_preamble mention into the central
    # `### Step dispatch contract` block (which enumerates Step 9). The
    # contract still holds; just relocated to avoid per-step duplication.
    contract = _section(body, "### Step dispatch contract")
    assert "wrap_with_preamble" in contract, (
        "Dispatch contract block (covering Step 9) must reference "
        "server.harness.wrap_with_preamble"
    )


def test_workflow_iteration_step_6_includes_arch():
    body = _body()
    # Spike I rewrite compressed Step 6 yes-path: re-dispatch is now
    # named via prompt files (`arch_step8.md`) rather than "Step 8" or
    # "ARCHITECTURE.md" verbatim, and the verb is "re-dispatch" /
    # "overwrite" rather than "re-draft" / "re-runs". The contract is
    # preserved through the prompt-file naming (arch_step8.md == Step 8
    # ARCH dispatch, by table mapping).
    step6 = _section(body, "### Step 6 yes-path detail")
    assert "arch_step8.md" in step6, (
        "iteration yes-path must re-dispatch ARCH via arch_step8.md"
    )
    assert "ARCH" in step6  # via {{ARCH_TEXT}} placeholder + parallel-dispatch line
    assert ("re-dispatch" in step6.lower()
            or "overwrite" in step6.lower()
            or "re-draft" in step6.lower()
            or "re-runs" in step6.lower())


def test_workflow_iteration_has_explicit_write_order():
    """Dogfood finding #3: iteration write order was implicit. Step 6
    yes-path must show numbered write-order steps so the main Claude
    follows a deterministic sequence.

    Spike I rewrite (commit 02d2237) collapsed the per-doc enumerated
    overwrite list into a single sentence ("Each sub-agent overwrites
    its doc via write_run_artifact and returns WROTE: <path>"). The
    deterministic-sequence contract still holds — the yes-path is now
    numbered 1-5 and step 4 explicitly carries the overwrite verb.
    """
    body = _body()
    step6 = _section(body, "### Step 6 yes-path detail")
    # The yes-path is a numbered list; "overwrite" + "write_run_artifact"
    # together prove deterministic-sequence ownership without requiring
    # per-doc enumeration prose.
    assert "overwrites" in step6.lower() or "overwrite" in step6.lower()
    assert "write_run_artifact" in step6, (
        "Step 6 yes-path must reference write_run_artifact as the "
        "deterministic write surface (replaces enumerated write-order block)"
    )


def test_workflow_iteration_step_6_no_force_arch():
    body = _body()
    # Spike I rewrite split Step 6 into a parent `## Step 6 — iteration
    # round-trip` block (entry policy + no/yes bullets) and a child
    # `### Step 6 yes-path detail`. The "exits the workflow" semantic
    # anchor lives in the parent block; widen scope to capture it.
    step6 = _section(body, "## Step 6 — iteration round-trip")
    # V4 identity rule: "no" must exit cleanly.
    assert "exits the workflow" in step6.lower()


def test_skill_description_mentions_adr():
    from server import parse_skill_frontmatter
    fm = parse_skill_frontmatter(SKILL)
    desc = (fm.get("description") or "").upper()
    assert "ADR" in desc, f"description does not mention ADR: {fm.get('description')}"


def test_workflow_step_10_adr_interview():
    body = _body()
    assert "Step 10" in body
    step10 = _section(body, "### Step 10")
    assert "AskUserQuestion" in step10
    # Gate B3.2 seeds: interview must surface decisions, alternatives, tradeoffs
    lower = step10.lower()
    assert "decision" in lower
    assert "alternative" in lower or "rejected" in lower
    assert "tradeoff" in lower or "trade-off" in lower


def test_workflow_step_11_adr_single_dispatch():
    body = _body()
    assert "Step 11" in body
    step11 = _section(body, "### Step 11")
    # Phase B spec §3: B-2 through B-4 are single-dispatch, not parallel.
    # Spike I rewrite (commit 02d2237) hoisted the "single-dispatch" mark
    # into the role-mapping section ("Steps 8/11/13 are single-dispatch
    # first-pass"). Verify there.
    role_block = body[body.index("## Sub-agent role mapping"):
                      body.index("## Workflow execution sequence")]
    assert "single-dispatch" in role_block, (
        "Role-mapping block must mark Steps 8/11/13 as "
        "single-dispatch first-pass"
    )
    assert "ADR.md" in step11 or "ADR" in step11
    # Spike I §8.2 카테고리 1: orchestrator dispatches sub-agent prompt
    # file; sub-agent writes the artifact and returns `WROTE:` on stdout.
    assert "prompts/adr_step11.md" in step11
    # Decision count contract for gate B3.2 — survives in Step 10 interview
    # ("Three decisions = minimum") and Step 11 references "per decision".
    assert "decision" in step11.lower()


def test_workflow_step_9_includes_adr():
    body = _body()
    step9 = _section(body, "### Step 9")
    # The cross-doc review must now span ADR as well
    assert "ADR" in step9
    assert "ADR.md" in step9 or "ADR.md" in body[body.index("### Step 9"):body.index("### Step 6")]


def test_workflow_step_9_three_way_consistency():
    body = _body()
    step9 = _section(body, "### Step 9")
    # Must explicitly cover ARCH↔ADR decision integrity (per phase-b.md §6 B-3)
    lower = step9.lower()
    assert "decision" in lower
    # Spike I rewrite (commit 02d2237) compressed the pair-label block
    # to drop spaces around ↔ — "PRD↔ARCH" form. The 3-pair coverage
    # contract holds in compressed form. Anchor on the no-space variant.
    assert ("rationale" in lower or "reasoning" in lower
            or "missing" in lower or "traceability" in lower)
    window = step9
    assert "PRD↔ARCH" in window or "PRD ↔ ARCH" in window
    assert "ARCH↔ADR" in window or "ARCH ↔ ADR" in window
    assert "PRD↔ADR" in window or "PRD ↔ ADR" in window


def test_workflow_iteration_step_6_includes_adr():
    body = _body()
    # Spike I rewrite compressed Step 6 yes-path: ADR re-dispatch is named
    # via prompt file (`adr_step11.md`) rather than "ADR.md" verbatim.
    step6 = _section(body, "### Step 6 yes-path detail")
    assert "adr_step11.md" in step6, (
        "iteration yes-path must re-dispatch ADR via adr_step11.md"
    )
    assert "ADR" in step6  # via {{ADR_TEXT}} placeholder


def test_workflow_iteration_write_order_explicit_adr():
    body = _body()
    # Spike I rewrite (commit 02d2237) collapsed the "Iteration write
    # order" enumerated block. The deterministic-overwrite contract for
    # ADR survives via the parallel-dispatch line referencing
    # `adr_step11.md` and the "Each sub-agent overwrites its doc" sentence.
    step6 = _section(body, "### Step 6 yes-path detail")
    assert "overwrite" in step6.lower()
    assert "adr_step11.md" in step6, (
        "Step 6 yes-path must reference adr_step11.md as the ADR re-dispatch "
        "prompt (replaces verbatim ADR.md overwrite enumeration)"
    )

def test_workflow_iteration_step_6_no_force():
    body = _body()
    # Spike I rewrite — see test_workflow_iteration_step_6_no_force_arch.
    # "exits the workflow" lives in the parent `## Step 6` block, not the
    # `### Step 6 yes-path detail` child.
    step6 = _section(body, "## Step 6 — iteration round-trip")
    # V4 identity rule: "no" must exit cleanly, even after extension
    assert "exits the workflow" in step6.lower()


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
    step12 = _section(body, "### Step 12")
    assert "AskUserQuestion" in step12
    # Gate B4.1/B4.2 seeds: interview must surface visual identity, components, do/don't.
    lower = step12.lower()
    assert "visual" in lower or "tone" in lower or "aesthetic" in lower
    assert "component" in lower or "pattern" in lower
    assert "antipattern" in lower or "avoid" in lower or "don't" in lower or "do not" in lower


def test_workflow_step_13_ui_single_dispatch_inherits_plan_fix():
    body = _body()
    assert "Step 13" in body
    step13 = _section(body, "### Step 13")
    # Phase B spec §3: B-2 through B-4 are single-dispatch, not parallel.
    # Spike I rewrite hoisted the per-step "single dispatch" note into the
    # role-mapping block intro line.
    role_block = body[body.index("## Sub-agent role mapping"):
                      body.index("## Workflow execution sequence")]
    assert "single-dispatch" in role_block, (
        "Role-mapping block must mark Steps 8/11/13 as "
        "single-dispatch first-pass"
    )
    assert "UI_GUIDE.md" in step13 or "UI_GUIDE" in step13
    # Spike I §8.2 카테고리 1: orchestrator dispatches sub-agent prompt
    # file; sub-agent writes the artifact and returns `WROTE:` on stdout.
    assert "prompts/ui_step13.md" in step13
    # B-3 Finding #3 fix carried into Step 13: role mapping table is the
    # source of truth post Spike I rewrite. Assert the Step 13 row carries
    # plan-implementation role, and the role mapping block notes
    # general-purpose as the dispatch type.
    table = body[body.index("## Sub-agent role mapping"):body.index("## Workflow")]
    # The Step 13 row mentions ui_step13.md and uses plan-implementation role.
    ui_row = [line for line in table.splitlines()
              if line.startswith("| 13 ") or "ui_step13.md" in line]
    assert ui_row, f"no Step 13 row in role table; table=\n{table}"
    row_text = " ".join(ui_row).lower()
    assert "plan-implementation" in row_text
    # Spike I role mapping intro line: "All dispatches use general-purpose"
    assert "general-purpose" in table.lower()


def test_workflow_step_9_includes_ui_guide():
    body = _body()
    step9 = _section(body, "### Step 9")
    # The cross-doc review must now span UI_GUIDE as well.
    # Spike I rewrite compressed Step 9 prose to reference UI_GUIDE only
    # via pair-category labels (PRD↔UI_GUIDE, ARCH↔UI_GUIDE, ADR↔UI_GUIDE)
    # rather than spelling "UI_GUIDE.md" verbatim. The 4-doc coverage
    # contract holds — the UI_GUIDE token still appears in step9.
    assert "UI_GUIDE" in step9


def test_workflow_step_9_four_way_includes_antipattern_audit():
    body = _body()
    step9 = _section(body, "### Step 9")
    # Phase B-4 specific: Step 9 must include the design-audit category
    # (the cross-check between UI_GUIDE body and PRD design direction).
    # Spike I rewrite compressed Step 9 — the "antipattern" / "design
    # direction" verbatim phrases moved out to the dedicated step prompt
    # file (`prompts/cross_doc_step9.md`). Step 9 prose still names the
    # pair-category "PRD↔UI_GUIDE design audit" which encodes the same
    # contract.
    lower = step9.lower()
    assert "ui_guide" in lower or "ui guide" in lower
    # The 7-category enumeration in step9 must include design audit and
    # ARCH↔UI_GUIDE component coverage as new B-4 categories.
    assert "design audit" in lower or "ui_guide design" in lower, (
        "Step 9 must enumerate the PRD↔UI_GUIDE design audit category "
        "(B-4 antipattern + design direction cross-check)"
    )
    assert ("prd↔ui_guide" in lower or "prd ↔ ui_guide" in lower
            or "arch↔ui_guide" in lower or "arch ↔ ui_guide" in lower
            or "adr↔ui_guide" in lower or "adr ↔ ui_guide" in lower), (
        "Step 9 must enumerate at least one UI_GUIDE pair-label category"
    )


def test_workflow_iteration_step_6_includes_ui_guide():
    body = _body()
    step6 = _section(body, "### Step 6")
    # Iteration must now re-run UI_GUIDE (Step 13) alongside PRD (Steps 2+3),
    # ARCH (Step 8), and ADR (Step 11)
    assert "Step 13" in step6 or "UI_GUIDE" in step6
    assert "UI_GUIDE.md" in step6


def test_workflow_iteration_write_order_explicit_ui_guide():
    body = _body()
    # Spike I rewrite (commit 02d2237) collapsed the "Iteration write
    # order" enumerated block. The deterministic-overwrite contract for
    # UI_GUIDE survives via the parallel-dispatch line referencing
    # `ui_step13.md` and the "Each sub-agent overwrites its doc" sentence.
    step6 = _section(body, "### Step 6 yes-path detail")
    assert "overwrite" in step6.lower()
    assert "ui_step13.md" in step6, (
        "Step 6 yes-path must reference ui_step13.md as the UI_GUIDE "
        "re-dispatch prompt (replaces verbatim UI_GUIDE.md overwrite enumeration)"
    )


def test_workflow_iteration_step_6_quad_prompt_no_force():
    body = _body()
    # Spike I rewrite split Step 6: parent block (`## Step 6 — iteration
    # round-trip`) carries the "no" exit bullet, while the yes-path detail
    # child enumerates the 4-doc dispatch.
    step6 = _section(body, "## Step 6 — iteration round-trip")
    lower = step6.lower()
    # V4 identity rule: "no" must exit cleanly, even after extension to 4 docs.
    # Compressed form: "**no → done**: exits the workflow" (line 224 SKILL.md).
    assert ("no →" in step6 or "no — 종료" in step6 or "no exits" in lower
            or "exits the workflow" in lower)
    # The yes-path option label must reflect the 4-doc surface — Korean
    # "4-doc 재작성" or English "4-way" / mention of UI_GUIDE alongside
    # PRD/ARCH/ADR.
    assert ("4-doc" in lower or "4-way" in lower or "all four" in lower
            or "four" in lower or "ui_guide" in lower)


def test_workflow_iteration_scope_discipline():
    """B-4 dogfood Findings #4 + #5 fix — iteration must constrain
    sub-agents from introducing features/modules/screens not in PRD.

    Repro: B-4 iter1 surfaced UI_GUIDE adding dark-mode tokens (deferred
    in ADR) and ARCH adding `edit`/`toggleAll` actions without PRD signal,
    which UI_GUIDE then composed Screen C around. Both exited unresolved
    at the 1-iteration cap. The fix is a documented "scope discipline"
    constraint in Step 6 yes-path that the orchestrator must apply when
    constructing iteration sub-agent prompts.
    """
    body = _body()
    step6 = _section(body, "### Step 6")
    # Step 6 must document scope discipline for iteration
    lower = step6.lower()
    assert ("scope discipline" in lower or "scope creep" in lower), (
        "Step 6 missing 'scope discipline' / 'scope creep' wording — "
        "B-4 dogfood Findings #4 + #5 fix not applied"
    )
    # PRD must be named as the scope authority (since drift was that
    # ARCH/UI_GUIDE iter1 added features without PRD signal)
    assert "prd" in lower, "scope discipline must reference PRD as authority"
    # Must explicitly forbid introducing new features in iteration
    assert ("do not introduce" in lower
            or "must not introduce" in lower
            or "must not add" in lower), (
        "scope discipline must explicitly forbid introducing new features"
    )


# -------------------------------------------------------------------------
# Phase B-5 contracts (multi-iteration loop)
# -------------------------------------------------------------------------


def test_step6_has_stop_condition_contract():
    """B-5 Item A: the multi-iteration stop condition contract must be
    documented verbatim in SKILL.md.

    Spike I rewrite (commit 02d2237) extracted the multi-iteration loop
    spec out of Step 6 yes-path detail into its own top-level section
    `## Multi-iteration loop with stop conditions`. The verbatim
    contract phrase still appears there; check the body directly.

    The contract sentence wraps across lines inside a markdown blockquote
    (`> `-prefixed lines), so collapse whitespace + blockquote markers
    before substring matching.
    """
    body = _body()
    # Strip blockquote markers and collapse whitespace so the wrapped
    # contract sentence becomes a single contiguous string.
    flat = " ".join(line.lstrip("> ").strip() for line in body.splitlines())
    assert "two consecutive iterations both satisfy" in flat, (
        "Multi-iteration loop section missing the verbatim stop condition "
        "contract phrase — B-5 Item A spec drift"
    )
    assert "RESOLVED ≥ 80% AND NEW ≤ 0" in flat, (
        "Multi-iteration loop section missing RESOLVED/NEW threshold — "
        "B-5 Item A spec drift"
    )


def test_step6_has_iteration_state_contract():
    """B-5 Item A: SKILL.md must reference runs/<rid>/iteration_state.json.

    Spike I rewrite extracted the iteration-state-tracking block out of
    Step 6 into the top-level `## Multi-iteration loop with stop
    conditions` section.
    """
    body = _body()
    assert "runs/<rid>/iteration_state.json" in body, (
        "Multi-iteration loop section missing the "
        "runs/<rid>/iteration_state.json contract — B-5 Item A spec drift"
    )


def test_step6_has_iteration_scope_discipline_preserved():
    """B-5 Item A regression guard: the 33b3056 iteration scope discipline
    block (B-4 fix) must remain verbatim — it now applies to every iteration
    in the loop, not only the first."""
    body = _body()
    step6 = _section(body, "### Step 6")
    assert "PRD `## Core features` is the authoritative scope" in step6, (
        "Iteration scope discipline block (33b3056) was modified or "
        "removed during the B-5 multi-iteration rewrite — regression"
    )


def test_step6_step4_cites_platform_limit_research():
    """B-5 Item B-1: Step 6 step 4 must cite docs/research/2026-04-29-platform-limit.md
    so the parallel-dispatch caveat is empirically grounded, not folklore."""
    body = _body()
    step6 = _section(body, "### Step 6")
    assert "docs/research/2026-04-29-platform-limit.md" in step6, (
        "Step 6 step 4 missing platform-limit research citation — "
        "B-5 Item B-1 caveat tightening spec drift"
    )


def test_steps_2_3_have_preamble_byte_identity_contract():
    """B-5 Item B-2: preamble byte-identity contract.

    OBSOLETE-ANCHOR: Spike I rewrite (commit 02d2237) removed the
    verbatim "every dispatched prompt's preamble block, when isolated
    and hashed, MUST match" sentence from SKILL.md. The byte-identity
    contract is now enforced at runtime via
    `tests/unit/test_harness_dispatches.py` — see in particular
    `test_recorded_preamble_sha256_matches_canonical` (pins
    preamble_sha256 == canonical_preamble_sha256()) and
    `test_record_dispatch_full_byte_identity_with_real_canonical_preamble`.
    The SKILL.md still references `wrap_with_preamble` in both Step 2
    (via the dispatch contract block which enumerates Step 2) and the
    intro paragraph — that prose anchor proves the contract surface.
    """
    body = _body()
    # Surviving prose anchor: Step 2 dispatch must go through wrap_with_preamble
    # (named in the central dispatch contract that explicitly covers Step 2).
    contract = _section(body, "### Step dispatch contract")
    assert "Steps 2" in contract or " 2/" in contract, (
        "Step 2 must be enumerated in the dispatch contract block"
    )
    assert "wrap_with_preamble" in contract, (
        "Dispatch contract block (covering Step 2) must reference "
        "server.harness.wrap_with_preamble — the byte-identity contract "
        "surface. Verbatim byte-identity prose moved to runtime tests in "
        "test_harness_dispatches.py."
    )


# -------------------------------------------------------------------------
# Spike I §8.2 카테고리 1: sub-agent prompt path-only contract
# -------------------------------------------------------------------------


def test_prompts_have_magic_marker():
    """Spike I §8.2 카테고리 1: every sub-agent dispatch prompt must carry
    the `ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE` magic marker (so the hook v1
    passthrough recognises legitimate dispatches) and document the
    `WROTE:` stdout return convention.

    Covers all 7 dispatch prompts (excludes `iter_emphasis.md` — that's
    a prompt fragment used by the orchestrator's iteration AskUserQuestion
    flow, not a sub-agent dispatch payload).
    """
    plan_pack = Path.home() / ".claude/skills/assemble/bundled/plan-pack/prompts"
    for fname in ["prd_step2.md", "prd_step3.md", "prd_step4.md",
                  "arch_step8.md", "adr_step11.md", "ui_step13.md",
                  "cross_doc_step9.md"]:
        body = (plan_pack / fname).read_text()
        assert "ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE" in body, (
            f"{fname} missing magic marker for hook v1 passthrough"
        )
        assert "WROTE:" in body, f"{fname} missing WROTE: stdout convention"


def test_skill_md_documents_record_dispatch_signature():
    """Spike II F2: SKILL.md must spell out record_dispatch's exact signature.

    B-6 dogfood: main inferred `role=` kwarg from the Sub-agent role mapping
    table column header → TypeError on first call. Grep ensures the verbatim
    signature + `No role kwarg` warning are present.
    """
    text = (Path.home() / ".claude/skills/assemble/bundled/plan-pack/SKILL.md").read_text(encoding="utf-8")
    # Verbatim signature parts
    assert "record_dispatch(" in text
    assert "subagent_type" in text and "wrote_path" in text
    # No-role warning sentence (catches F2 regression)
    assert "kwarg 없음" in text  # 새 시그니처 문장에만 등장
    assert "TypeError" in text


def test_skill_md_step9_uses_update_iteration_state():
    """Spike II F15: Step 9 must instruct main to use server function."""
    text = (Path.home() / ".claude/skills/assemble/bundled/plan-pack/SKILL.md").read_text(encoding="utf-8")
    assert "update_iteration_state" in text
    # Both Step 9 detail + Multi-iteration loop wording reference it
    assert text.count("update_iteration_state") >= 2
    # And the §CRITICAL ban on sub-agent metadata delegation is reinforced
    assert "do not" in text.lower() or "위임 금지" in text


def test_skill_md_rule5_includes_loanword_examples():
    """Spike II F3: Rule 5 head에 외래어 표기 사례."""
    text = (Path.home() / ".claude/skills/assemble/bundled/plan-pack/SKILL.md").read_text(encoding="utf-8")
    for sample in ("architecture→아키텍처", "family→패밀리", "top-level→최상위", "recommended→추천"):
        assert sample in text, f"missing: {sample}"


def test_skill_md_korean_label_policy_section():
    """Spike II F4: (추천) 통일 정책이 명시."""
    text = (Path.home() / ".claude/skills/assemble/bundled/plan-pack/SKILL.md").read_text(encoding="utf-8")
    assert "Korean label policy" in text or "라벨 정책" in text
    assert "(추천)" in text
    assert "(승인)" in text  # 잘못된 사례 명시


def test_skill_md_step10_call5_call6_explicit():
    """Spike II F6: Call 5 / Call 6 형태 명확."""
    text = (Path.home() / ".claude/skills/assemble/bundled/plan-pack/SKILL.md").read_text(encoding="utf-8")
    assert "Call 5" in text and "Call 6" in text
    # Call 5 shape: single call, 3 sub-questions
    assert "single" in text.lower() or "*single*" in text or "1 AskUserQuestion call" in text
    # Call 6 shape: 3 calls
    assert "3 separate" in text or "3 AskUserQuestion calls" in text


def test_skill_md_step10_min_selected_3():
    """Spike II F5: gate B3.2 — minSelected 3 강제."""
    text = (Path.home() / ".claude/skills/assemble/bundled/plan-pack/SKILL.md").read_text(encoding="utf-8")
    assert "minSelected: 3" in text or "minSelected=3" in text or "minSelected`: 3" in text
    assert "maxSelected: 5" in text or "maxSelected=5" in text or "maxSelected`: 5" in text
    # main count validation
    assert "최소 3개" in text or "verify the user selected" in text


def test_skill_md_step12_u2_u3_exactly_3():
    """Spike II F7: U2/U3 minSelected:3, maxSelected:3 강제."""
    text = (Path.home() / ".claude/skills/assemble/bundled/plan-pack/SKILL.md").read_text(encoding="utf-8")
    # U2/U3 specific schema
    assert "minSelected: 3, maxSelected: 3" in text or "minSelected=3, maxSelected=3" in text
    # Main verification logic
    assert "4 answers" in text or "user supplied 4+" in text or "4개" in text


def test_cross_doc_prompt_enforces_counts_schema():
    """Spike II F10: cross_doc_step9 prompt에 COUNTS schema verbatim."""
    text = (Path.home() / ".claude/skills/assemble/bundled/plan-pack/prompts/cross_doc_step9.md").read_text(encoding="utf-8")
    assert "COUNTS: resolved=" in text
    assert "unresolved=" in text and "new=" in text
    # Wrong-keys 거부 사례
    assert "NEW=" in text or "no different keys" in text


def test_skill_md_step9_includes_counts_regex():
    """Spike II F10: SKILL.md Step 9 에 main parsing regex pin."""
    text = (Path.home() / ".claude/skills/assemble/bundled/plan-pack/SKILL.md").read_text(encoding="utf-8")
    assert r"COUNTS: resolved=\d+ unresolved=\d+ new=\d+" in text


def test_iter_emphasis_uses_per_doc_substitution():
    """Spike II F14: iter_emphasis 가 single-doc placeholder 패턴."""
    prompt = (Path.home() / ".claude/skills/assemble/bundled/plan-pack/prompts/iter_emphasis.md").read_text(encoding="utf-8")
    assert "{{DOC_NAME}}" in prompt
    assert "{{EMPHASIS_SECTION_TITLE}}" in prompt or "{{EMPHASIS_SECTION_BODY}}" in prompt
    # Old multi-doc placeholders should NOT all be present (4-doc full substitution removed)
    bad = sum(p in prompt for p in ("{{PRD_TEXT}}", "{{ARCH_TEXT}}", "{{ADR_TEXT}}", "{{UI_TEXT}}"))
    assert bad <= 1, "iter_emphasis should not embed all 4 doc bodies — F14 압축"


def test_skill_md_step6_yespath_uses_per_doc_emphasis():
    """SKILL.md Step 6 yes-path detail 본문도 per-doc 패턴 명시."""
    text = (Path.home() / ".claude/skills/assemble/bundled/plan-pack/SKILL.md").read_text(encoding="utf-8")
    assert "{{DOC_NAME}}" in text
    assert "Per-doc emphasis" in text or "per-doc" in text.lower()


def test_step6_options_are_korean_only():
    """C3 — Step 6 entry/exit options must not contain '4-doc' or 'cross-doc'
    English tokens. Code identifiers (DOC_NAME, prompt filenames) are exempt."""
    from pathlib import Path
    skill = (
        Path.home() / ".claude/skills/assemble/bundled/plan-pack/SKILL.md"
    ).read_text()
    # Find AskUserQuestion option blocks (lines starting with '> options:')
    option_lines = [
        line for line in skill.splitlines()
        if line.lstrip().startswith("> options:")
    ]
    assert option_lines, "no AskUserQuestion option blocks found in SKILL.md"
    for line in option_lines:
        assert "4-doc" not in line, f"4-doc in: {line}"
        assert "cross-doc" not in line, f"cross-doc in: {line}"
