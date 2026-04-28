# Changelog

All notable changes to this project will be documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — V4 Phase A + B-1

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

### Notes
- Phase B (`plan-pack` ★) is intentionally out of scope; the placeholder `hello-bundle` is the only bundled tool until then.
- No agent-name hardcoding, no main-Claude heavy work in bundled SKILLs, no Codex/Gemini harness compatibility (per V4 정체성 보호 — see `project_assemble_v4_spec.md`).
- Phase A's `bundled/hello-bundle/` placeholder has been retired; plan-pack now occupies the bundled `plan` stage slot.
- Phase B-2 (ARCH), B-3 (ADR), B-4 (UI_GUIDE), and B-5 (4-doc integration spike) remain out of scope and will each be planned with a fresh `writing-plans` pass after the previous phase's dogfood passes.
- Cross-cutting B (system-wide AC-bash execution by `verifier`) and C (auto trace + learning replay) remain out of scope for Phase B.
- **Dogfood report (`docs/dogfood/phase-b-1.md`) is pending — it lands in a follow-up commit after the user runs the smoke.**

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
