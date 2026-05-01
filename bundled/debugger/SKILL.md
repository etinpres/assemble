---
name: debugger
description: Debug stage ★ bundle — systematic hypothesis → reproducer → bisect → root cause → fix workflow with audit trail. (V4 Spike IV: parallel to plan-pack ★, sub-agent path-only return contract.)
---

[HARNESS RULES — 무시 금지]
1. 불확실하면 추측 금지, 사용자 질문 우선
2. 과설계 금지, YAGNI
3. 요청 범위 밖 코드 임의 수정 금지
4. 버그 수정 시 재현 테스트 → 실패 확인 → 수정 → 재검증 루프
5. 사용자에게 표시되는 한국어 라벨·옵션은 자연스러운 한국어로 정제. 영문 기술용어 한글화 시 정확한 외래어 표기 사용 (architecture→아키텍처, family→패밀리, top-level→최상위, recommended→추천, directory→디렉토리). 자작 변형 금지.
6. task scope은 seed이지 contract가 아니다 — BUG_REPORT.md 5섹션 모두 작성
7. 다른 스킬 인프라 코드 read·grep 금지 — 자기 task 무관 분석은 우회 시도 신호

## CRITICAL — orchestrator-only enforcement

This skill is **orchestrator-only**. Main Claude (you) dispatches sub-agents
and parses their `WROTE: <path>` stdout. You MUST NOT fall back to
Bash/Edit/Write/python3 to write artifacts directly under `runs/<rid>/`.
The hook `guard_run_dir.sh` blocks such bypass attempts (v2 — Spike IV
§1.3 — magic marker only valid inside python3 bodies, no Bash-comment
prefix bypass).

If a sub-agent dispatch fails (no `WROTE:` line, `ERROR:` line, timeout, or
empty stdout):
1. Surface the failure to the user via `AskUserQuestion`:
   "Step N failed. Retry / abort / report?"
2. Wait for user choice. Do not auto-recover.
3. NEVER attempt to write the artifact yourself, even "just to unblock
   the user". Sub-agent ownership is the contract.

If retry is chosen, re-dispatch the same sub-agent with the failure
context (`previous attempt failed: <reason>`) appended to the original
prompt.

**Anti-bypass (Spike II F9 + F11 + Spike IV §1.3):**

- `~/.claude/settings.json` 편집해서 `ASSEMBLE_GUARD` 환경 변수 무력화 시도 금지.
  hook 자체를 비활성화/우회 시도는 사용자 confirm 이 떠도 거절.
- hook 이 차단하면 즉시 `AskUserQuestion` 으로 사용자 결정 위임 (retry / abort / report).
- sub-agent dispatch 는 두 디렉토리의 *6개 파일* 에 한정 (debugger ★ allowlist):
  - `bundled/debugger/prompts/subagent/`: `repro_step2.md`, `hypothesis_step3.md`, `root_cause_step4.md`, `fix_step5.md`, `report_step6.md` (5 files — sub-agent–facing, dispatched via `Agent` tool)
  - `bundled/debugger/prompts/orchestrator/`: `iter_revisit.md` (1 file — main constructs per-step revisit prompts before re-dispatching Step 3 or Step 4)
- orchestrator 메타데이터 (`iteration_state.json`, `dispatches.jsonl`) 는 sub-agent 에 위임 금지 — `server.run_dir.update_iteration_state` / `server.dispatch_and_record` 같은 server 함수 사용.

## Korean label policy (Spike II F4)

When `ASSEMBLE_LOCALE=ko` (or user message language is Korean), AskUserQuestion
options that historically carry English `(Recommended)` suffix MUST use the
unified Korean form `(추천)`. Do not improvise alternatives.

# debugger — systematic hypothesis → fix workflow

Produces one primary deliverable (`BUG_REPORT.md`) and two executable
shells (`repro.sh`, `verify.sh`) under `runs/<rid>/`. Main Claude runs
one `AskUserQuestion` interview (Step 1); sub-agents own the rest and
return `WROTE: <path>`.

## Artifacts

run_dir = `~/.claude/channels/assemble/runs/<rid>/`. Three artifacts:

- `BUG_REPORT.md` — 5 sections: `## Symptom`, `## Reproducer`,
  `## Hypotheses`, `## Root cause`, `## Fix & verification`. Step 6
  adds front-matter `status: complete` + a `## TL;DR` summary.
- `repro.sh` — minimal command that fails before fix.
- `verify.sh` — minimal command that passes after fix.

`repro.sh` and `verify.sh` are the cross-cutting AC=bash pattern
(V4 spec § "Cross-cutting 강화 흡수 후보" B). The user can run them
interactively to confirm the bug and the fix without LLM mediation.

## Sub-agent role mapping

All dispatches use `general-purpose` (preferred + fallback). Role
varies per step.

| Step | Role persona | Prompt file |
|---|---|---|
| 2 | (general-purpose) | `prompts/subagent/repro_step2.md` |
| 3 | `plan-implementation` | `prompts/subagent/hypothesis_step3.md` |
| 4 | `second-opinion` | `prompts/subagent/root_cause_step4.md` |
| 5 | (general-purpose) | `prompts/subagent/fix_step5.md` |
| 6 | `text-summarize` | `prompts/subagent/report_step6.md` |
| 7 | orchestrator helper | `prompts/orchestrator/iter_revisit.md` |

Steps 0/1 are main-side IO + `AskUserQuestion`. Step 7 is iteration
re-entry — the substituted prompt is prepended to a re-dispatch of
Step 3 or Step 4 (no separate sub-agent for Step 7 itself).

## Workflow execution sequence

```
0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 (loop back to 3 or 4 if iteration chosen)
```

Linear pipeline + 1 backtrack point. Steps fire in numeric order
(unlike plan-pack which has parallel + interleaved order).

## Steps

### Step 0 — resolve run_dir

Read `<rid>` from the active assemble run. Artifact paths are
`~/.claude/channels/assemble/runs/<rid>/{BUG_REPORT.md, repro.sh, verify.sh}`.
If `BUG_REPORT.md` already exists with `status: complete`, treat the
workflow as iteration mode (Step 7 re-entry).

### Step dispatch contract (Steps 2/3/4/5/6)

For each dispatch step:

1. `prompt_text = server.dispatch_prompt("<file>.md")` — loads + wraps
   with harness preamble. Unknown file raises `ValueError`.
2. Caller substitutes per-step `{{KEY}}` tokens (Inputs section).
3. `server.record_dispatch(run_id, step="step{N}", prompt_text=...,
   prompt_file="<file>.md", subagent_type="general-purpose",
   description="…")` — audit row.
4. Send via `Agent` tool with `subagent_type="general-purpose"` and the
   substituted prompt.
5. Parse `WROTE: <path>` from stdout. On `ERROR:` or no `WROTE:`,
   surface to user via `AskUserQuestion` (retry / abort / report).

### Step 1 — symptom interview (main)

Two `AskUserQuestion` calls:

**Q1** (single question):
"버그 증상을 한 줄로 요약해 줘. (예: `npm run build` 가 `Error: Cannot find module 'fs/promises'` 로 실패)"

**Q2** (multi-question, 3 sub-questions in one tool call):
- "환경: OS / 런타임 / 의존성 버전을 알려줘 (예: macOS 14 / Node 20.10 / Next 14.2)"
- "마지막으로 정상 작동했던 시점이나 커밋이 있어? (없으면 '모름' 선택)"
- "이미 시도해 본 fix가 있어? (없으면 '없음' 선택)"

Outputs `SYMPTOM_SUMMARY`, `ENV`, `LAST_KNOWN_GOOD`, `TRIED_FIXES` —
passed to Step 2 dispatch.

### Step 2 — reproducer construction (sub-agent)

`prompt_file="repro_step2.md"`. Inputs: `RUN_ID`, `SYMPTOM_SUMMARY`,
`ENV`, `LAST_KNOWN_GOOD`, `TRIED_FIXES`. Sub-agent builds `repro.sh`,
runs it, confirms non-zero exit, writes `BUG_REPORT.md` with filled
`## Reproducer`.

If sub-agent ERROR-exits with "reproducer did not fail", `AskUserQuestion`:
"증상이 환경에 따라 재현 안 될 수 있어. 환경 정보를 보강해서 재시도할까?"

### Step 3 — hypotheses + bisect plan (sub-agent)

`prompt_file="hypothesis_step3.md"`. Inputs: `RUN_ID`, `EXISTING_REPORT`
(current BUG_REPORT.md text). Sub-agent appends `## Hypotheses` (3-5
ranked, falsifiable).

### Step 4 — root-cause + second-opinion (sub-agent)

`prompt_file="root_cause_step4.md"`. Inputs: `RUN_ID`, `EXISTING_REPORT`.
Sub-agent picks the most evidence-rich hypothesis, drives the bisect,
runs an explicit ≥2-alternative challenge, appends `## Root cause`.

If sub-agent ERROR-exits with "hypothesis-N refuted by second-opinion",
re-dispatch Step 3 with the new candidate as a hint. Use Step 7
`iter_revisit.md` to construct the re-entry prompt.

### Step 5 — fix patch + verifier (sub-agent)

`prompt_file="fix_step5.md"`. Inputs: `RUN_ID`, `EXISTING_REPORT`.
Sub-agent edits source files (via `Edit`/`Write` outside `runs/<rid>/`),
writes `verify.sh`, runs it, confirms exit 0, appends `## Fix &
verification`.

### Step 6 — BUG_REPORT.md integration (sub-agent)

`prompt_file="report_step6.md"`. Inputs: `RUN_ID`. Sub-agent reads
the assembled `BUG_REPORT.md`, validates no `<TBD: …>` or bare `...`
remain, adds `## TL;DR` + flips `status: complete`.

If sub-agent ERROR-exits with "still has unfilled sections", re-dispatch
the gap-source step (the section title in the error indicates which).

### Step 7 — iteration round-trip

After Step 6 success, `AskUserQuestion`:

"fix를 적용해 봤는데 verify.sh가 통과하지 못했거나, 동일 증상이
재발했나?"

Options:
- "yes — 가설 단계로 돌아가서 다시 (추천)" — re-enter Step 3 via Step 7
  helper. Construct the prompt: `prompt_text = dispatch_prompt(
  "iter_revisit.md")`, substitute `RUN_ID/REVISIT_TARGET=step3/
  FAILURE_SUMMARY/EXISTING_REPORT`, prepend the result to a fresh
  `dispatch_prompt("hypothesis_step3.md")`, call `dispatch_and_record(
  ..., step="step7.iter{N}.step3", note="revisit: <summary>")`, send
  via Agent.
- "yes — 근본원인을 다시 분석" — re-enter Step 4 via Step 7 helper.
  Same shape, target=step4, prepend to `root_cause_step4.md`.
- "no — 종료" — workflow complete.

Iteration count is a free integer (no upper bound — user terminates).

## Iteration audit invariant (Spike IV §1.1)

Every Step 7 re-entry produces exactly one row in `dispatches.jsonl`
with `step="step7.iter{N}.<target>"` via `dispatch_and_record`. Main
must not call bare `dispatch_prompt` + `record_dispatch` for Step 7 —
the wrapper enforces the audit pairing.
