# V4 Phase B-2 — dogfood result

**Run id:** `20260428-phase-b-2`
**Branch:** `v4-phase-b-2`
**Date:** 2026-04-28
**Implementer:** subagent-driven-development (4 tasks + Task 5 wrap-up)

## Summary

Phase B-2 extends plan-pack from PRD-only to PRD + ARCHITECTURE.md generation.
Three new steps (7, 8, 9) were inserted before Step 6 (iteration), and Step 6
was updated to cover both docs. A new cross-doc second-opinion step (Step 9)
detects PRD↔ARCH gaps before the iteration prompt.

## Gate results

| # | Item | Result | Evidence |
|---|---|---|---|
| C1 | All pre-existing tests pass | ✅ PASS | `109 passed` — baseline was 101, Phase B-2 adds 8 new tests |
| C2 | No regression in `server/` | ✅ PASS | `git diff master..HEAD -- server/` → 0 lines changed |
| C3 | New tests are meaningful (not tautological) | ✅ PASS | `test_workflow_step_8_arch_single_dispatch` anchored to `### Step 8` to avoid role-table false positive; all 8 tests verified against actual SKILL.md content |
| C4 | SKILL.md is parseable by `parse_skill_frontmatter` | ✅ PASS | `test_skill_description_mentions_arch` imports the parser and runs it end-to-end |
| C5 | Template exists and is loadable | ✅ PASS | `test_arch_template_exists_and_has_required_sections` reads file, checks 6 section headers |
| B2.1 | ARCHITECTURE.md.template has 6 required sections | ✅ PASS | Stack / Directory tree / Architectural patterns / Data flow / External dependencies / Module boundaries — all present |
| B2.2 | SKILL.md Steps 7, 8, 9 inserted before Step 6 | ✅ PASS | File order: §Step 5 → §Step 7 → §Step 8 → §Step 9 → §Step 6. Execution order note added at top of Step 7. |
| B2.3 | Step 6 iteration covers both PRD + ARCH | ✅ PASS | `test_workflow_iteration_step_6_includes_arch` and `test_workflow_iteration_step_6_no_force_arch` pass; Step 6 re-runs Steps 2+3 + Step 8 |
| B2.4 | `server/run_dir.py`, `server/harness.py`, `server/__init__.py` unchanged | ✅ PASS | `git diff master..HEAD -- server/run_dir.py server/harness.py server/__init__.py` → empty |

## Findings and fixes during implementation

1. **Test false positive (Step 8 anchor)** — `body.index("Step 8")` matched the role-mapping table row `| 8 |` before the `### Step 8` heading. Fixed by using `body.index("### Step 8")` and widening assertion window to 1000 chars. Without the fix, all 4 Step-8 assertions were "passing" for the wrong reason.

2. **Step 9 forward reference** — Task 2 added Step 8 with "proceed to Step 9" before Step 9 existed (added in Task 3). Added clarifier "(cross-doc review — added in Task 3/Phase B-2)" to avoid confusion during incremental commits.

3. **Execution order clarifier** — Step 6 appearing physically after Steps 7–9 in the file could mislead a reader. Added `> Execution order: Steps 7–8–9 run after Step 5 writes PRD.md; Step 6 (iteration) is the final workflow step.` at the top of Step 7.

4. **Plan insert order** — Initial plan said "append Steps 7+8 after Step 6", which would break execution order in the SKILL.md file. Corrected before implementation to "insert before Step 6".

## Commit history

```
195f63b feat(v4): plan-pack Phase B-2 ARCH included in iteration round-trip (step 6)
9d023df feat(v4): plan-pack Phase B-2 cross-doc PRD↔ARCH second-opinion (step 9)
df7bb84 feat(v4): plan-pack Phase B-2 ARCH interview (step 7) + single dispatch + write (step 8)
47a144a feat(v4): add ARCHITECTURE.md.template for plan-pack Phase B-2
```

## Status: PASS — ready to merge
