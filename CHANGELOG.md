# Changelog

All notable changes to this project will be documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — V4 Phase A + B-1 + B-2 + B-3 + B-4 + B-5 + Quality Pass (C+D) + Hygiene Pass (E+F) + B-5 Findings (#1 #2 #4) + B-5 Finding #3 closure (iter2 + iter3 supplemental) + B-5 Item B-7 (dispatches.jsonl) + cap-reached on-disk closure (synthetic) + MED/LOW ambiguity hygiene + Spike I + Spike II + Spike III + Spike IV

### V4 Spike IV (2026-05-01, B-9 dogfood ship — debugger ★ second self-sufficient bundle)

**Adds the second ★ bundle (`bundled/debugger/`) parallel to `plan-pack` ★, and closes the three iter1 audit-trail integrity carryforwards from B-8 dogfood**:

- **Phase A — hook v2** (B-8 carryforward C): `hooks/_guard_bash_matcher.py` delegate; canonical magic marker `ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE` only valid as the first non-empty source line (Python comment) inside a `python3 -c '...'` invocation or `python3 << <DELIM>` heredoc — Bash-comment-prefix bypass closed. Includes regex extension to accept `python3.10`/`python3.11` minor-version forms; `main()` argv parameter dropped (M1+M2 review polish). 8 matcher cases + 1 hook integration case. Commits `020a146` (initial) + `d1e9a1b` (α-tighten: marker as first-line comment only).
- **Phase B — `dispatch_and_record`** (B-8 carryforwards A + B): `server.harness.dispatch_and_record(run_id, *, prompt_file, step, status="dispatched", note=None) -> str` composes `dispatch_prompt` + `record_dispatch` atomically. New `status` (dispatched/skipped/failed) + `note` kwargs on `record_dispatch` schema. `(no change)` iter1 emphasis flips to orchestrator-side skip with `status="skipped"` audit row — sub-agent never dispatched, intent recorded. SKILL.md Step 6 yes-path detail rewritten to use the wrapper exclusively for iter1 4-way path. `iter_emphasis.md` step 1 contract softened (ERROR-back if main misroutes `(no change)`). Commits `152ceac` + `9ad8fd4` + `ca85de4` (Inputs comment fix) + `1cdd4f9` (contracts.json registers 4-row audit invariant).
- **Phase C — `debugger` ★ bundle**: `bundled/debugger/SKILL.md` + 5 sub-agent prompts (`repro_step2`, `hypothesis_step3`, `root_cause_step4`, `fix_step5`, `report_step6`) + 1 orchestrator helper (`iter_revisit`) + 3 templates (`BUG_REPORT.md`, `repro.sh`, `verify.sh` — cross-cutting AC=bash pattern). Linear pipeline + 1 backtrack point: `0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 (loop back to 3 or 4 if iteration chosen)`. Step 1 is main-side `AskUserQuestion` ×2 (symptom + env/last-known-good/tried-fixes). Steps 2-6 dispatch via `dispatch_prompt` + `record_dispatch`. Step 7 uses `dispatch_and_record` for iter1 audit pairing (audit invariant: every iteration produces exactly one row per `step7.iter{N}.<target>`). 7 commits: `90e0e43` (C1) → `6fa1c64` (C2) → `c89a0c4` (C2 polish — `started` field + `pytest.skip` visibility) → `dd32895` (C3) → `e659dcf` (C3 polish — dynamic allowlist size + future-proof test name) → `6f49664` (C4) → `a31d726` (C5) → `ed9a6df` (C6) → `a2564da` (C7) → `58c0800` (C7 polish — explicit 5-section check + iter_revisit prose fix).

**Schema additions**:
- `dispatches.jsonl` rows gain `status` (dispatched/skipped/failed) + `note` fields.
- `ALLOWED_PROMPT_FILES` grows from 8 → 14 (6 debugger entries: `repro_step2.md`, `hypothesis_step3.md`, `root_cause_step4.md`, `fix_step5.md`, `report_step6.md`, `iter_revisit.md`).
- `_resolve_prompt_path` extends bundle order: plan-pack first, debugger second.

**Tests**: 231 → 251 (+20 net). New: 8 hook v2 matcher cases + 1 hook integration + 5 dispatch_and_record + 1 schema-default + 1 inventory + 1 print-contract + 1 no-bare-ellipsis + 1 placeholder-match (active at C7) + 1 contracts entry. Some tests amortized across phases (e.g. contract tests are bulk-iteration single test functions).

**Canonical preamble v3 sha**: `8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9` — unchanged from Spike II/III. ALLOW_LIST = {v1, v2, v3} unchanged.

**B-9 dogfood result**: **13/13 acceptance criteria PASS**. Run `20260501-133444-035a` (OneShot daily puzzle UTC timezone bug — KST 00:00–08:59 window). 5-section `BUG_REPORT.md` + TL;DR + status:complete; `repro.sh` exit 64 (non-zero, bug reproduces); `verify.sh` exit 0 (fix verified); 4 OneShot source files patched (8 individual `DateTime.now().toUtc()` → `DateTime.now()` and `DateTime.utc(now.year,...)` → `DateTime(now.year,...)` substitutions). canonical preamble v3 sha byte-identical across all 5 dispatch rows. iter1 path not exercised (bug resolved in iter0); Bash-prefix-marker probe 0 attempts.

**Carryforward to Spike V** (3 minor items, not ship blockers):

- M1. `repro.sh` Dart heredoc syntax misfire (`dart - <<EOF` ran as `dart -`, exit 64 via wrong path; non-zero contract still satisfied).
- M2. `verify.sh` is grep-based static check, not behavioral execution.
- M3. Step 2 sub-agent left `## Symptom` sentinel intact in some renderings — orchestrator recovered via title-line extraction; downstream steps unaffected.

All 3 are sub-agent prompt polish (additional `.replace()` literals or example idioms in `repro_step2.md`/`fix_step5.md`); deferred to Spike V's `builder` ★ scope or Spike IV-patch.

**YAML strict-load latent issue (deferred)**: both `bundled/{plan-pack,debugger}/SKILL.md` frontmatter `description` values contain unquoted `: ` (from `(V4 Spike X: ...)` parenthetical). System convention is the inventory scanner's `_parse_yaml_ish` line parser (lenient); strict `yaml.safe_load()` would fail. Out of Spike IV scope (would require touching plan-pack identity-protected SKILL.md). Tracked as future cleanup.

Source spec: `docs/specs/2026-04-30-v4-spike-iv-design.md`. Plan: `docs/plans/2026-05-03-v4-spike-iv.md`. Final memo: `docs/dogfood/spike-iv-final.md`.

Spike IV commits (in order): `020a146` (A1 hook v2) · `d1e9a1b` (A1 α-tighten) · `152ceac` (B1 dispatch_and_record) · `9ad8fd4` (B2 SKILL.md Step 6 + iter_emphasis) · `ca85de4` (B2 D3 Inputs fix) · `1cdd4f9` (B2 I1 contracts) · `90e0e43` (C1 skeleton + inventory) · `6fa1c64` (C2 templates) · `c89a0c4` (C2 polish) · `dd32895` (C3 repro_step2) · `e659dcf` (C3 polish) · `6f49664` (C4 hypothesis_step3) · `a31d726` (C5 root_cause_step4) · `ed9a6df` (C6 fix_step5) · `a2564da` (C7 report_step6 + iter_revisit + SKILL.md completion) · `58c0800` (C7 polish).

### V4 Spike III (2026-04-30, B-8 dogfood ship)

**B-7 carryforward + Spike I final-review carryforward closed**:

- **N1 — PRD schema fix (Phase A)**: `prd_step2.md` rewritten from 2-replace (`{{TASK}}` + phantom `{{PRD_BODY}}`) to arch_step8 7-replace pattern (TASK + 6 section vars + AC marker route). `prd_step3.md` substitutes raw bash into the AC marker (template's existing fence preserved — no nested fence). New guard `tests/unit/test_prd_template_placeholder_match.py`. Eliminates the 6-placeholder leak that triggered F12 in B-7.
- **F12 safety net (Phase B)**: new `server.dispatch_prompt(prompt_file: str) -> str` (load + `wrap_with_preamble`, no placeholder substitution — caller's responsibility per option B from B1 review). `record_dispatch` gains `prompt_file: Optional[str] = None` kwarg + 8-entry `ALLOWED_PROMPT_FILES` allowlist; default soft-warn, `ASSEMBLE_DISPATCH_STRICT=1` for hard ValueError. SKILL.md §"Step dispatch contract" rewritten as 5-step numbered contract referencing `dispatch_prompt`. New tests `tests/unit/test_dispatch_prompt.py` (5 tests).
- **Spike I final-review carryforward (Phase C)**: bare `...` Ellipsis sentinels → `<TBD: 1-line description>` form across 5 sub-agent prompts (prd_step4, arch_step8, adr_step11, ui_step13, cross_doc_step9) + new guard `test_prompts_no_bare_ellipsis.py` (regex catches whitespace-padded, dash-prefixed, bullet-prefixed forms). Sub-agent prompt first-paragraph wording unified: `Print \`WROTE: <absolute path>\` on stdout — main parses with regex \`^WROTE: (.+)$\`. No other prose.` + new guard `test_prompts_print_contract.py`. SKILL.md Step 6 entry/exit options Korean-only (`4-doc` → `네 문서`, `cross-doc` → `문서 간`) + retuned C3 guard. New explicit "Step 6 prompt selector" table at top of `## Step 6 — iteration round-trip` resolving entry-vs-exit selector ambiguity. `ui_step13.md` antipattern keyword list reframed as **conditional signals, not absolute bans** (gradient/glass-morphism/all-purple legitimate when PRD `## Core features` requires; annotate `(domain-required by PRD § Core features)`). `prompts/` directory split into `subagent/` (7 files) + `orchestrator/` (1 file: iter_emphasis.md); `_resolve_prompt_path` resolver supports both layouts; SKILL.md §"Anti-bypass" 8-file allowlist updated.
- **F3 (Korean phrasing drift) — accepted (Phase D)**: 9 sub-agent inferred phrasing artifacts from B-7 (`도구파 경량`, `리시완 DB`, etc.) accepted as inference limits per Spike III memory § option C. No code change; manual post-edit at distribution time. F3 reopens only if B-N rate climbs past ~12 violations per run.

**B-8 dogfood result**: 12/13 acceptance criteria full PASS + 1 partial PASS (#13 first-pass clean, iter1 path 3 carryforwards). Run `20260430-211523-212a` (md-sync — markdown notes sync CLI). PRD/ARCH/ADR/UI_GUIDE all rendered with `{{...}}` zero leaks, AC fence single (no nested), `<TBD: ...>` zero leaks, 5 ADR decisions with 5 sub-headings each, Cross-doc review (first-pass + iteration 1) headings separated correctly, COUNTS keys (`resolved`/`unresolved`/`new`) consistent across both passes, Step 6 entry+exit options Korean-only verified live.

**Carryforward to Spike IV** (3 items, all iter1-path):

- A. iter1 4-way dispatch missing from `dispatches.jsonl` (orchestrator skipped `record_dispatch` after `dispatch_prompt` in iter1 emphasis path). Fix: SKILL.md Step 6 yes-path detail step 3 enumerate 4 `record_dispatch` calls.
- B. iter1 `(no change)` doc mtime not updated — sub-agents elided verbatim write despite spec. Fix: tighten `iter_emphasis.md` step-1 or relax spec to skip-with-audit-row.
- C. ADR sub-agent "Bash command prefix marker" hook v1 false-negative (intentional guard probe; `bash -c '# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE\n...'` pattern passes). Fix: `hooks/guard_run_dir.sh` Bash branch tightened to require marker as first comment of `python3 -c` invocation only; new hook test case for the false-negative shape.

Source spec: `docs/specs/2026-04-30-v4-spike-iii-design.md`. Plan: `docs/plans/2026-05-02-v4-spike-iii.md`. Final memo: `docs/dogfood/spike-iii-final.md`.

Spike III commits (in order): `9e7bbf5` (spec+plan), `044768f` (Phase A1), `6174852` (Phase B1), `51868bd` (B1 fix option B), `b4fbb4a` (B1 polish), `4eb0e75` (Phase B2), `1ba9dc4` (B2 polish), `89b861e` (Phase C1), `2ef13f5` (C1 polish), `c5df204` (Phase C2), `7d340e1` (Phase C3), `3dcfe84` (Phase C4), `1cb173f` (Phase C5), `14e4d21` (Phase C6), `a92277d` (Phase D1).

### V4 Spike I (2026-04-30, post-B-5 distribution prep)

**Sub-agent path-only return contract**: `bundled/plan-pack/SKILL.md` re-architected (732→323 lines) so sub-agents call `write_run_artifact` themselves and return only `WROTE: <path>` on stdout. Main Claude has zero artifact body access — eliminates the body-write bypass observed across 4 dogfoods (B-prime+K). 8 new prompt files in `bundled/plan-pack/prompts/` (prd_step2/3/4, arch_step8, adr_step11, ui_step13, cross_doc_step9 are sub-agent prompts with `ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE` magic marker; iter_emphasis is orchestrator-facing).

**harness-preamble v2**: rules 5 (한국어 quality — 좌히기/PRD emp/키디텍터 직역체 금지) + 6 (anti-downscale — task scope은 seed이지 contract가 아니다) added (J-5, L). sha256 changes `858e9ff1...→ df274505...`; pre-cutoff dogfood data accepted via `verify_dispatches` ALLOW_LIST.

**hook v1 — Bash matcher**: `hooks/guard_run_dir.sh` adds Bash branch that blocks main Claude's `python3 + write_run_artifact` patterns; sub-agent legitimate dispatch passes via `ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE` magic marker. `~/.claude/settings.json` PreToolUse matcher extended to `Edit|Write|NotebookEdit|Bash` (backup at `~/.claude/settings.json.pre-spike-i`).

**Step 6 yes-path label fix (J-6)**: `"yes — refine all four"` → `"yes — 강조점 인터뷰 + 4-doc 재작성 + cross-doc 재검증"` (entry + multi-iter both).

**Tests**: +4 hook test cases (`test_guard_bash_matcher.py`), +4 sub-agent path-only contract tests (`test_plan_pack_subagent_path_return.py`), +2 anti-fallback contract tests (`test_plan_pack_anti_fallback.py`), +2 harness ALLOW_LIST tests (`test_harness_dispatches.py`), +1 magic marker test in `test_plan_pack_skill.py`. Re-anchored 25 phrase-stale `test_plan_pack_skill.py` assertions and 6 of 8 `tests/contracts/contracts.json` entries to compressed SKILL.md (2 contracts removed — covered by runtime tests in `test_harness_dispatches.py`). Final: 192 passed, 0 failed.

**Out of scope (deferred to Spike II)**: J-1/J-2/J-3/J-4 (menu layer dynamic Recommended) — Spike II. Item A multi-iter stop condition algorithm — Spike II. Items C/D/E/F (test pattern hygiene) — quality/hygiene passes.

**B-6 acceptance criteria**: 0 main direct-write, 0 hook block on legitimate sub-agent path, new label workflow alignment, Korean quality clean, anti-downscale clean. See `docs/dogfood/spike-i-readiness.md`.

Source spec: `docs/specs/2026-04-30-v4-spike-i-design.md` (commit `eeb6c96`).

Spike I commits (in order): `6598788` (preamble v2), `5d9c325` (PRD prompts), `93da925` (ARCH/ADR/UI prompts), `877715f` (cross_doc + iter_emphasis), `02d2237` (SKILL.md rewrite), `9532dfa` (SKILL.md fix — role disambiguation + COUNTS missing), `cceec77` (test_plan_pack_skill.py grep), `95af374` (Task 6.5 — 25 stale assertions), `0e85dab` (sha256 + research memo), `9d4f254` (harness.py wrote_path + ALLOW_LIST), `17acc98` (hook Bash matcher), `0fbee91` (hook test cases), `14af40a` (subagent path-only contract test), `8e9555b` (anti-fallback contract test), `8611b0d` (contracts.json registry cleanup).

### Changed (MED/LOW ambiguity hygiene — Item E continuation)
- `bundled/plan-pack/SKILL.md` fresh ambiguity audit (post B-7 + cap-reached state of the doc). The original Hygiene Pass (commit `e4f37df`) resolved 4 HIGH-priority items; the 4 MED + 1 LOW items it deferred were not captured to disk anywhere. The SKILL has changed substantially since (B-5 Findings, B-7 dispatches.jsonl additions), so this pass surfaces 5 actionable items via a fresh audit dispatch instead of archaeology.
- **MED-1** (Step 6 §"Iteration write order" step 2): "or sequentially after Steps 2+3 if you prefer simpler control flow" granted latitude that step 4 (same section) immediately revoked with "MUST NOT be the default + General 'Agent-call budget caution' is no longer sufficient grounds". Edit: pinned step 2 to MUST-parallel and pointed at step 4 as the single source of fallback exceptions.
- **MED-2** (Step 4 §"consistency review" role mapping): unbalanced parenthesis "(preferred: codex:codex-rescue, then superpowers:code-reviewer; fallback: general-purpose with the bare task prompt. (V4 spec memory describes a..." left "with the bare task prompt" syntactically ambiguous. Edit: closed the role-list paren after `general-purpose`, lifted "bare task prompt" into a stand-alone clause, and turned the V4 spec note into a separate sentence.
- **MED-3** (Step 6 entry prompt vs §"User exit override"): the line-592 prompt ("Run one iteration?" with "yes — refine all four"/"no — done") and the line-705 prompt ("Continue iterating?") could collide on iter≥2 boundaries since neither referenced the other. Edit: pinned the entry prompt to `iteration_count == 0` only, with explicit hand-off to §"User exit override" for `iteration_count ≥ 1` so the two prompts never both fire on the same boundary.
- **MED-4** (Step 6 §"Orchestrator enforcement" step 2): "appears verbatim in PRD `## Core features`, or is a direct elaboration of one of those features" — "direct elaboration" had no operational test, so two orchestrators on the same return string could disagree on which names get stripped (step 3). Edit: replaced the subjective predicate with a string-match-only rule covering bullet text + sub-bullet/elaboration text.
- **LOW-1** (Step 4c outcome): "Iteration-mode absorption arrives in Step 6 (Task 7)" — "Task 7" was a stale phase-development tracker reference an orchestrator could not resolve. Edit: dropped the tracker reference and pinned the runtime contract — Step 4 always appends, never re-dispatches; absorption is Step 6's job.

### Notes (MED/LOW ambiguity hygiene)
- Honest disclosure: the original 4-MED + 1-LOW list from the Hygiene Pass `superpowers:code-reviewer` audit was never captured to disk (commit `e4f37df` only listed the 4 HIGH items). This pass therefore audits the *current* SKILL.md, not the original audit's deferred items. The 5 items here may differ from what the Hygiene Pass had in mind. Both interpretations of Item E are honored — the original 4-HIGH fixes shipped under that label, and these 5 lower-priority items now ship as the "Item E continuation" closure.
- Diff scope: `bundled/plan-pack/SKILL.md` (5 surgical edits) + CHANGELOG.md. No code, no tests, no contracts changes (none of the edited lines are pinned by `tests/contracts/contracts.json`). No regression: 181 passed (unchanged from B-7 commit baseline).
- Item E now has both threads closed — HIGH thread (`e4f37df`) and MED/LOW thread (this commit). Distribution-prep ledger has no remaining quality-pass items at the SKILL.md instruction-clarity layer.

### Added (cap-reached termination path on-disk closure — synthetic)
- `runs/20260429-cap-reached-synthetic/iteration_state.json` (channels dir, not in repo): self-labeled synthetic state showing 7 iterations with NEW ≥ 1 each → `termination.reason: "cap-reached"`, `iteration_at_stop: 7`, `stop_condition_satisfied_consecutively: 0`. `supplemental_run_metadata.synthetic: true` + prose `note` make synthetic provenance explicit at the JSON level.
- `runs/20260429-cap-reached-synthetic/NOTES.md` (channels dir): provenance + integrity disclosure. Spells out what the synthetic artifact does prove (cap-reached arithmetic) and does not prove (B5.1 parallel × 7, B5.7 byte-identity × 7). Includes a small `python3 -c` integrity-check snippet a reader can paste to confirm the JSON is well-formed and self-labeled synthetic.
- `docs/dogfood/phase-b-5.md` § "Supplemental run: iter2 + iter3 ... B5.7 evidence backfill" updated: the prior "cap-reached remains the one termination path with no on-disk replayable evidence" line is struck and pointed at a new § "Cap-reached termination path closure (synthetic)". The new section documents the synthetic-vs-real distinction and includes the 3-row table mapping each termination path to its run dir + real/synthetic status.

### Notes (cap-reached closure)
- All 3 multi-iteration loop termination paths (`user-requested-stop`, `stop-condition-met`, `cap-reached`) now have on-disk evidence. Two are from real loops (`runs/20260429-135600-3b6d/`); the third is honestly synthetic (`runs/20260429-cap-reached-synthetic/`) with explicit self-labeling at every level (JSON field + prose note + companion NOTES.md). Future contributors who want real cap-reached evidence can replace the synthetic dir with a genuine 7-iter cycle — the path is unblocked.
- Diff scope: `docs/dogfood/phase-b-5.md` + `CHANGELOG.md` + 2 files in `~/.claude/channels/.../runs/20260429-cap-reached-synthetic/` (outside repo). No code changes, no test changes. Test count unchanged: 181.

### Added (B-5 Item B-7 — `runs/<rid>/dispatches.jsonl` replayable evidence)
- `server/harness.py` gains 3 new public symbols: `record_dispatch(run_id, step, prompt_text, *, subagent_type, description)` appends a hash-only JSONL record to `runs/<run_id>/dispatches.jsonl`; `verify_dispatches(run_id)` reads the JSONL and asserts every recorded `preamble_sha256` matches `canonical_preamble_sha256()`; `canonical_preamble_sha256()` returns the audit constant (sha256 of the on-disk preamble file). Schema is hash-only — no full prompt text persisted, so `dispatches.jsonl` is privacy-safe and compact.
- `server/__init__.py` exports the 3 new symbols via the canonical facade.
- `tests/unit/test_harness_dispatches.py` — 13 new tests covering: file creation, schema correctness, sha256 alignment with canonical, append behavior across multiple records, unwrapped-prompt degraded mode, run_id validation (path-traversal rejection + empty/leading-dot/separator rules), step required, missing-preamble file → `canonical_preamble_sha256()` returns None, `verify_dispatches` green/red/missing-file/empty-file branches, smoke test against the actual repo preamble file (sha `858e9ff1...e159` confirmed).
- `tests/contracts/contracts.json` adds 2 entries: `B-5-B7-dispatches-jsonl-required` (locks the "MUST also call record_dispatch ... runs/<rid>/dispatches.jsonl" clause under § Step 2) and `B-5-B7-verify-dispatches` (locks the "verify_dispatches(rid) reading the JSONL" audit method clause). Both now under contracts meta-test parametrization (Item D).

### Changed (B-5 Item B-7)
- `bundled/plan-pack/SKILL.md` § Step 2 §"Preamble byte-identity" gains a new sub-section §"Replayable on-disk evidence (`runs/<rid>/dispatches.jsonl`)" — documents the `record_dispatch` mandatory call after each `wrap_with_preamble` + dispatch, schema fields list, and points at `verify_dispatches(rid)` for replayable audit. Existing §"Preamble byte-identity" verbatim block (contract `B-5-B2-preamble-byte-identity`) untouched. The new sub-section converts gate B5.7 from orchestrator self-report ("the orchestrator claims byte-identity") to replayable disk audit ("`verify_dispatches` reads the JSONL and computes per-record sha256 against canonical").

### Notes (B-5 Item B-7)
- This closes the B5.7 evidence path #3 — orchestrator self-report is now backed by a replayable on-disk audit. iter2/iter3 supplemental run (commit `7dd49f3`) noted "self-report only — `runs/<rid>/dispatches.jsonl` server hook for replayable verification remains a future B5.7 enhancement". This change is that enhancement.
- Test count: 179 (166 + 13 dispatches).
- Diff scope: `server/harness.py` + `server/__init__.py` + `tests/unit/test_harness_dispatches.py` (new) + `tests/contracts/contracts.json` (+2 entries) + `bundled/plan-pack/SKILL.md` (+1 sub-section under Step 2) + CHANGELOG.md. No regression in existing 166 tests. Existing run dirs (e.g. `runs/20260429-135600-3b6d/`) do not gain `dispatches.jsonl` retroactively — the file only appears for runs that explicitly call `record_dispatch`. This is intended; the supplemental dogfood §"Honest dispatch trace caveat" already documents that the iter2/iter3 sha self-report happened before this hook landed.
- Privacy posture: hash-only schema means user-product content (PRD/ARCH/etc.) is NOT persisted in `dispatches.jsonl`. Safe to commit run dirs without redaction (though by current convention runs live in `~/.claude/channels/` outside the skill repo).

### Changed (B-5 Finding #3 — iter2 + iter3 supplemental run)
- `runs/20260429-135600-3b6d/iteration_state.json`: extended from 2 iteration entries (first-pass + iter1) to 4 (adds iter2 + iter3). `termination.reason` updated from `user-requested-stop` to `stop-condition-met`, `iteration_at_stop` 1 → 3, `stop_condition_satisfied_consecutively` 0 → 2. Added `supplemental_run_metadata` block recording dispatch form per iteration, preamble sha256 self-report, and `started_after_master_commit: a7fb8b3`.
- `runs/20260429-135600-3b6d/PRD.md`: Goal sentence resolution clause `(≥1080p)` → `(긴 변 ≥1920px, ≈1080p)` to align unit with ARCH `≤1920px 긴 변`. Closes iter1 NEW Finding #4 (unit drift).
- `runs/20260429-135600-3b6d/UI_GUIDE.md`: Screen C bullet 3 extended with "30초 초과 시 Screen D로 전환" transition; new Screen D — Failed (OCR 실패/타임아웃) section appended (안내 텍스트 + UploadZone 재노출 + 톤다운, 레드 액센트 미사용); Color tokens 섹션 끝에 token migration note 1단락 추가 (`--color-text-primary` → `--color-text` / `--color-text-secondary` → `--color-text-muted` / `--color-accent-pressed`는 `filter: brightness(0.85)`로 통합). Closes iter1 NEW Finding #3 (Screen C timeout) and Finding #2 (token rename note).
- `runs/20260429-135600-3b6d/ADR.md`: Decision 5 신설 (30초 SLA 초과 시 텍스트 fallback Screen D로 전환 — Context/Decision/Reasoning/Tradeoffs/Rejected alternatives 4개 reject 명시). Cross-doc review section heading bump `(iterations 1–2)` → iter2 추가 후 `(iterations 1–3)` → iter3 supplemental block 추가. Decisions 1-4 byte-identical (verbatim preservation 적용).
- `docs/dogfood/phase-b-5.md`: Finding #3 entry status updated (`No action needed` → `CLOSED post-merge via supplemental iter2+iter3 run`). § "Status update (post-merge)" updated to reference Finding #3 closure branch + supplemental section. New § "Supplemental run: iter2 + iter3 (Finding #3 closure + B5.7 evidence backfill)" with cycle summary table, iter2 closure detail, iter3 confirmation pass, honest dispatch trace caveat (iter2 split as 1+3 / iter3 clean 4-way), B5.7 evidence delta narrative.

### Notes (B-5 Finding #3 closure)
- Loop termination paths now exercised on disk: `user-requested-stop` (original iter1) + `stop-condition-met` (this supplemental cycle). `cap-reached` remains the one path with no replayable evidence — closing it would require contrived synthetic input; left as future exercise.
- Sub-agent dispatch quality: iter2 was split (PRD solo + ARCH/UI_GUIDE/ADR 3-way) due to orchestrator implementation lapse, not platform limit (per `docs/research/2026-04-29-platform-limit.md`). iter3 was true 4-way single-message. Documented honestly in supplemental section.
- Preamble byte-identity: all 8 dispatched prompts (4 iter2 + 4 iter3 sub-agents + 2 cross-doc reviews) used canonical 256-byte preamble (sha256 `858e9ff1cdc05ca73bb4009aab3acfc841169b30873d2fb00f2dfd546b86e159`). Self-report only — `runs/<rid>/dispatches.jsonl` server hook for replayable verification remains a future B5.7 enhancement.
- Test count: 166 passed (no test changes — this is run-artifact + documentation).
- Diff scope: `runs/20260429-135600-3b6d/*` (PRD/UI_GUIDE/ADR/iteration_state.json) + `docs/dogfood/phase-b-5.md` + CHANGELOG.md. SKILL.md untouched. Server infrastructure (gate B5.4) untouched. Tests + contracts registry untouched.

### Changed (B-5 Findings #1 #2 #4)
- `bundled/plan-pack/SKILL.md` Step 6 iteration scope discipline block: extended the verbatim constraint with two new clauses — (a) "Existing sections that are not the explicit target of the iteration emphasis MUST be returned verbatim — do not reword Reasoning/Tradeoffs/Rejected-alternatives blocks just because you are re-emitting the document" closes Finding #1 (iter1 ADR reworded Decisions 1-3); (b) "Pre-existing identifiers (variable names, token names, module names, component names) MUST NOT be renamed unless the rename IS the requested change; maintain identifier continuity across iterations" closes Finding #2 (iter1 UI_GUIDE renamed `--color-text-primary` → `--color-text` without a request). The B-4 origin paragraph below the constraint was rewritten to summarize both B-4 (scope-creep) and B-5 (cosmetic drift) origins.
- `bundled/plan-pack/SKILL.md` Step 9 cross-doc review prompt: added a 7th finding category — "Numerical / unit consistency (cross-doc)" — with PRD `≥1080p` vs ARCH `≤1920px long edge` as the canonical example. Closes Finding #4 (iter1 ARCH-PRD unit drift).

### Added (B-5 Findings)
- `tests/contracts/contracts.json` gains 3 entries: `B-5-finding1-verbatim-preservation`, `B-5-finding2-no-rename`, `B-5-finding4-unit-consistency`. Locks the new clauses against future drift (Item D meta-test catches removal).
- `docs/dogfood/phase-b-5.md` § Findings: status note marking #1, #2, #4 as addressed in this branch. #3 remains open as a domain-level (not workflow-contract) iter-2 design question.

### Notes (B-5 Findings)
- Test count: 166 passed (163 + 3 new contracts meta).
- Diff scope: bundled/plan-pack/SKILL.md + tests/contracts/contracts.json + docs/dogfood/phase-b-5.md + CHANGELOG.md. Server infrastructure unchanged.

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
