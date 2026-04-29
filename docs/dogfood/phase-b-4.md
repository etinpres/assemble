# V4 Phase B-4 — dogfood result

**Run id:** `20260429-103152-e35b`
**Branch:** `v4-phase-b-4` (pre-merge)
**Date:** 2026-04-29 (first-pass + iteration 1)
**Task used:** `V4 Phase B-4 dogfood — minimal todo SPA (localStorage)` (synthetic vanilla-DOM SPA for UI_GUIDE exercising)

## Run artifacts (real, on disk)

```
~/.claude/channels/assemble/runs/20260429-103152-e35b/
├── progress.json   (477 bytes)
├── PRD.md          (3781 bytes, 28 lines — iter1 overwritten; first-pass had ## Review notes appended)
├── ARCHITECTURE.md (4146 bytes, 62 lines — iter1 overwritten)
├── ADR.md          (8295 bytes, post-iter1 — first-pass + iteration 1 cross-doc reviews appended)
└── UI_GUIDE.md     (9359 bytes, 109 lines — iter1 overwritten)
```

Final files represent the post-iteration-1 refined quadruple. PRD's first-pass `## Review notes` (Step 4 output) is intentionally discarded on iteration overwrite (per write-order step 5; cross-doc review surface lives entirely on ADR.md). ADR.md carries both `## Cross-doc review` (first-pass) and `## Cross-doc review (iteration 1)` sections.

## Workflow trace (Steps 0–13 + iteration 1)

| Step | Action | Result |
|---|---|---|
| 0 | Resolve run_dir | rid `20260429-103152-e35b` created via `create_run` (sequence `[plan]` only) |
| 1 | 8-question PRD interview (2× AskUserQuestion ×4) | All 8 answers collected (Korean) |
| 2 | PRD body draft (Plan-fix preferred path: `general-purpose`) | 6 sections returned cleanly, no `### Critical Files` drift (B-3 Finding #3 fix verified) |
| 3 | AC bash draft (sequential after Step 2 — process deviation, see Findings #1) | One-liner returned; weak (review surfaces 7 CRITICAL issues) |
| 4 | second-opinion via `codex:codex-rescue` | 21 bullets (7 CRITICAL, 10 IMPORTANT, 4 NIT) |
| 4b | Verify before appending (1 dropped: IMPORTANT #16 false alarm — node -e body IS double-quoted) | 20 kept / 1 dropped |
| 5 | Write PRD.md via `write_run_artifact` | First-pass: 4446 bytes (template + Review notes section appended) |
| 7 | 6-question ARCH interview (2× AskUserQuestion ×3) | All 6 answers collected |
| 8 | ARCH single dispatch (general-purpose) + section-parse + write | 2233 bytes ARCH body, all 6 sections populated |
| 10 | 6-question ADR interview (2× AskUserQuestion ×3) | All 6 answers collected (D1–D3 titles, D4 alternatives, D5 tradeoffs, D6 risks) |
| 11 | ADR single dispatch (general-purpose) + template-fill + write | 6209 bytes ADR with 3 decisions × 5 sub-headings; gates B3.2/B3.3 ✓ (decisions=3 tradeoffs=3 rejected=3, zero TBD/TODO/미정) |
| 12 | 6-question UI_GUIDE interview (2× AskUserQuestion ×3) | All 6 answers collected (U1–U3 visual/screens/components, U4–U6 colors/type/antipattern emphasis) |
| 13 | UI_GUIDE single dispatch (general-purpose) + template-fill + write | First-pass: 8497 bytes UI_GUIDE with all 5 sections; gate B4.3 ✓ (no antipattern keywords in body), B4.5 ✓ (zero TBD/TODO/미정), B4.1 ✓ (8 antipattern bullets in template ≥6) |
| 9 | 4-way cross-doc review via `codex:codex-rescue` | 12 findings: 2 PRD↔ARCH + 2 ARCH↔ADR + 2 PRD↔ADR + 3 PRD↔UI_GUIDE (1 CRITICAL — keyboard-first vs hover-only delete) + 2 ARCH↔UI_GUIDE + 1 ADR↔UI_GUIDE (gate B3.5 carry-over: 6/6 categories ✓; gate B4.2 ✓) |
| 9 (cont.) | Triage + append `## Cross-doc review` to ADR.md | 12 kept / 0 dropped (all internal-contradiction or spec-gap claims; no runtime tests) — first-pass ADR.md grew to 6119 bytes |
| 6 | Iteration prompt — user picked **yes — refine all four** | Yes-path entered |
| 6 (yes) | Follow-up emphases (4 questions, one per doc) | PRD: keyboard tests + localStorage direct verify / ARCH: data flow → store.commit() + clearCompleted / ADR: Decision 3 Tradeoffs explicit focus pattern + Future ADRs / UI_GUIDE: hover-delete → keyboard-first |
| 6 → 2+3+8+11+13 | 5 sequential dispatches (PRD body → AC bash → ARCH → ADR → UI_GUIDE) — process deviation, see Findings #1 | All returned cleanly; Plan-fix preferred-path holds across all dispatches |
| 6 (write order steps 5–8) | Step 5 overwrites PRD.md (3781 bytes) → Step 8 overwrites ARCHITECTURE.md (4146 bytes) → Step 11 overwrites ADR.md (6216 bytes; old `## Cross-doc review` discarded per step 7 contract) → Step 13 overwrites UI_GUIDE.md (9359 bytes) | All four overwritten atomically |
| 6 → 9 | Step 9 re-runs on refreshed quadruple via `codex:codex-rescue` | 12/12 RESOLVED + 2 NEW (1 IMPORTANT [PRD↔UI_GUIDE] inline editing screen vs PRD core features + 1 NIT [ADR↔UI_GUIDE] dark-mode tokens forward-shadow) |
| 6 → 9 (cont.) | Append `## Cross-doc review (iteration 1)` to ADR.md (per iteration suffix mandatory) | 14 entries (12 RESOLVED summaries + 2 NEW) — final ADR.md 8295 bytes |
| 6 (cap) | Workflow exits — Phase B-4 one-iteration cap | ✅ |

## Gate results

> **Kind**: `static` = SKILL.md / code path verifiable without a run trace.
> `runtime` = required actual workflow execution to observe.
> `mixed` = both static intent and runtime behavior must hold.

| # | Item | Kind | Status | Evidence |
|---|---|---|---|---|
| C1 | All pre-existing tests pass | static | ✓ | `147 passed in 3.09s` (138 master + 1 Task 1 + 3 Task 2 + 2 Task 3 + 3 Task 4 = 147; matches plan progression) |
| C2 | No regression in `server/` | static | ✓ | `git diff master..v4-phase-b-4 -- server/` empty (gate B4.4 carry-over) |
| C3 | New tests are meaningful | static | ✓ | All 9 new tests grep-anchored on `### Step N`/`Step N` headings; Task 2 test 3 uses role-table slice for the Step 13 row preferred-column assertion (B-3 Finding #3 swap lock-in) |
| C4 | SKILL.md is parseable by `parse_skill_frontmatter` | static | ✓ | `test_skill_description_mentions_ui_guide` invokes parser end-to-end and PASSES |
| C5 | Templates loadable + substitutable | mixed | ✓ | UI_GUIDE.md.template + ADR.md.template + ARCHITECTURE.md.template + PRD.md.template all loaded from disk; section-parse + placeholder-substitute succeeded for all 4 docs in both first-pass and iteration |
| B4.1 | UI_GUIDE.md exists with antipattern table (≥6 items) | runtime | ✓ | 9359 bytes on disk; antipattern_bullets=8 (≥6) |
| B4.2 | antipattern cross-check trace recorded against PRD design direction | runtime | ✓ | First-pass: 6/12 findings touch UI_GUIDE (1 CRITICAL — keyboard-first vs hover-only delete is the antipattern audit core), 3/3 distributed across PRD↔UI_GUIDE + ARCH↔UI_GUIDE + ADR↔UI_GUIDE pairs. Iteration 1: 2/2 NEW findings touch UI_GUIDE pairs |
| B4.3 | UI_GUIDE body contains zero antipattern instances | runtime | ✓ | grep on `{{UI_BODY}}` portion (after `## Visual identity`) returned no matches across all 12 baseline keywords |
| B4.4 | `server/run_dir.py`, `server/harness.py`, `server/__init__.py` unchanged | static | ✓ | empty diff against master |
| B4.5 | Zero TBD/TODO/미정 in UI body | runtime | ✓ | grep on `{{UI_BODY}}` portion returned no matches |
| B3.5 | ≥1 cross-doc finding distributed across pairs (carry-over) | runtime | ✓ | First-pass: 2 PRD↔ARCH + 2 ARCH↔ADR + 2 PRD↔ADR + 3 PRD↔UI_GUIDE + 2 ARCH↔UI_GUIDE + 1 ADR↔UI_GUIDE = **6/6 categories** (exceeds minimum 2/3 carry-over by wide margin). Iteration 1: 1 [PRD↔UI_GUIDE] + 1 [ADR↔UI_GUIDE] NEW = 2/6 categories. |

## Trace excerpts

### Step 13 single dispatch — harness preamble verified

The dispatched UI_GUIDE prompt began with the literal `[HARNESS RULES — 무시 금지]` block from `server/harness.wrap_with_preamble` style (constructed via in-Bash Python helper writing to /tmp/dogfood-b4-prd-body.txt for first-pass; iteration 1 dispatches inlined the preamble in the Agent prompt). Step 13 turn contained exactly **one** Agent call (single-dispatch verification location *c*).

### Plan-agent fix (B-3 Finding #3) verified end-to-end

All 6 plan-implementation dispatches across this run used preferred=`general-purpose`, fallback=`Plan`:

| Step | Dispatch | Drift observed |
|---|---|---|
| 2 | PRD body (first-pass) | none — clean 6 sections, no `### Critical Files` |
| 3 | AC bash (first-pass) | none — raw one-liner returned, no fences |
| 8 | ARCH (first-pass) | none — clean 6 sections, no `### Critical Files` |
| 11 | ADR (first-pass) | none — 3 decisions × 5 sub-headings, gate B3.2 stricter form ✓ |
| 13 | UI_GUIDE (first-pass) | none — 5 sections, antipattern keywords absent, gate B4.3 ✓ |
| 2,3,8,11,13 (×5) | iter1 re-drafts | none across all 5 |

Total: **0 drift observations across 11 plan-implementation dispatches under `general-purpose`-preferred**. This is the first 4-doc trace under the Plan-agent fix and provides the iteration-1 baseline the SKILL.md NOTE block referenced.

### Step 9 first-pass review — distribution evidence

```
- [PRD↔ARCH]      IMPORTANT × 2 (persistence guarantee gap, localStorage capacity unaddressed)
- [ARCH↔ADR]      IMPORTANT × 1 (mutator setItem vs ADR2 store monopoly contradiction) + NIT × 1 (DOM helper ownership undocumented)
- [PRD↔ADR]       IMPORTANT × 1 (keyboard-first vs re-render focus gap) + NIT × 1 (motivation trace implied)
- [PRD↔UI_GUIDE]  CRITICAL × 1 (keyboard-first vs hover-only delete) + IMPORTANT × 1 (monochrome vs accent untraced) + NIT × 1 (Empty state hidden-tab exception)
- [ARCH↔UI_GUIDE] IMPORTANT × 2 (clear-completed action path missing, submitting state without async flow)
- [ADR↔UI_GUIDE]  IMPORTANT × 1 (focused states + re-render preservation unspecified)
```

### Step 9 iteration 1 — RESOLVED rate + new findings

```
RESOLVED:    12 / 12 prior findings (100%) — exceeds B-3's 90% rate
UNRESOLVED:  0
NEW:         2 — both iteration-introduced
  - IMPORTANT [PRD↔UI_GUIDE] UI_GUIDE Screen C "Editing a row" composes inline edit, but PRD `## Core features` only lists add/toggle/delete (no edit). UI_GUIDE iter1 added the edit screen referencing ARCH iter1's `actions.edit` — a feature ARCH grew during iteration that PRD doesn't sanction.
  - NIT [ADR↔UI_GUIDE] ADR Future ADRs blockquote defers "dark-mode token strategy", but UI_GUIDE Color tokens table iter1 already defines light+dark pairs (`#0E0E0E` bg, `#5B8DEF` accent dark variants, etc.) — UI_GUIDE pre-emptively decided what ADR explicitly deferred.
```

This reproduces **B-2 Finding #4** and **B-3 Finding #5** for the third consecutive phase: iteration resolves prior findings (and even improves the resolution rate vs B-3) but introduces new ones that exit unresolved at the 1-iteration cap. Three corroborating data points now exist for re-prioritizing the multi-iteration post-tuning track. See Findings #2 below.

### Iteration diffs (summary)

- **PRD.md** — Core features bullets gained explicit keyboard-first phrasing for toggle/delete/filter ("마우스 hover 의존 금지", "전환 시 입력 focus 유지", "입력 검증도 동기 처리, async 플로우 없음"). Design direction added "상태 변화 후에도 입력 포커스가 보존되어야 한다". Risks added "localStorage.* 값을 직접 inspect하는 방식의 직접 검증이 필요하다".
- **ARCHITECTURE.md** — Stack now lists Vitest + jsdom (unit) + Playwright (e2e — keyboard/focus 검증). Directory tree adds `src/dom.ts` (querySelector wrapper + focus helpers) and `src/types.ts` (type-only). Patterns gained "Store monopoly on persistence" (ADR-0002 ref), "Pub-Sub", "Pure view", "Event delegation" labels. Data flow step 3 rewritten — `store.commit()` is now the single persistence path, no more `mutator.localStorage.setItem`. Step 4 mentions view-side focus snapshot/restore. Module boundaries: store gains commit() contract w/ quota+JSON parse handling; actions gains `clearCompleted`; view gets explicit focus preservation responsibility (ADR Decision 3 ref); dom.ts adds `saveFocus`/`restoreFocus`.
- **ADR.md** — Decision 1 Tradeoffs reference src/dom.ts as explicit module. Decision 2 Reasoning notes ARCH iter1 contradiction resolved. Decision 3 Tradeoffs heavily expanded — explicit "save-before-rerender / restore-after-rerender pattern" with `selectionStart`/`selectionEnd` snapshot, dom.ts ownership, Playwright e2e coverage requirement. Trailing `> **Future ADRs**` blockquote added with 4 deferred decisions (quota/clearCompleted/dark-mode/scroll-position).
- **UI_GUIDE.md** — Visual identity opens with single-accent rule traced to PRD design direction. Color tokens table expanded to 7 tokens with light+dark pairs (introduces dark-mode support — note this is the source of new finding #2 since ADR defers dark-mode strategy). Component patterns: input field `submitting` state dropped (synchronous flow only). Checkbox row delete is keyboard-first primary (Backspace/Delete on focused row), mouse fallback secondary; focus rule documents post-delete focus migration. Filter tab uses `role="tablist"` + arrow keys + `aria-selected`. Component patterns explicitly state focus preservation via `data-focus-id` attributes (ADR Decision 3 ref). Priority screens: A=Empty, B=Main (clear-completed maps to actions.clearCompleted), C=Editing (NEW — iteration-introduced, source of new finding #1).

## Findings — wording/spec issues exposed by dogfood

These are issues the dogfood discovered that static tests would not have caught. Tracked here as Phase B-5+ candidates, **not blockers for B-4**.

### #1 — Steps 2+3 (and iter1 4-way) sequentially dispatched instead of single-message parallel

**Symptom.** SKILL.md Step 2/3 contract says "fire both in a single message with two Agent calls (true parallel dispatch — Phase B-1 verification location *a*)". The iteration write order step 4 says Step 13 "can be parallel with Steps 2+3 + 8 + 11" demonstrating the 4-way surface. In this dogfood:
- First-pass: Steps 2 and 3 dispatched sequentially (Step 2 returned, then Step 3 fired in next message).
- Iteration: PRD body, AC bash, ARCH, ADR, UI_GUIDE all dispatched sequentially (5 separate messages with 1 Agent call each).

**Cause.** Orchestrator (main Claude) chose sequential out of single-message Agent-call budget caution. The B-3 dogfood Finding #4 explicitly permitted sequential as a fallback for iteration; B-4 inherits that permission but fails to demonstrate the 4-way surface even opportunistically.

**Verdict.** Acceptable per the SKILL.md "sequential dispatch remains acceptable" caveat in Step 6 step 4. Gate B1.3 (single-message ≥2 Agent-calls trace) is a Phase B-1 first-introduction gate and not actively gated on B-4 dogfood — so B-4 still passes.

**Fix candidate (Phase B-5).** B-5 will explicitly exercise true 4-way parallel as its core spike. The orchestrator's "Agent-call budget caution" should be either (a) verified via a controlled experiment (does Claude Code actually have a hard limit on parallel Agent calls in a single response?) or (b) removed from the caveat block if no real limit exists.

### #2 — Iteration introduced 2 NEW findings (third corroboration of multi-iteration justification)

**Symptom.** Iteration 1 resolved 12/12 prior findings (100% — exceeds B-3's 90%) but introduced 2 NEW findings:
- IMPORTANT [PRD↔UI_GUIDE]: UI_GUIDE iter1 added Screen C "Editing a row" inline edit, ARCH iter1 added `actions.edit` to the actions module — but PRD `## Core features` was not amended to include editing. The iteration grew the implementation surface without growing the PRD.
- NIT [ADR↔UI_GUIDE]: ADR Future ADRs deferred "dark-mode token strategy", but UI_GUIDE Color tokens table iter1 added light+dark pairs anyway. The two docs decided opposite things in the same iteration.

Both NEW findings exit unresolved at the Phase B-4 1-iteration cap.

**Cause.** Same as B-2 Finding #4 / B-3 Finding #5: iterative refinement over a 4-doc surface naturally surfaces new contradictions because each doc evolves independently and the cross-doc consistency is only re-checked at Step 9 (after all 4 are written). One iteration is sufficient to resolve prior findings but creates room for new ones; the cap forces these to ship unresolved.

**Recurrence pattern.**

| Phase | Iteration resolves | Iteration introduces | Cap behavior |
|---|---|---|---|
| B-2 | 4 prior CRITICALs | 1 new CRITICAL | Exit unresolved |
| B-3 | 9/10 prior findings (90%) | 1 new IMPORTANT | Exit unresolved |
| B-4 | 12/12 prior findings (100%) | 2 new findings (1 IMPORTANT + 1 NIT) | Exit unresolved |

**Fix candidate (Phase B post-tuning).** Three consecutive phases now justify multi-iteration with stop conditions. Proposed stop condition: keep iterating until `RESOLVED ≥ 80% AND NEW ≤ 0` for two consecutive iterations, capped at 7 iterations. The 1-iteration cap is no longer defensible by absence of evidence; B-2/B-3/B-4 form a pattern.

### #3 — Gate B4.5 grep is robust against the antipattern table (no false positive observed)

**Symptom (positive).** The `{{UI_BODY}}` slice (extracted via `awk '/^## Visual identity/{flag=1} flag'`) correctly excludes the `## Antipatterns to avoid` section that contains the literal `TODO` keyword as part of antipattern bullets. Gate B4.5 returned ✓ with zero hits in both first-pass and iter1.

**Verdict.** Plan Task 5 Step 3's awk-based slice design (anchoring on the first body section heading instead of the literal `{{UI_BODY}}` placeholder, which doesn't survive substitution) was correct. **No fix needed**; this Finding is recorded as positive validation of the slice anchoring strategy.

### #4 — UI_GUIDE iter1 introduced dark-mode token pairs that the PRD never asked for

**Symptom.** First-pass UI_GUIDE Color tokens listed only light values + a brief note "다크 모드는 v1 범위 외이며, 도입 시 ... 쌍으로 매핑한다". Iter1 expanded into a full 7-token light/dark table inline. PRD never lists dark-mode as a core feature or excluded item. ADR iter1 explicitly defers dark-mode to a future ADR.

**Cause.** UI_GUIDE iter1 sub-agent prompt asked it to expand the table; the agent took the latitude to fully populate dark variants. The first-pass had hedged with "v1 범위 외" — iter1 dropped that hedge.

**Fix candidate (Phase B-5 or post-tuning).** Either (a) Step 13 prompt should explicitly forbid expanding scope ("do not introduce features not in PRD"); or (b) gate B4.2 audit should specifically check UI_GUIDE for unscoped feature additions (ADR-deferred items reappearing in UI_GUIDE). (b) is cleaner since (a) requires per-iteration prompt discipline.

### #5 — `## Core features` ↔ ARCH `actions` module drift on `edit`

**Symptom.** PRD Core features (both first-pass and iter1) list "task 추가 / 완료 토글 / 삭제" — no edit. ARCH first-pass actions module had only `add/toggle/delete/setFilter`. ARCH iter1 expanded to include `add/toggle/remove/edit/clearCompleted/toggleAll/setFilter` — adding `edit` and `toggleAll` without explicit interview signal.

**Cause.** ARCH iter1 sub-agent inferred edit/toggleAll as "natural extensions" because the actions module shape called for it (4 → 6 modules implies more granular operations). UI_GUIDE iter1 then composed Screen C around `edit` (since ARCH advertised it). The drift propagated: ARCH adds → UI_GUIDE consumes → PRD ignores.

**Fix candidate (Phase B-5 or post-tuning).** Same as Finding #4 — Step 8/13 prompts should constrain to PRD-derived features. Cross-doc audit should explicitly check that any module/function/screen introduced in iteration ARCH/ADR/UI_GUIDE traces back to a PRD `## Core features` entry. This is a **scope-creep guard** that complements the existing antipattern audit.

## Status

Phase B-4 dogfood **passes** end-to-end — all 5 phase-specific gates (B4.1–B4.5) green, all 5 common gates (C1–C5) green, gate B3.5 carry-over (≥1 finding distributed across ≥2 of 6 pairs) wildly exceeded (6/6 first-pass, 2/6 iter1). Workflow completed Steps 0–13 + iteration 1 with real artifacts on disk in run `20260429-103152-e35b`. 5 wording/spec findings captured (none blocking; Finding #2 escalates the multi-iteration post-tuning track to high priority based on B-2/B-3/B-4 corroboration).

Branch `v4-phase-b-4` is **ready for Task 6 (review-before-merge gate)**: 5 implementation commits (Tasks 1–4 + 1 NIT fix-up `ebfc610`) + this dogfood report = 6 total expected, full regression at 147 passes, gate B4.4 (server/* unchanged) holds.

## Pre-merge review (Task 6 Step 3 gate)

Reviewer: `superpowers:code-reviewer` subagent against `git diff master..HEAD`.
Verdict: **Not READY initially → READY after IMPORTANT + 2 NIT fix-up commit**.

### Acceptance criteria results

| AC | Status | Note |
|---|---|---|
| 1 | PASS | Step 13 row `plan-implementation` / `general-purpose` / `Plan` matches Steps 2/3/8/11 |
| 2 | PASS | Forward-step pointer chain `0→1→2+3→4→5→7→8→10→11→12→13→9→6` consistent (Step 11 → Step 12 fixed in `ebfc610`) |
| 3 | PASS | UI_GUIDE template uses `{{TASK}}` + `{{DESIGN_DIRECTION}}` + `{{UI_BODY}}`; Step 13 substitutes all three with PRD-on-disk design direction extraction |
| 4 | PASS | Antipattern table 8 bullets ≥6, all canonical keywords present |
| 5 | PASS | File sizes match disk; 147 tests pass; gate B4.4 server diff empty |
| 6 | PASS | No PRD-only / PRD+ARCH / PRD+ARCH+ADR sub-mode exists in plan-pack to break |
| 7 | PASS | Diff scope = `bundled/plan-pack/SKILL.md`, `bundled/plan-pack/templates/UI_GUIDE.md.template`, `docs/dogfood/phase-b-4.md`, `tests/e2e/test_plan_pack_inventory.py`, `tests/unit/test_plan_pack_skill.py` only |

### IMPORTANT findings (addressed in fix-up commit on this branch)

1. **SKILL.md:194 — stale execution-order banner.** Step 7 blockquote read `Steps 7–8–10–11–9` (B-3 era); should enumerate Steps 12 and 13 in the new B-4 chain. **Fixed**: now reads `Steps 7–8–10–11–12–13–9 run after Step 5 writes PRD.md`.

### NIT findings (addressed in same fix-up commit)

1. **SKILL.md:14-18 — orchestrator-only preamble stale prose.** Said "results to `<run_dir>/PRD.md` and `<run_dir>/ARCHITECTURE.md`" — never updated through B-3 or B-4. **Fixed**: now reads "PRD, ARCHITECTURE, ADR, or UI_GUIDE content directly … writes the combined results to `<run_dir>/{PRD,ARCHITECTURE,ADR,UI_GUIDE}.md`".
2. **dogfood report progress.json size off by 24 bytes** (477 reported vs 501 actual on disk; runtime touch). Cosmetic; deferred.

### Dogfood findings classified per "Out of scope"

Reviewer confirmed all 5 dogfood findings are correctly classified:
- Findings #1 (sequential dispatch), #4 (UI_GUIDE dark-mode scope creep), #5 (ARCH `edit`/`toggleAll` scope creep) — Phase B-5 / post-tuning track per plan §"Out of scope"
- Finding #2 (multi-iteration justification third corroboration) — meta evidence, not a B-4 blocker
- Finding #3 (gate B4.5 awk slice positive validation) — confirms design

None reveal a contradiction in the merged code itself; none block merge.

### Verdict

**READY for merge** after the 1 IMPORTANT + 2 NIT fixes land on this branch (commit `_to_be_added_below_`).
