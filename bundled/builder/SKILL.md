---
name: builder
description: "Execute stage ★ bundle — TDD-first red→green pipeline (test_first.sh → impl → verify.sh). SCOPE.md contract + IMPL_REPORT.md audit trail. (V4 Spike V: parallel to debugger ★, sub-agent path-only return contract.)"
stages: [execute]
---

[HARNESS RULES — 무시 금지]
1. 불확실하면 추측 금지, 사용자 질문 우선
2. 과설계 금지, YAGNI
3. 요청 범위 밖 코드 임의 수정 금지
4. 버그 수정 시 재현 테스트 → 실패 확인 → 수정 → 재검증 루프
5. 사용자에게 표시되는 한국어 라벨·옵션은 자연스러운 한국어로 정제. 영문 기술용어 한글화 시 정확한 외래어 표기 사용 (architecture→아키텍처, family→패밀리, top-level→최상위, recommended→추천, directory→디렉토리). 자작 변형 금지.
6. task scope은 seed이지 contract가 아니다 — IMPL_REPORT.md 7섹션 모두 작성
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
3. NEVER attempt to write the artifact yourself.

If retry is chosen, re-dispatch the same sub-agent with the failure context
(`previous attempt failed: <reason>`) appended to the original prompt.

**Anti-bypass (Spike II F9 + F11 + Spike IV §1.3):**

- `~/.claude/settings.json` 편집해서 `ASSEMBLE_GUARD` 환경 변수 무력화 시도 금지.
  hook 자체를 비활성화/우회 시도는 사용자 confirm 이 떠도 거절.
- hook 이 차단하면 즉시 `AskUserQuestion` 으로 사용자 결정 위임 (retry / abort / report).
- sub-agent dispatch 는 두 디렉토리의 *7개 파일* 에 한정 (builder ★ allowlist):
  - `bundled/builder/prompts/subagent/`: `scope_step2.md`, `test_step3.md`, `impl_step4.md`,
  `verify_step5.md`, `review_step6.md`, `report_step7.md` (6 files)
  - `bundled/builder/prompts/orchestrator/`: `builder_iter_revisit.md` (1 file — main constructs per-step revisit prompts before re-dispatching Step 2 or Step 4)
- orchestrator 메타데이터 (`dispatches.jsonl`) 는 sub-agent 에 위임 금지 — `server.dispatch_and_record` 같은 server 함수 사용.

## Korean label policy (Spike II F4)

When `ASSEMBLE_LOCALE=ko` (or user message language is Korean), AskUserQuestion
options that historically carry English `(Recommended)` suffix MUST use the
unified Korean form `(추천)`. Do not improvise alternatives.

# builder ★ — TDD-first implementation pipeline

Produces four artifacts under `runs/<rid>/`. Main Claude is orchestrator-only;
sub-agents own all writes via `WROTE: <path>` stdout.

## Artifacts

run_dir = `~/.claude/channels/assemble/runs/<rid>/`. Four artifacts:

- `SCOPE.md` — allow-list + deny-list + completion criterion + task breakdown (Step 2).
- `test_first.sh` — exits non-zero before implementation (red). Step 3.
- `verify.sh` — exits 0 after implementation (green). Step 5.
- `IMPL_REPORT.md` — 7 sections filled across Steps 2–7. `status: complete` when done.

`test_first.sh` and `verify.sh` are the cross-cutting AC=bash pattern (V4 spec
§ "Cross-cutting 강화 흡수 후보" B). The user can run them interactively to
confirm the red→green cycle without LLM mediation.

## Sub-agent role mapping

All dispatches use `general-purpose` (preferred + fallback). Role varies per step.

| Step | Role persona | Prompt file |
|---|---|---|
| 2 | `plan-implementation` | `prompts/subagent/scope_step2.md` |
| 3 | (general-purpose) | `prompts/subagent/test_step3.md` |
| 4 | (general-purpose) | `prompts/subagent/impl_step4.md` |
| 5 | (general-purpose) | `prompts/subagent/verify_step5.md` |
| 6 | `second-opinion` | `prompts/subagent/review_step6.md` |
| 7 | `text-summarize` | `prompts/subagent/report_step7.md` |
| 8 | orchestrator helper | `prompts/orchestrator/builder_iter_revisit.md` |

Steps 0/1 are main-side IO + `AskUserQuestion`. Step 8 is iteration re-entry —
the substituted prompt is prepended to a re-dispatch of Step 2 or Step 4.

## Workflow execution sequence

```
0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 (loop back to 2 or 4)
```

Linear pipeline + 1 backtrack point. Steps fire in numeric order.

## Steps

### Step 0 — resolve run_dir

Read `<rid>` from the active assemble run. Artifact paths are
`~/.claude/channels/assemble/runs/<rid>/{SCOPE.md,test_first.sh,verify.sh,IMPL_REPORT.md}`.
If `IMPL_REPORT.md` already exists with `status: complete`, treat as iteration
mode (Step 8 re-entry with new task).

### Step dispatch contract (Steps 2/3/4/5/6/7)

For each dispatch step:

1. `prompt_text = server.dispatch_prompt("<file>.md")` — loads + wraps with harness preamble.
2. Caller substitutes per-step `{{KEY}}` tokens (Inputs section).
3. `server.dispatch_and_record(run_id, prompt_file="<file>.md", step="step{N}",
   subagent_type="general-purpose", description="…")` — audit row.
4. Send via `Agent` tool with `subagent_type="general-purpose"` and substituted prompt.
5. Parse `WROTE: <path>` from stdout. On `ERROR:` or no `WROTE:`,
   surface to user via `AskUserQuestion` (retry / abort / report).

### Step 1 — task interview (main)

Two `AskUserQuestion` calls:

**Q1** (single):
"구현할 작업을 한 줄로 요약해 줘. (예: 'POST /api/items 엔드포인트 추가', 'Flutter 홈 위젯 리팩토링')"

**Q2** (multi, 3 sub-questions):
- "변경 대상 파일·모듈을 알고 있으면 알려줘 (모르면 '모름')"
- "테스트 실행 커맨드가 있어? (예: pytest tests/, flutter test, bash smoke.sh — 없으면 '없음')"
- "완료 기준 (AC)을 bash 커맨드로 표현할 수 있어? (예: curl ... | grep -q ok — 없으면 '모름')"

Outputs `TASK_SUMMARY`, `KNOWN_FILES`, `TEST_CMD`, `AC_CMD` → passed to Step 2.

### Step 2 — SCOPE.md + IMPL_REPORT.md skeleton (sub-agent)

`prompt_file="scope_step2.md"`. Inputs: `RUN_ID`, `TASK_SUMMARY`, `KNOWN_FILES`,
`TEST_CMD`, `AC_CMD`. Sub-agent writes SCOPE.md + IMPL_REPORT.md skeleton.

### Step 3 — test_first.sh red phase (sub-agent)

`prompt_file="test_step3.md"`. Inputs: `RUN_ID`, `SCOPE_CONTENT`.
Sub-agent writes `test_first.sh`, runs it, confirms non-zero exit, fills
`## Test (red)`.

If sub-agent ERROR-exits with "test already passes", `AskUserQuestion`:
"테스트가 이미 통과해. test_first.sh를 수정할래, 아니면 task가 이미 완료된 건지 확인할래?"

### Step 4 — implementation (sub-agent)

`prompt_file="impl_step4.md"`. Inputs: `RUN_ID`, `SCOPE_CONTENT`, `EXISTING_REPORT`.
Sub-agent edits source files (Edit/Write) within SCOPE.md allow-list only.
Any edit outside allow-list triggers `ERROR: scope creep — patch touches <file>
not in allow-list`.

Does NOT run tests (Step 5 owns verification).

### Step 5 — verify.sh green phase + IMPL_REPORT draft (sub-agent)

`prompt_file="verify_step5.md"`. Inputs: `RUN_ID`, `EXISTING_REPORT`.
Sub-agent writes `verify.sh` (behavioral preferred), runs it, confirms exit 0,
fills `## Verify (green)`.

If sub-agent ERROR-exits with "verifier failed after implementation", `AskUserQuestion`:
"verify.sh가 실패했어. Step 4 재시도 / abort / report?"

### Step 6 — self-review diff vs SCOPE (sub-agent)

`prompt_file="review_step6.md"`. Inputs: `RUN_ID`, `SCOPE_CONTENT`, `EXISTING_REPORT`.
Sub-agent runs `git diff`, compares against SCOPE allow/deny lists, fills
`## Self-review` (scope deviation count + recommendation).

### Step 7 — commit message + IMPL_REPORT finish (sub-agent)

`prompt_file="report_step7.md"`. Inputs: `RUN_ID`.
Sub-agent validates no `<TBD:` remain, adds `## Commit message` +
`## TL;DR`, flips `status: complete`.

If ERROR-exits with "IMPL_REPORT has unfilled sections", re-dispatch the
gap-source step (section name in error indicates which).

### Step 8 — iteration round-trip

After Step 7 success, `AskUserQuestion`:

"verify.sh가 통과했어. 추가 작업이 남아 있어?"

Options:
- `"yes — 새 task로 Step 2부터 다시 (추천)"` → SCOPE.md 초기화, Step 2 재진입
- `"yes — 같은 SCOPE에서 구현만 다시"` → Step 4 재진입 (SCOPE.md 유지)
- `"no — 완료"` → workflow 종료

Iteration audit: `dispatch_and_record(..., step="step8.iter{N}.step2")` or
`step8.iter{N}.step4`.

## TDD tier rules

| Situation | test_first.sh content |
|---|---|
| Unit test framework available | `pytest tests/test_foo.py` — exits non-zero (test not yet written or failing) |
| No unit test but runnable entry point | AC=bash smoke — exits non-zero |
| Neither available | SCOPE.md `## Completion criterion` + grep/stat check |

All tiers use the same shell contract. Distinction documented in SCOPE.md, not in SKILL.md branching.

## Iteration audit invariant (Spike V §1.1)

Every Step 8 re-entry produces exactly one row in `dispatches.jsonl` with
`step="step8.iter{N}.<target>"` via `dispatch_and_record`. Main must not
call bare `dispatch_prompt` + `record_dispatch` for Step 8.
