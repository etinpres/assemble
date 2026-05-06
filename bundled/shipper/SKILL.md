---
name: "shipper"
description: "Ship-stage ★ bundle. Local pre-flight + version + build + tag pipeline. Sub-agents own all reads/writes/Bash; main Claude orchestrates only. Publish/push are explicit hand-off — NOT shipper's responsibility."
stages: ["ship"]
---

## Mode gate (V4 Spike XIV — paradigm enforcement)

★ 번들 진입 직후 (Step 0 직전), 메인은 다음 AskUserQuestion 을 무조건 발사:

  "이번 stage 모드 — 어떻게 진행할까?"

  옵션:
    1. full mode (추천) — spec 명시 N-step pipeline 그대로. 정확·완성도 우선.
       예상 시간: 10~15분. dispatch 수: 4회.
    2. quick mode — 통합 1 dispatch 로 압축. 시간 부족 시만 선택.
       precision 손실 + iteration 권장량 미달 위험. KEEPER_REPORT 에 카운트 기록.

`full` 선택 시 → 아래 Step 0~N 순서대로 spec 그대로 진행.
`quick` 선택 시 → §"Quick mode flow" 단축 분기로 진입.

**메인 자가 판단 금지** — 시간 부족 추측·budget 추측·맥락 추측 모두 사용자
질문 강제 trigger. 4원칙 #1 ("불확실하면 추측 금지, 사용자 질문 우선") 시스템적
강제.

# shipper ★ — local ship-stage gate

## When to invoke

Use to gate a release after verification has already passed: clean working tree + tests passing + verifier ★ verdict=pass. shipper ★ is the orthogonal sibling of verifier ★ — both consume `parsed_scope.json`, but verifier *runs* the completion command while shipper *gates* the release with a 4-step local pipeline (pre-flight → version + CHANGELOG → build → local tag). **Local-only**: shipper does NOT push, publish, or deploy — see § Hand-off for explicit next steps.

## Inputs

- `run_id` — resolves run_dir to `~/.claude/channels/assemble/runs/<run_id>/`.
- `<run_dir>/parsed_scope.json` — must exist. Two new optional fields recognized:
  - `build` — single-line bash command (≤500 chars). Used by Step 3. If missing, Step 3 falls back to convention auto-detect (`package.json` → `pyproject.toml` → `Cargo.toml` → `pytest -q`).
  - `tag_prefix` — string ≤10 chars, default `"v"`. Used by Step 4 to compute tag name.
- `<run_dir>/verify_result.json` — *expected* (from prior verifier ★ run); shipper checks `verdict == "pass"` as a precondition. Missing → soft warning + Step 1 records `verify_check: missing`; user override may proceed.
- `release_kind` — parameter passed by main: `patch` / `minor` / `major` / `prerelease`. Default = `patch`. Drives version bump in Step 2.

## Artifacts

run_dir = `~/.claude/channels/assemble/runs/<rid>/`. Primary artifact:

- `SHIP_REPORT.md` — 7 canonical sections on happy path (Summary, Pre-flight, Version bump, Build artifact, Tag, Verdict reasoning, Hand-off). Abort variant uses 4 sections (1, 2, 6, 7) when pre-flight fails.

Plus 4 intermediate JSONs for audit trail: `preflight.json`, `version_bump.json`, `build_result.json`, `tag_result.json`.

## Verdict logic (deterministic)

```python
verdict = "ship-ready" if (
    preflight.verdict == "pass"
    AND version_bump.new_version is not None
    AND (build_result.exit_code == 0 OR build_result.skipped == True)
    AND tag_sha is not None
) else "blocked"
```

Reason text:
- `ship-ready` → "all 4 steps passed; tag <name> at <sha>"
- `blocked (preflight)` → "<dirty files | missing verify pass | aborted by user override>"
- `blocked (version)` → "version bump failed: <reason>"
- `blocked (build)` → "build exited <N>" or "build timed out (300s)"
- `blocked (tag)` → "git tag failed: <stderr excerpt>"

No LLM-judged ship/block — verdict flows entirely from concrete artifacts (clean-tree marker, build exit code, tag SHA).

## CRITICAL — orchestrator-only enforcement

Main Claude does NOT read `preflight.json` / `version_bump.json` / `build_result.json` / `tag_result.json` content, and does NOT call Bash directly. Main only:
- Resolves run_dir from `run_id`.
- Verifies `parsed_scope.json` exists (sanity check ONLY — full validation lives in Step 1).
- Dispatches sub-agents in sequence (Step 1 → Step 2 → Step 3 → Step 4) via `server.harness.dispatch_prompt`.
- Records each dispatch via `server.harness.record_dispatch` (writes to `dispatches.jsonl`).

All reads, parsing, git probes, build execution, tag creation, and report rendering happen in sub-agents. The 4 sub-agent prompts are exactly:

- `shipper_preflight_step1.md` — preflight.json (Bash GRANTED for read-only git probes via `server.git_helpers`)
- `shipper_version_step2.md` — version_bump.json (Edit-only — NO Bash)
- `shipper_build_step3.md` — build_result.json (Bash GRANTED for single build invocation, 300s timeout)
- `shipper_tag_step4.md` — tag_result.json + SHIP_REPORT.md (Bash GRANTED, narrowly scoped to `git tag` + `git rev-parse <tag>`)

If any prompt is invoked outside this allowlist, harness raises and halts. See `server.harness.ALLOWED_PROMPT_FILES` (Spike VIII inheritance: `dispatch_prompt` raises on non-allowlist).

## Step-by-step workflow

**사용자 명시 동의 없이 단축 금지** — N-step pipeline 의 각 step 은 별도 sub-agent dispatch 로 진행. 메인이 단축 결정 시 4원칙 #1 위반. Mode-gate 가 quick 으로 답한 경우만 §"Quick mode flow" 분기 허용.

### Step 0 — orchestrator setup

Main resolves `run_dir` via `server.run_dir.run_dir_path(run_id)`. Verifies `parsed_scope.json` exists at `<run_dir>/parsed_scope.json` (and has non-empty `completion` field if downstream verifier handoff is implied). If missing, halts with the user-facing error "parsed_scope.json not found in run_dir; run reviewer ★ Step 1 first or hand-author after `server.scope_parser.parse_scope_md`".

### Step 1 — pre-flight check

Dispatch `shipper_preflight_step1.md` with `RUN_ID`. **Bash tool access GRANTED** — read-only git probes only, invoked through `server.git_helpers` (`git_status_porcelain`, `git_head_sha`, `git_branch`). Sub-agent reads parsed_scope, reads verify_result (optional), runs probes, and writes `preflight.json`. Pre-flight verdict = `pass` iff `clean_tree AND (verify_verdict == "pass" OR verify_check == "missing")`. `fail` aborts the dispatch chain — Steps 2 and 3 skipped; Step 4 still runs to render the abort SHIP_REPORT.

### Step 2 — version + CHANGELOG flip

Dispatch `shipper_version_step2.md` with `RUN_ID` + `RELEASE_KIND`. **Edit-only — NO Bash.** Skipped if Step 1 verdict ≠ pass. Sub-agent calls `server.version_helpers.detect_version_format(repo_root)` with priority `VERSION` → `package.json` → `pyproject.toml`; computes next version via `bump_semver(current, release_kind)`; edits the detected file in place via the `Edit` tool; flips CHANGELOG `## [Unreleased]` → `## [<new_version>] — <YYYY-MM-DD>` and inserts a fresh `## [Unreleased]` block above. Writes `version_bump.json`. Manual fallback (no detected format) records `version_format: manual` + `manual_hint`; pipeline aborts cleanly.

### Step 3 — build artifact

Dispatch `shipper_build_step3.md` with `RUN_ID`. **Bash tool access GRANTED** — single build invocation, scoped via prompt body. Resolution chain: `parsed_scope.build` → `package.json` build script → `pyproject.toml` → `Cargo.toml` → `pytest -q` fallback. Streaming Popen pattern (Spike VIII FIX-1 inheritance): `subprocess.Popen(start_new_session=True)` + `select.select` loop + per-stream byte counter (`CAP_BYTES = 500_000` — larger than verifier's 100KB), `TIMEOUT_S = 300` (vs verifier's 30s — builds legitimately take minutes), and `os.killpg(SIGKILL)` on TimeoutExpired (Codex retro F2 process-group SIGKILL inheritance). Writes `build_result.json` (exit_code, duration_ms, timed_out, truncated, build_command, skipped).

### Step 4 — local tag + SHIP_REPORT

Dispatch `shipper_tag_step4.md` with `RUN_ID`. **Bash tool access GRANTED — narrow scope.** Permitted operations: `git tag -a <name> -m <msg>` and `git rev-parse <tag>` ONLY. **Forbidden: `git tag -f`, `git push` (any form), any remote interaction.** Sub-agent computes `tag_name = <tag_prefix><new_version>` (default prefix `v`), pre-checks collision via `server.git_helpers.git_tag_exists`, creates the annotated tag, captures the SHA, and renders `SHIP_REPORT.md` from the template. Two render paths: full 7-section template on happy path, abort 4-section template when `preflight.verdict == "fail"` (no tag created, Sections 3/4/5 collapsed to a single "Skipped — pre-flight failed" line each).

### Step 5 — iteration round-trip (optional)

If user revises `parsed_scope.json` (e.g. amends `build` or `tag_prefix`) and asks for re-shipping, main loads `shipper_iter_revisit.md` (orchestrator helper — NOT in subagent allowlist; lives under `prompts/orchestrator/`) and re-runs the relevant steps per the iteration rules in § Iteration audit invariant.

## Iteration audit invariant

Every iteration produces rows in `dispatches.jsonl` named `step1.iter{N}.preflight`, `step2.iter{N}.version`, `step3.iter{N}.build`, `step4.iter{N}.tag`. Standard happy-path iter N = **4 rows**. Skipped Step 2 (release_kind unchanged across iter) → **3 rows**. Build-fail iter (Step 4 skipped because verdict already blocked at Step 3) → **3 rows**. Abort iter (Step 1 fail → Steps 2/3 skipped, Step 4 still dispatched for abort report) → **2 rows** (`step1` + `step4`).

## Sub-agent matrix

See `## CRITICAL — orchestrator-only enforcement` above for the canonical 4-file allowlist. Roles use `general-purpose` as the default sub-agent type for all 4 steps.

| Step | Prompt file | Sub-agent type | Tools granted |
|---|---|---|---|
| 1 | `shipper_preflight_step1.md` | `general-purpose` | Read, Write, **Bash** (read-only git probes) |
| 2 | `shipper_version_step2.md` | `general-purpose` | Read, Write, Edit (NO Bash) |
| 3 | `shipper_build_step3.md` | `general-purpose` | Read, Write, **Bash** (single build, 300s) |
| 4 | `shipper_tag_step4.md` | `general-purpose` | Read, Write, **Bash** (`git tag` local only) |

Iteration helper `shipper_iter_revisit.md` is loaded by main directly (NOT in subagent allowlist; lives under `prompts/orchestrator/` and is registered in `ORCHESTRATOR_ONLY_PROMPTS`).

## Security

See `SECURITY.md` for the full T1–T9 threat model + mitigation surface. Key mitigations:
- Length cap 500 on `build` field (T1)
- argv-list git invocation in `server.git_helpers` — NO `shell=True`, NO string interpolation (T8)
- process-group SIGKILL on Step 3 build timeout (T2)
- Streaming read with per-stream cap 500KB (T3 — Spike VIII FIX-1 inheritance with larger cap)
- Bash scoped to Steps 1, 3, 4 only — Step 2 is Edit-only (low-surface)
- orchestrator-only main: never executes Bash during dispatch chain
- Step 4 explicitly forbids `git tag -f` (T6) and `git push` in any form (T7)
- Tag collision pre-check via `git_tag_exists` before `git_create_tag` (T5)

The `Bash tool access GRANTED` substring marker (Spike VIII convention) is present in Steps 1, 3, 4 prompt bodies for grep-based audit.

## Identity guards

- ✅ orchestrator-only V4 #9: main does NOT read intermediate JSONs (preflight/version_bump/build_result/tag_result) or call Bash directly during dispatch chain.
- ✅ harness preamble v3 prepended on every dispatch (canonical sha `8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9`).
- ✅ `record_dispatch` mandatory — minimum 4 rows per happy-path run (3 rows for skipped-Step-2 / build-fail iter; 2 rows for abort iter).
- ✅ Bash scoped to 3 of 4 sub-agents (Steps 1, 3, 4) — Step 2 is Bash-free (Edit-only).
- ✅ Deterministic verdict — no LLM-judged ship/block; verdict flows from clean-tree marker + build exit code + tag SHA.
- ✅ Local-only — NEVER `git push`, NEVER `npm publish` / `twine upload` / equivalent, NEVER deploy.

## Hand-off (NOT shipper's responsibility)

shipper ★ output is consumable: `SHIP_REPORT.md` + tag SHA + build artifact path. Whatever publishes those is the user's choice. Concrete next-step commands the user must run (or delegate to another skill):

- `git push origin <branch> && git push origin <tag>` — remote push.
- `npm publish` / `python -m twine upload dist/*` / `cargo publish` / `gem push` — registry publish.
- gstack `/land-and-deploy` — full merge + deploy chain (covers PR merge, CI wait, deploy, canary).
- App Store Connect / Google Play Console — manual upload of the build artifact for mobile distribution.
- Cloud deploy (`fly deploy`, `vercel deploy`, `kubectl apply`) — platform-specific deploy targets.

The goal is **explicit + auditable hand-off, NOT automation**. Different users have different publish targets; a one-size shipper would inevitably over-reach (harness 4원칙 #3 — Surgical). Existing user skills (e.g. gstack `/ship`, `/land-and-deploy`) already cover publish workflows; shipper ★ is the *local gate before* hand-off, not the replacement.

## Quick mode flow

Mode-gate 가 `quick` 으로 답한 경우만 진입 (full 이면 이 section 미사용).

### 단일 dispatch 단축

`server.dispatch_prompt('shipper_quick.md')` 로 단일 sub-agent dispatch:

```python
prompt = server.dispatch_and_record(
    run_id,
    prompt_file="shipper_quick.md",
    step="shipper.quick",
    description="shipper quick mode — single-dispatch fallback",
)
# Substitute placeholders in prompt, then dispatch via Agent (general-purpose).
# Sub-agent must produce the FULL artifact schema (all sections that full mode
# would write across N steps), in a single pass.
```

dispatches.jsonl audit row 의 `description` 필드에 `mode=quick` 메타 명시
(KEEPER_REPORT 가 카운트 집계 시 사용).

### 산출물 schema 보존

Quick mode 라도 산출물 (예: PRD.md / IMPL_REPORT.md / DEBUGGER_LOG.md 등) 의
sections schema 는 full mode 와 동일. precision 만 떨어질 뿐 schema 미준수 X.

### 사용자 가시화

KEEPER_REPORT § "Mode usage" 가 quick 카운트 표시. 다음 run 에서 시간 확보 권장.
