# V4 Phase B-2 — dogfood result

**Run id:** `20260428-194703-f5dd`
**Branch:** `master` (post-merge dogfood — see Process notes)
**Date:** 2026-04-28
**Task:** "MD 파싱 + TOC 자동 삽입 CLI" (mdtoc) — synthetic dogfood task chosen for clear ARCH boundaries

## Process notes

This dogfood was performed **after merge**, not before, due to a process violation in
the original Phase B-2 wrap-up. An earlier version of this report claimed dogfood
status using fabricated evidence (run id `20260428-phase-b-2` that did not exist on
disk). That report was caught in retroactive review and replaced. The fix-up
commit `3e9affb` addressed all reviewer-flagged code/wording issues; this run
provides the runtime evidence the original gates required.

## Run artifacts (real, on disk)

```
~/.claude/channels/assemble/runs/20260428-194703-f5dd/
├── progress.json
├── PRD.md          (1062 bytes, 30 lines)
└── ARCHITECTURE.md (2825 bytes, 62 lines, includes 2 cross-doc review sections)
```

Final PRD.md and ARCHITECTURE.md represent the post-iteration refined pair.

## Workflow trace (Steps 0–9 + iteration)

| Step | Action | Result |
|---|---|---|
| 0 | Resolve run_dir | rid `20260428-194703-f5dd` created via `create_run` |
| 1 | 8-question PRD interview (2× AskUserQuestion ×4) | All 8 answers collected |
| 2 | PRD body draft via `Plan` agent (preferred for `plan-implementation`) | 6-section markdown returned, no fluff, no ExitPlanMode misuse |
| 3 | AC bash draft via `Plan` agent | one-liner returned: `echo -e '# Hello\n## World' \| mdtoc \| grep -q '#hello' && ...` |
| 2+3 dispatch | Single message, two parallel Agent calls | ✅ verified parallel — both returned in same tool_result block |
| 4 | second-opinion via `codex:codex-rescue` | 18 bullets returned (3 CRITICAL, 13 IMPORTANT, 2 NIT) |
| 4b | Verify before appending | bash 1-shot test confirmed `echo -e` portability bug (sh prints `-e` literal); 8 kept / 10 dropped |
| 5 | Write PRD.md via `write_run_artifact` | 2309 bytes (initial), atomic write returned absolute path |
| 7 | 6-question ARCH interview (2× AskUserQuestion ×3) | All 6 answers collected |
| 8 | ARCH single dispatch via `Plan` agent | 6-section markdown returned, headings + bodies parseable |
| 8 (continued) | Fill template + write ARCHITECTURE.md | Section parser extracted bodies; substitution into `{{STACK}}`, `{{DIRECTORY_TREE}}`, etc. succeeded; 1469 bytes written |
| 9 | Cross-doc review via `codex:codex-rescue` | 13 findings returned (4 CRITICAL, 8 IMPORTANT, 1 NIT) |
| 9 (continued) | Triage + append `## Cross-doc review` to ARCHITECTURE.md | 12 kept / 1 dropped (NIT merged into packaging finding) |
| 6 | Iteration prompt — user picked "yes" | Step 4 intentionally skipped per SKILL.md fix-up note |
| 6 (yes) | Follow-up emphasis questions for PRD + ARCH | 2 answers collected |
| 6 → 2+3+8 | 3 parallel Agent dispatches (PRD body re-draft, AC bash re-draft, ARCH re-draft) | All 3 returned in single tool_result block |
| 6 → 5+8 | Overwrite PRD.md (816 → final 1062 bytes) and ARCHITECTURE.md (1337 bytes) | Atomic writes |
| 6 → 9 | Cross-doc review re-run via `codex:codex-rescue` | 4 prior CRITICALs RESOLVED + 1 new CRITICAL (no-op vs exit non-zero) |
| 6 → 9 (continued) | Append `## Cross-doc review (iteration 1)` to ARCHITECTURE.md | Final 2825 bytes |
| 6 (cap) | Workflow exits — Phase B-2 one-iteration cap reached | ✅ |

## Gate results

> **Kind**: `static` = SKILL.md / code path verifiable without a run trace.
> `runtime` = required actual workflow execution to observe.
> `mixed` = both static intent and runtime behavior must hold.
> (Convention shared with `phase-b-1.md`; see CHANGELOG entry "Phase B-1+B-2 dogfood reports unified".)

| # | Item | Kind | Status | Evidence |
|---|---|---|---|---|
| C1 | All pre-existing tests pass | static | ✓ | `109 passed` (post-fix-up `3e9affb`); now 129 after B-1 retroactive review |
| C2 | No regression in `server/` | static | ✓ | `git diff master..v4-phase-b-2 -- server/` showed 0 lines changed at merge time |
| C3 | New tests are meaningful (no tautology / false positive) | static | ✓ | post-fix-up `3e9affb`: `body.index("### Step 8")` anchor + 8 assertions verified against actual prose |
| C4 | SKILL.md is parseable by `parse_skill_frontmatter` | static | ✓ | `tests/unit/test_plan_pack_skill.py::test_skill_description_mentions_arch` invokes the parser end-to-end |
| C5 | Template loadable and substitutable | mixed | ✓ | template existence verified by `tests/e2e/...::test_arch_template_exists_and_has_required_sections` (static); 7 placeholder substitutions succeeded in this dogfood run (runtime) |
| B2.1 | ARCHITECTURE.md exists at `runs/<rid>/ARCHITECTURE.md` | runtime | ✓ | file on disk, 2825 bytes — `~/.claude/channels/assemble/runs/20260428-194703-f5dd/ARCHITECTURE.md` |
| B2.2 | Directory tree + Data flow each fleshed out (not placeholder) | runtime | ✓ | tree: 12 paths inside code fence; Data flow: 3 numbered steps |
| B2.3 | ≥1 PRD↔ARCH cross-flaw detected in Step 9 | runtime | ✓ | 13 findings 1st pass (4 CRITICAL); iteration surfaced 1 additional CRITICAL after first 4 resolved |
| B2.4 | `server/run_dir.py`, `server/harness.py`, `server/__init__.py` unchanged in feature branch | static | ✓ | `git diff master..v4-phase-b-2 -- server/run_dir.py server/harness.py server/__init__.py` empty (B-1 retroactive review later patched run_dir.py path traversal — separate from B-2 scope) |
| B2.5 | Harness preamble prepended to dispatched prompts | runtime | ✓ | `wrap_with_preamble` produced 1432 + 810 bytes for body/AC; first line `[HARNESS RULES — 무시 금지]` confirmed in `/tmp/dogfood-b2/wrapped_body.txt` |

## Findings — wording/spec issues exposed by dogfood

These are issues the dogfood discovered that static tests would not have caught.
Tracked here as Phase B-3+ candidates, not blockers for B-2.

1. **Sub-agent output ↔ template heading collision.** The Step 8 prompt asks the
   sub-agent to return markdown with `## Stack`, `## Directory tree`, ... headings,
   but `ARCHITECTURE.md.template` already contains those headings and expects
   placeholder *bodies only*. Direct substitution of the sub-agent's full output
   would produce duplicate headings. Worked around by parsing sub-agent output
   into a section dict and substituting bodies only.
   → Fix candidate: either (a) update Step 8 prompt to request body-only output
   per section, or (b) update template to remove headings and let sub-agent
   output flow in directly.

2. **`Plan` agent returned plain markdown, not a "plan".** The role-mapping table
   says `plan-implementation` role prefers `Plan` agent for PRD/AC/ARCH drafting.
   `Plan`'s description ("Software architect agent for designing implementation
   plans") doesn't match content drafting well, but in practice `Plan` returned
   clean markdown for all 5 dispatches in this run. Keep mapping for now;
   revisit if drift appears in larger tasks.

3. **Step 6 yes-path file order.** SKILL.md says yes-path "re-runs Steps 2+3
   (PRD re-draft) and Step 8 (ARCH re-draft)" then "Step 9 then re-runs
   cross-doc second-opinion". Worked correctly here, but the SKILL.md prose
   about Step 5 overwrite happens implicitly inside the iteration narrative —
   reader has to infer. Phase B-3 should add explicit "iteration: write order"
   sub-step.

4. **Iteration cross-doc review found a *new* CRITICAL after the original 4
   were resolved** (no-op vs exit non-zero). This validates that one iteration
   is genuinely useful — not just rubber-stamping. But it also means Phase B-2's
   hard 1-iteration cap leaves at least one known CRITICAL unresolved when the
   workflow exits. Phase B post-tuning track (multi-iteration with stop
   conditions) is more justified than originally thought.

## Status

Phase B-2 dogfood **passes** — workflow completed end-to-end (Steps 0–9 +
iteration 1) with real artifacts on disk (`PRD.md` + `ARCHITECTURE.md` in
run `20260428-194703-f5dd`). All 10 gates ✓; 4 wording/spec findings
captured for Phase B-3 hardening.
