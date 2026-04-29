# Changelog

All notable changes to this project will be documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — V4 Phase A + B-1 + B-2 + B-3 + B-4 + B-5 + Quality Pass (C+D) + Hygiene Pass (E+F)

### Added (Hygiene Pass — Items E + F)
- `docs/contributing/dogfood-gate-patterns.md` — codifies the line-anchored placeholder-token regex pattern (`^TBD$|^TODO$|^미정$`) as the canonical form for future dogfood gates, replacing the word-boundary form (`\bTBD\b|\bTODO\b|미정`) that produced B-3 Finding #1's false positive on narrative prose. Past phase-*.md files left as historical records (Item F).

### Changed (Hygiene Pass — Items E + F)
- `bundled/plan-pack/SKILL.md` ambiguity audit (Item E). Four HIGH ambiguities surfaced by `superpowers:code-reviewer` and resolved:
  - Workflow §"Execution sequence" callout added at top — explicit `0 → 1 → (2 + 3) → 4 → 5 → 7 → 8 → 10 → 11 → 12 → 13 → 9 → 6` sequence with a one-line "step numbers reflect historical addition order, not execution order" note. Closes the HIGH-4 ambiguity (orchestrator could read step numbers and run 6→7→8 in numeric order).
  - Step 9 cross-doc append snippet: branched the heading on `iteration_count` (bare for first-pass, suffixed for iterations); added a precondition assert that the heading isn't already present in `current` (catches HIGH-2 — Step 11 overwrite failure that would silently produce duplicate same-named sections). Note expanded to cover B-5 multi-iteration cap=7 instead of B-4 cap=1.
  - Step 6 iteration write order step 7: "discard the old `## Cross-doc review` section" replaced with explicit "overwrite from scratch — re-run template fill, do NOT read existing file first" wording. Closes HIGH-1 (B-4 Task 6 incident class — "replace" misread as "add alongside").
  - Step 6 iteration scope discipline enforcement: replaced the prose paragraph with a 6-step concrete enforcement procedure (scan → check PRD anchor → strip section → record stripped_items → conditionally append audit-header line). Closes HIGH-3 ("strip it" was ambiguous about what artifact, where to record).

### Notes (Hygiene Pass)
- Phase B-5 closed Items A + B (multi-iteration + parallel/byte-identity); Quality Pass closed Items C + D (test pattern + spec/test drift CI); this Hygiene Pass closes Items E + F. The full distribution-prep checklist from `project_assemble_v4_phase_b_posttuning.md` is now drained.
- Test count: 163 passed (Quality Pass baseline). No new tests; this pass is documentation/clarity changes.
- Diff scope: bundled/plan-pack/SKILL.md + docs/contributing/dogfood-gate-patterns.md + CHANGELOG.md. Server infrastructure (gate B5.4) unchanged.

### Added (Quality Pass — Items C + D)
- `tests/contracts/contracts.json` — verbatim contract registry. Initial entries cover the 5 B-5 contracts (stop condition, iteration state, scope discipline preserved, platform-limit citation, preamble byte-identity). Contributors register new contracts here as new verbatim spec blocks ship (Item D).
- `tests/unit/test_contracts_meta.py` — parametrized meta-test that reads the registry and asserts each phrase appears as a literal substring within its declared section of its declared spec file. CI-grade defense against silent test ↔ spec wording drift (Item D).
- `docs/contributing/test-anchoring.md` — canonical contributor reference for the test-anchoring pattern. Codifies the `body[:N]` window-slice prohibition, the `_section()` helper contract, and the heading-depth semantics. Future contributors hit one doc instead of rediscovering the pattern from B-4 retro (Item C).

### Changed (Quality Pass — Items C + D)
- `tests/unit/test_plan_pack_skill.py` refactored: all `step_X[:N]` window slices replaced with `_section(body, "### Step N")` heading-anchored slices (28 step assignments + 54 window-slice usages cleaned up). Step variable assignments normalized from `body[body.index("Step N..."):]` to `_section(body, "### Step N")`. The wholesale refactor that B-4 retro #1 documented and B-5 plan §"Out of scope" deferred (Item C).

### Notes (Quality Pass)
- Phase B-5 closed Items A + B (multi-iteration + parallel/byte-identity); this Quality Pass closes Items C + D (test pattern + spec/test drift CI). Items E + F remain queued for a Hygiene Pass per ledger `project_assemble_v4_phase_b_posttuning.md` Tier 3.
- Test count delta: +8 contracts meta tests (parametrized over 5-entry registry plus 3 sanity-check tests). Total: 163 passed.
- Diff scope: tests/unit/test_plan_pack_skill.py + 3 new files. server/run_dir.py, server/harness.py, server/__init__.py unchanged (gate B5.4 intact).

### Added (Phase B-5)
- `server/inventory.py` honors `ASSEMBLE_BUNDLED_ONLY=1`: when the env flag is set, `scan()` filters enumeration results down to entries under the assemble bundled root and returns the in-memory rebuild without persisting to cache. Lets blank-Mac dogfood gates simulate a fresh user with no installed skills without nuking `~/.claude/skills/` (Phase B-5 distribution prep).
- plan-pack Step 6 multi-iteration loop with stop conditions: replaces the B-4 1-iteration cap with `RESOLVED ≥ 80% AND NEW ≤ 0` × 2 consecutive iterations (cap=7). Per-run state persists at `runs/<rid>/iteration_state.json` with three termination paths (`stop-condition-met`, `cap-reached`, `user-requested-stop`). Iteration scope discipline block (`33b3056`) preserved verbatim and now applies to every iteration in the loop, not only the first (Phase B-5 Item A).
- `docs/research/2026-04-29-platform-limit.md` — empirical platform-limit experiment. T2/T3/T4/T5 trials (single-message dispatch of 2/3/4/5 `general-purpose` Agent calls) all returned without reject / rate-limit / silent-degrade. Documents the 5-way dispatch headroom and the decision branches it forced in B-5 (Phase B-5 Item B prep).
- plan-pack Steps 2/3 + Step 6 step 4 caveat tightening: cite the platform-limit research; restrict sequential fallback to documented input dependency or retry-after only. The orchestrator's "Agent-call budget caution" no longer counts as sufficient grounds (Phase B-5 Item B-1).
- plan-pack Steps 2/3 preamble byte-identity contract: orchestrator may call `wrap_with_preamble` OR inline the literal preamble; the contract is byte-identity (sha256 match against `bundled/_shared/harness-preamble.md`). Decouples function-call discipline (B-2 dogfood evidence: /tmp roundtrip awkwardness drove orchestrator to bypass) from byte-identity guarantee. Verified at dogfood time via gate B5.7 (Phase B-5 Item B-2).
- `docs/plans/2026-04-30-v4-phase-b-5.md` — Phase B-5 implementation plan (5 tasks; Task 5 = review-before-merge gate, standard pattern).
- `docs/dogfood/phase-b-5.md` — Phase B-5 dogfood result + gate B5.1–B5.7 evidence + pre-merge code-reviewer findings (run `20260429-135600-3b6d`).

### Notes (Phase B-5)
- B-5 dogfood verified 4-way parallel dispatch is platform-supported (5-way headroom from research doc) and exercised the multi-iteration loop's user-override termination path. B-3/B-4 sequential-fallback was orchestrator caution, not platform constraint.
- Recurrence pattern: B-2 (4 prior CRITICALs / 1 NEW), B-3 (9/10 / 1 NEW), B-4 (12/12 / 2 NEW), B-5 (5/5 / 3 NEW). The 1-iteration cap-1 forcing function that B-2/B-3/B-4 had no defense against is gone. iter1 in B-5 could have continued; user chose to stop.
- 4 dogfood findings captured (#1 iter1 ADR sub-agent reworded Decisions 1-3 despite verbatim instruction → iteration prompts need structural verbatim contract; #2 token rename drift; #3 Screen C Processing missing timeout/fallback semantics; #4 ARCH-PRD unit drift). All Phase B-5+ post-tuning candidates.
- Pre-merge review (`superpowers:code-reviewer`) verdict: READY. AC1-AC10 all PASS. 2 IMPORTANT findings (preamble byte count typo, B5.7 evidence quality) addressed in fix-up commit before merge.
- Phase B closure: B-5 closes the 4-doc plan-pack distribution prep checklist for Items A + B (multi-iteration + parallel/byte-identity). Items C/D/E/F remain queued for post-B-5 quality + hygiene passes per ledger `project_assemble_v4_phase_b_posttuning.md`.

### Added
- `bundled/plan-pack/templates/UI_GUIDE.md.template` — UI guide shape with `{{TASK}}` + `{{DESIGN_DIRECTION}}` + `{{UI_BODY}}` placeholders; design direction carried in from PRD §6 to anchor the cross-doc antipattern audit; ships an `## Antipatterns to avoid` section with 8 canonical AI-slop bullets (gradient-text, glass morphism, backdrop-blur, all-purple palettes, emoji-as-decoration, Lorem ipsum / placeholder, TODO / FIXME, ad-copy clichés like "innovative" / "next-generation") (Phase B-4).
- plan-pack Step 12: UI_GUIDE interview (6 questions, 2 `AskUserQuestion` calls of 3) after `ADR.md` is written — visual identity, priority flows, component patterns, color tokens, typography, project-specific antipattern emphasis (Phase B-4).
- plan-pack Step 13: UI_GUIDE single dispatch via `plan-implementation` role (preferred `general-purpose`, fallback `Plan` — inherits the post-B-3 swap from `v4-plan-pack-content-role-fix`), harness-preamble-prepended, writes `runs/<rid>/UI_GUIDE.md` atomically; sub-agent contract requires five sections (Visual identity, Color tokens, Typography, Component patterns, Priority screens) with synthesis from PRD `## Design direction` + `## Core features` (Phase B-4).
- plan-pack Step 9 extended: cross-doc second-opinion is now 4-way (PRD ↔ ARCH ↔ ADR ↔ UI_GUIDE) with three new pair categories — design-direction audit (PRD ↔ UI_GUIDE, antipattern violations are CRITICAL), component coverage (ARCH ↔ UI_GUIDE), UX decision integrity (ADR ↔ UI_GUIDE). Verified bullets continue to land on `ADR.md` (Phase B-4).
- plan-pack Step 6 extended: iteration now re-runs PRD (Steps 2+3) + ARCH (Step 8) + ADR (Step 11) + UI_GUIDE (Step 13) as a consistent quadruple; explicit "Iteration write order" subsection enumerates the 10-step overwrite order; iteration prompt label updated to "yes — refine all four" (Phase B-4).
- `docs/plans/2026-04-29-v4-phase-b-4.md` — Phase B-4 implementation plan (6 tasks; Task 6 = review-before-merge gate, now the standard).
- `docs/dogfood/phase-b-4.md` — Phase B-4 dogfood result + gate evidence + pre-merge code-reviewer findings (run `20260429-103152-e35b`).

### Notes (Phase B-4)
- Phase B-4 closes the four-doc plan-pack surface (PRD + ARCH + ADR + UI_GUIDE). Phase B-5 promotes all docs to true 4-way parallel dispatch and runs the blank-Mac simulation under `ASSEMBLE_BUNDLED_ONLY=1`.
- Plan-agent fix (B-3 Finding #3) was already merged on master before B-4 started (commit `85366f1` on `v4-plan-pack-content-role-fix`); the new Step 13 row inherits the swap (`plan-implementation` preferred `general-purpose`, fallback `Plan`). B-4 dogfood produced the first 4-doc trace (11 plan-implementation dispatches, 0 drift observations) under `general-purpose`-as-preferred — baseline for future drift comparisons.
- B-3 Finding #1 (gate B3.3 mechanical grep false positive on narrative prose) recurrence check: **not observed** in B-4 dogfood. Plan Task 5 Step 3's awk-based slice (anchoring on `## Visual identity` instead of literal `{{UI_BODY}}` placeholder) correctly excluded the antipattern table from B4.5 grep — captured as positive design validation in dogfood Finding #3.
- B-3 Finding #5 (a fresh CRITICAL surfacing only on iteration 1, exiting unresolved at the cap) recurrence check: **observed** in B-4 dogfood. Iteration 1 resolved 12/12 prior findings (100% — vs B-3's 90%) but introduced 2 NEW findings (1 IMPORTANT [PRD↔UI_GUIDE] inline editing screen vs PRD core features + 1 NIT [ADR↔UI_GUIDE] dark-mode tokens forward-shadow). Both exit unresolved at the 1-iteration cap. Three consecutive phases (B-2 / B-3 / B-4) now corroborate the multi-iteration post-tuning track justification.

### Added (Phase B-3, carried into Unreleased)
- `bundled/plan-pack/templates/ADR.md.template` — minimal ADR shape with `{{TASK}}` + `{{DECISIONS_BLOCK}}` placeholders; sub-agent emits the entire `## Decision N: <title>` tree directly (Phase B-3, avoids B-2 Finding #1 heading-collision pattern).
- plan-pack Step 10: ADR interview (6 questions, 2 `AskUserQuestion` calls of 3) after `ARCHITECTURE.md` is written (Phase B-3).
- plan-pack Step 11: ADR single dispatch via `plan-implementation` role, harness-preamble-prepended, writes `runs/<rid>/ADR.md` atomically; sub-agent contract requires ≥3 decisions each with `### Rejected alternatives` and `### Tradeoffs` sub-headings, with `### Context` and `### Reasoning` synthesized from PRD + ARCH (review I1 fix-up — never user-collected stubs) (Phase B-3).
- plan-pack Step 9 extended: cross-doc second-opinion is now 3-way (PRD ↔ ARCH ↔ ADR) — gap detection, decision integrity (ARCH ↔ ADR), motivation traceability (PRD ↔ ADR); verified bullets appended as `## Cross-doc review` to `ADR.md`. Iteration uses `## Cross-doc review (iteration N)` suffix (Phase B-3).
- plan-pack Step 6 extended: iteration now re-runs PRD (Steps 2+3) + ARCH (Step 8) + ADR (Step 11) as a consistent triple; explicit "Iteration write order" subsection enumerates the 8-step overwrite order (Phase B-3, addresses B-2 Finding #3).
- `docs/plans/2026-04-28-v4-phase-b-3.md` — Phase B-3 implementation plan (6 tasks; Task 6 = explicit review-before-merge gate).
- `docs/dogfood/phase-b-3.md` — Phase B-3 dogfood result + gate evidence + pre-merge code-reviewer findings (run `20260428-214502-6b79`).

### Notes
- Phase B-3 closed B-2's after-merge process violation by introducing **review-before-merge** as a dedicated Task 6 gate. `superpowers:code-reviewer` ran against the branch diff before any merge; READY verdict required all 6 acceptance criteria to PASS, and IMPORTANT findings were addressed on the same branch.
- Phase B-4 (UI_GUIDE) follows the same 5-task shape with the AI-slop antipattern table; review-before-merge gate from Phase B-3 (Task 6) is now the standard for the rest of Phase B.
- Cross-cutting B (verifier executes AC bash) and C (auto trace + learning replay) remain out of scope for Phase B.
- Phase B-3 dogfood reproduced B-2 Finding #4: iteration resolves CRITICALs but introduces 1 new finding (`--max-concurrency` knob naming inconsistency) that exits unresolved at the 1-iteration cap. Multi-iteration with stop conditions is increasingly justified for the post-tuning track.


- `bundled/` skill root for self-sufficient bundled library (V4 decisions #1–#5).
- `_shared/harness-preamble.md` — harness 4-rule preamble that bundled SKILLs prepend to subagent prompts.
- `hello-bundle/` placeholder so bundled-path discovery has a real file in Phase A; replaced when Phase B lands real bundles.
- `bundled` boolean on every inventory entry (`scan()` flags entries under `~/.claude/skills/assemble/bundled/`).
- `★ ` label prefix and fallback hint when a bundled tool is the only match for a stage.
- i18n keys: `menu.bundled_prefix`, `notices.bundled_only_hint` (en + ko).
- `server/run_dir.py` with atomic `write_run_artifact` / `read_run_artifact` / `run_artifact_path` helpers (Phase B-1).
- `server/harness.py` exposing `wrap_with_preamble(prompt)` so bundled SKILLs can prepend the 4-rule preamble to every dispatched sub-agent prompt (Phase B-1).
- `bundled/plan-pack/` — first ★ bundle. Phase B-1 ships PRD-only generation: 8-question interview → parallel dispatch (PRD body + AC bash) → second-opinion review → opt-in one-iteration round-trip → atomic write to `runs/<rid>/PRD.md`.
- `bundled/plan-pack/templates/PRD.md.template` — fillable PRD shape with 7 sections (Goal, Users, Core features, Excluded from MVP, Acceptance Criteria bash, Design direction, Risks).
- `docs/plans/2026-04-28-v4-phase-b.md` — Phase B design spec (B-1 to B-5 roadmap).
- `docs/plans/2026-04-28-v4-phase-b-1.md` — Phase B-1 implementation plan (9 tasks).
- `docs/dogfood/phase-b-1.md` — Phase B-1 dogfood report (run `20260428-160618-654d`).
- `bundled/plan-pack/templates/ARCHITECTURE.md.template` — 6-section architecture artifact (Stack, Directory tree, Architectural patterns, Data flow, External dependencies, Module boundaries) (Phase B-2).
- plan-pack Step 7: ARCH interview (6 questions, 2 `AskUserQuestion` calls of 3) after PRD.md is written (Phase B-2).
- plan-pack Step 8: ARCH single dispatch via `plan-implementation` role, harness-preamble-prepended, writes `runs/<rid>/ARCHITECTURE.md` atomically (Phase B-2).
- plan-pack Step 9: cross-doc second-opinion spanning PRD + ARCH — gap detection and scope-creep check, verified bullets appended as `## Cross-doc review` to ARCHITECTURE.md (Phase B-2).
- plan-pack Step 6 extended: iteration now re-runs both PRD (Steps 2+3) and ARCH (Step 8) as a consistent pair; one-iteration cap updated to Phase B-2 (Phase B-2).
- `docs/plans/2026-04-28-v4-phase-b-2.md` — Phase B-2 implementation plan (5 tasks).
- `docs/dogfood/phase-b-2.md` — Phase B-2 dogfood result + gate evidence.

### Changed
- `bundled/plan-pack/SKILL.md` Step 1: 8-question interview now spans two
  `AskUserQuestion` calls of 4 each (platform `maxItems=4`); the prior
  "single batched" wording was unimplementable.
- `bundled/plan-pack/SKILL.md` Step 2/3: ships the canonical
  `wrap_with_preamble` call snippet; explicit "do not hand-write the
  preamble inline" guidance to keep harness wording from drifting
  across runs.
- `bundled/plan-pack/SKILL.md` Step 4: new Step 4b "verify before
  appending" — second-opinion runtime claims require a 1-shot Bash
  test, internal-contradiction claims require re-reading the cited
  sentences, unverifiable speculation is dropped. Audit header
  (`> verified by main Claude on <date> — <n> kept / <m> dropped`)
  prepended to Review notes.

### Changed
- **Phase B-1+B-2 dogfood reports unified**: both `docs/dogfood/phase-b-1.md`
  and `docs/dogfood/phase-b-2.md` now use the same Gate results table shape
  with explicit `Kind` column (`static` / `runtime` / `mixed`) per row.
  Each row also carries an `Evidence` cell that cites the specific test,
  trace path, or `git diff` command that backs the status. Addresses the
  retroactive-review concern that "passes" was claimed without distinguishing
  between code-path verifiable contracts and behaviors that only a real run
  can observe. The same shape is the template for Phase B-3+ dogfood.

### Fixed
- **Phase B-1 retroactive review C1 (security)**: `server/run_dir.py` now
  validates `run_id` and `filename` as plain basenames before writing —
  rejects `/`, `\`, `..`, leading `.`, and empty values. Prevents path-
  traversal / absolute-path injection out of the runs directory. Adds a
  defense-in-depth `resolve()` check that the final target sits under
  the runs root, catching symlink swaps that basename validation alone
  would miss. Reproduced live before fix: `write_run_artifact("rid",
  "/tmp/evil", ...)` wrote outside the runs root.
- **Phase B-1 retroactive review C2**: Plan-doc role-mapping tables
  (`docs/plans/2026-04-28-v4-phase-b-1.md`, `docs/plans/2026-04-28-v4-phase-b.md`)
  Step 5 row claimed `text-summarize`/`gemma-worker` dispatch, contradicting
  the prose (main Claude calls `write_run_artifact` directly) and violating
  V4 identity rule "no Codex/Gemini harness compatibility in bundled SKILLs".
  SKILL.md was silently corrected in B-2 — plan docs now match.
- **Phase B-1 retroactive review C3**: Phase B-1 dogfood report status
  clarified — passes only for the SKILL.md-fixes track. The PRD artifact
  produced during the dogfood iteration 2 still carries the false-alarm
  bullet that motivated Step 4b; report now explicitly preserves it as
  historical evidence rather than an authoritative PRD.
- **Phase B-1 retroactive review C4**: `bundled/plan-pack/SKILL.md` Steps
  2/3 prose now says "proceeds to Step 4 (consistency review), not Step 5"
  — was previously "proceeds to Step 5", which silently skipped the
  second-opinion review that exists immediately after.
- **Phase B-1 retroactive review C5**: `_load_preamble` no longer caches
  the missing-file (`None`) result. The previous `lru_cache` cached the
  first call's outcome forever — a preamble created late in process was
  silently never picked up. Replaced with a per-resolved-path dict cache
  that only stores successful loads.
- **Phase B-1 retroactive review I1**: AC bash fence-strip is now an
  exposed `strip_bash_fence` helper in `server/run_dir.py` (also in
  facade) with 5-case unit tests. SKILL.md Step 5 prose previously
  described the algorithm but never implemented or tested it.
- **Phase B-1 retroactive review I2**: 6 plan-pack tests rewritten to
  anchor on the actual workflow section (`### Step N` slice) instead of
  searching the whole file body. Previously these tests passed on
  role-table mentions alone — workflow prose could be deleted entirely
  and tests still passed. Affected: step_3 parallel/explains_role,
  step_4_second_opinion_review, review_uses_role_mapping_fallback,
  step_6_iteration_prompt.
- **Phase B-2 dogfood finding #1**: Step 8 fill pseudocode now uses a
  `split_sections` parser to extract section bodies from sub-agent output
  before substituting into the template. Previous version mapped raw
  interview answers (`a1`–`a6`) to template placeholders, which collided
  with the sub-agent's actual output format (full markdown with `## Stack`,
  `## Directory tree` headings).
- **Phase B-2 dogfood finding #2**: Caveat note added under sub-agent
  role-mapping table — `Plan` agent's stated description is "designing
  implementation plans", which doesn't perfectly match content drafting.
  Empirically works with explicit "no ExitPlanMode" prompts; documented as
  fragile mapping with `general-purpose` fallback guidance.
- **Phase B-2 dogfood finding #3**: Step 6 yes-path now includes an
  explicit "Iteration write order" 6-step list (Steps 2+3 → Step 8 → write
  PRD → write ARCH → Step 9 → append cross-doc review) instead of leaving
  order implicit in narrative prose.
- **Phase B-2 dogfood finding #4**: Multi-iteration justification note added
  citing the actual run that exposed it (`20260428-194703-f5dd` — single
  iteration left 1 new CRITICAL unresolved).
- Tests: 109 → 111 (added `test_workflow_step_8_handles_sub_agent_headings`,
  `test_workflow_iteration_has_explicit_write_order`).
- Replaced fabricated B-2 dogfood report (claimed run id that did not exist
  on disk) with real run trace from `20260428-194703-f5dd`.

### Notes
- Phase B (`plan-pack` ★) is intentionally out of scope; the placeholder `hello-bundle` is the only bundled tool until then.
- No agent-name hardcoding, no main-Claude heavy work in bundled SKILLs, no Codex/Gemini harness compatibility (per V4 정체성 보호 — see `project_assemble_v4_spec.md`).
- Phase A's `bundled/hello-bundle/` placeholder has been retired; plan-pack now occupies the bundled `plan` stage slot.
- Phase B-3 (ADR) and B-4 (UI_GUIDE) follow the same 5-task shape as B-2; each gets its own `writing-plans` pass after the previous phase's dogfood clears. Phase B-5 (4-doc integration spike) remains planned.
- Phase B-2 (ARCH) is now complete and merged.
- Cross-cutting B (system-wide AC-bash execution by `verifier`) and C (auto trace + learning replay) remain out of scope for Phase B.
- Dogfood report delivered in `docs/dogfood/phase-b-1.md` — run `20260428-160618-654d`, plan-pack ★ end-to-end smoke. Status: pass; three SKILL.md fixes shipped from findings (see Changed).

## [3.0.0] — 2026-04-21

First public release. Classification is now installation-aware and the skill
ships with an English baseline + Korean locale overlay.

### Added
- `config/i18n/en.json` + `config/i18n/ko.json` locale files.
- `server/i18n.py` locale loader driven by the `ASSEMBLE_LOCALE` env var, with
  `en` fallback when a key is missing.
- Frontmatter-based heuristic classifier (`_classify_heuristic` in `inventory.py`).
- `unclassified_entries()` returns both skill and agent buckets; `bin/classify-inventory`
  now handles agents as well as skills.
- Corrupt-cache quarantine: a bad `inventory.json` is renamed to
  `inventory.json.bad-<timestamp>` and rebuilt instead of being silently overwritten.
- Illegal transition guard in `mark_stage`: driving `done` back to `in_progress`
  raises `ValueError`.
- Regression test suite for architecture-review findings (`tests/unit/test_codex_findings.py`).
- `LICENSE` (MIT), `README.md`, `VERSION`.

### Changed
- SKILL.md rewritten in English. Korean-language UX is preserved via the
  locale overlay plus Claude's own language adaptation.
- `server/menu.py` now resolves meta-action labels through the locale layer
  instead of hardcoding Korean strings (`물어보기`, `직접`, etc.).
- `config/stages.json` holds stage ids only; display labels and descriptions
  live in the locale files.
- `load_stages()` merges ids with the active locale on every call.
- LLM prompts in `server/classify.py` and `server/sequence.py` translated to
  English (LLMs handle either language; English is more portable).
- User skills now win over plugin skills when names collide — fixed a
  first-wins dedupe bug where plugin paths could beat user paths.
- `scan()` and `apply_classification()` share `update_json_locked`, closing a
  race condition where concurrent writers could lose a classification.
- Menu dedupe: a skill mapped both as a stage tool and as a meta/safety helper
  is surfaced only once under the `tool` kind.
- `back` no longer persists as a stage status; it only rewinds the cursor.
  Earlier builds broke wrap-up counts and `find_resumable` by stamping
  `status='back'` on the record.
- All internal comments and docstrings translated to English.

### Removed
- `config/pre_mapping.json` — the hand-maintained name→stage table. The
  design was fundamentally broken because it pre-mapped tools that might
  not be installed on the user's machine.
- Legacy `pre-mapped` source value from inventory entries. Current sources
  are `heuristic-classified`, `llm-classified`, `unclassified`.

### Fixed
- Personalization leak: removed session-id references and per-user phrasing
  that was baked into the original codebase; honorifics neutralized.
- `.context/` added to `.gitignore` so Codex session artifacts don't ship.
