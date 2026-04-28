# Changelog

All notable changes to this project will be documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — V4 Phase A + B-1 + B-2

### Added
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

### Fixed
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
