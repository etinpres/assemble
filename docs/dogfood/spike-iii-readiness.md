# Spike III post-implementation readiness (B-8 dogfood prep)

## Spike III scope (Phase A–C landed, Phase D no-code)

- **Phase A**: N1 — `prd_step2` 7-replace + `prd_step3` raw AC bash (commit `044768f`).
- **Phase B**: F12 safety net — `dispatch_prompt(prompt_file)` (load + preamble wrap, allowlist-checked) + `record_dispatch(prompt_file=...)` audit field. Initial commit `6174852`; option-B simplification fix `51868bd`; doc polish `b4fbb4a`. SKILL.md Step dispatch contract update `4eb0e75`; markdown list polish `1ba9dc4`.
- **Phase C**: 6 final-review carryforwards from Spike I — Ellipsis sentinels (`89b861e` + polish `2ef13f5`), WROTE wording (`c5df204`), Step 6 Korean tokens (`7d340e1`), Step 6 prompt-selector table (`3dcfe84`), `ui_step13` antipattern reframe (`1cb173f`), `prompts/` subdir split (`14e4d21`).
- **Phase D**: F3 Korean phrasing — *accepted, no code change*.

Baseline at start: master `23fa6c6`, pytest 220/220.
Baseline at end of Phase D: pytest **231** passing, master HEAD as of D1 commit.

Canonical preamble v3 sha256: `8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9` (unchanged from Spike II — Spike III did not touch preamble bytes).

## F3 acceptance decision

B-7 dogfood (run `20260430-151140-4945`) surfaced ≥9 sub-agent-inferred Korean phrasing artifacts ("도구파 경량", "리시완 DB", "미니멀 평수", "신택스 하이라이트", "능속도 저하", "보일플레이트", "토큰 해서 애니메이션", "캐러 톤", "스로우링"). These are sub-agent inference limits, not template bugs.

Options considered:
- **A**. Add more prompt examples — Spike II already tried; diminishing returns observed.
- **B**. Post-hoc Korean lint hook (sub-agent output validator + re-write dispatch on violation) — high cost, low ROI for 1-person dogfood.
- **C**. **Accept the limit** — natural-Korean polish moves to manual post-edit at distribution time (V4 ship gate).

**Decision**: **C**. F3 reopens only if a future B-N dogfood shows the rate climbing past ~12 violations per run.

## B-8 dogfood acceptance criteria

Per spec §3 (`docs/specs/2026-04-30-v4-spike-iii-design.md`), 13 criteria gate Spike III's exit:

1. `PRD.md` rendered from a fresh dogfood run has zero `{{...}}` literal placeholders. (Phase A1 fix + integration evidence under `runs/<rid>/PRD.md`.)
2. `PRD.md` AC bash block has exactly one ` ``` ` fence pair (no nested). (Phase A1 fix.)
3. Informal `record_dispatch(prompt_file="evil.md")` raises `ValueError` under strict mode. (Phase B1 unit test.)
4. `dispatch_prompt` rejects unknown prompt file with `ValueError`. (Phase B1 unit test.)
5. `dispatch_prompt` for known file returns wrapped prompt with all `{{KEY}}` tokens preserved verbatim (caller-side substitution). (Phase B1 option-B contract.)
6. No bare `...` line in any prompt save-block template. (Phase C1 guard.)
7. Every sub-agent prompt's first paragraph carries `Print \`WROTE: <absolute path>\``. (Phase C2 guard.)
8. SKILL.md `AskUserQuestion` Korean options contain no `4-doc` / `cross-doc` tokens. (Phase C3 guard.)
9. SKILL.md Step 6 begins with prompt-selector table. (Phase C4.)
10. `ui_step13.md` antipattern list reframed as conditional signals. (Phase C5.)
11. `prompts/` split into `subagent/` + `orchestrator/`; allowlist updated. (Phase C6.)
12. All 231 tests pass after each Phase commit. (CI gate, current.)
13. **B-8 dogfood**: 0 informal sub-agent dispatch, 0 placeholder leak, 0 nested fence. (Pending — runs in fresh session.)

Items 1-12 are landed and CI-verified. Item 13 is the B-8 dogfood gate.

## What did NOT change in Spike III (deferred)

- V3 concierge "(Recommended)" labels (M1 → Spike V).
- Other ★ candidate bundles (`builder`, `debugger`, `reviewer` — Spike IV).
- F3 Korean lint hook (accepted, no code).
- Spike I sub-agent path-only return contract (identity protection — unchanged).
- Spike II 8-file allowlist / hook v1 / `update_iteration_state` (identity protection — unchanged).

## B-8 dogfood task candidates (form-distinct from B-6 / B-7)

B-6 was a single-page web diary; B-7 was an Ollama desktop chat. B-8 should exercise different shapes:

1. **Markdown notes sync CLI with conflict resolution** — exercises `## External dependencies` (filesystem only) + AC-bash testability (e.g. `git diff -q | grep -c conflict`).
2. **PWA RSS reader, no backend** — exercises browser API surface + offline cache vs. PRD `## Excluded from MVP`.
3. **Telegram bot + cron memo digest** — exercises both `## External dependencies` (Telegram API) and AC-bash testability (e.g. `bot reply contains today's digest count`).

형 picks one of these (or substitutes a form-distinct task) and runs `/assemble` in a fresh session.

## After B-8: 13-criterion mapping protocol

When 형 captures the B-8 transcript and opens a follow-up session ("B-8 결과 정리해" or attaches captures):

1. Map each transcript event → 13 criteria, point-by-point.
2. All 13 PASS → Spike III ships. Update CHANGELOG `[Unreleased]`. Open `docs/dogfood/spike-iii-final.md` with PASS evidence.
3. Some FAIL → carryforward extraction. Decide Spike IV (★ candidate bundles), Spike V (V3 concierge), or Spike III patch.
4. F3 still accepted unless violation rate > ~12/run (open Spike III patch only if so).

## Source

- B-7 dogfood transcript: 형 직접 캡처 9 화면 (run `20260430-151140-4945`).
- Spec: `docs/specs/2026-04-30-v4-spike-iii-design.md`.
- Plan: `docs/plans/2026-05-02-v4-spike-iii.md`.
- Memory: `~/.claude/projects/-Users-yonghaekim-my-folder/memory/project_assemble_v4_spike_iii.md`.
- Sibling readiness memos: `docs/dogfood/spike-i-readiness.md`, `docs/dogfood/spike-ii-readiness.md` (if exists).
