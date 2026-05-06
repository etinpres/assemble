---
name: "verifier"
description: "Verify-stage ★ bundle. Executes parsed_scope.json completion bash and emits deterministic exit-code verdict. Sub-agents own all reads/writes/Bash; main Claude orchestrates only."
stages: ["verify"]
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

# verifier ★ — completion criterion runner

## When to invoke

Use after `parsed_scope.json` exists in the run_dir (built by reviewer ★ Step 1 or builder ★ Step 2 or hand-authored after running `server.scope_parser.parse_scope_md`) when an independent, deterministic verdict on the SCOPE author's completion criterion is needed. verifier ★ is the orthogonal sibling of reviewer ★ — same `parsed_scope.json` input contract, but executes the bash one-liner and emits exit-code-driven pass/fail rather than diff/scope auditing.

## Inputs

- `run_id` — resolves run_dir to `~/.claude/channels/assemble/runs/<run_id>/`.
- `<run_dir>/parsed_scope.json` — must exist with non-empty `completion` field.
- (No `<base>..<tip>` git range — verifier is purely a completion-criterion runner.)

## Artifacts

run_dir = `~/.claude/channels/assemble/runs/<rid>/`. One primary artifact:

- `VERIFY_REPORT.md` — 7 canonical sections (Summary, Completion command, Execution result, Stdout sample, Stderr sample, Verdict reasoning, Recommendations) with verdict line in Section 1.

Plus 3 intermediate JSONs for audit trail: `extracted_completion.json`, `execution_result.json`, `verify_result.json`.

## Verdict logic (deterministic)

```python
verdict = "pass" if (
    execution_result.exit_code == 0
    AND not execution_result.skipped
    AND not execution_result.timed_out
) else "fail"
```

Reason text:
- `pass` → "completion command exited 0"
- `skipped` → "skipped: <comma-joined skip_reasons>"
- `timed_out` → "timed out (30s budget)"
- `exit_code != 0` → "exited <N>"

Truncated stdout/stderr does NOT auto-fail — `truncated: true` is metadata for VERIFY_REPORT, not a verdict input.

## CRITICAL — orchestrator-only enforcement

Main Claude does NOT read `parsed_scope.json` content, `execution_result.json` content, or call Bash directly. Main only:
- Resolves run_dir from `run_id`.
- Verifies `parsed_scope.json` exists + has non-empty `completion` field via `server.run_dir.read_run_artifact` if needed (sanity check ONLY — full validation lives in Step 1).
- Dispatches sub-agents in sequence (Step 1 → Step 2 → Step 3 → Step 4).
- Records each dispatch via `server.harness.record_dispatch` (writes to `dispatches.jsonl`).

All reads, parsing, execution, classification, and report rendering happen in sub-agents. The 4 sub-agent prompts are exactly:

- `verifier_extract_step1.md` — parsed_scope.json → extracted_completion.json
- `verifier_execute_step2.md` — bash execution + capture (Bash tool GRANTED for this step ONLY)
- `verifier_classify_step3.md` — execution_result.json → verify_result.json (deterministic verdict)
- `verifier_report_step4.md` — VERIFY_REPORT.md render from 3 prior JSONs + template

If any prompt is invoked outside this allowlist, harness raises and halts. See `server.harness.ALLOWED_PROMPT_FILES`.

## Step-by-step workflow

**사용자 명시 동의 없이 단축 금지** — N-step pipeline 의 각 step 은 별도 sub-agent dispatch 로 진행. 메인이 단축 결정 시 4원칙 #1 위반. Mode-gate 가 quick 으로 답한 경우만 §"Quick mode flow" 분기 허용.

### Step 0 — orchestrator setup

Main resolves `run_dir` via `server.run_dir.run_dir_path(run_id)`. Verifies `parsed_scope.json` exists at `<run_dir>/parsed_scope.json`. If missing, halts with the user-facing error "parsed_scope.json not found in run_dir; run reviewer ★ Step 1 first or hand-author after `server.scope_parser.parse_scope_md`".

### Step 1 — extract completion bash

Dispatch `verifier_extract_step1.md` with `RUN_ID`. Sub-agent reads parsed_scope.json, validates completion field (non-empty after strip, len ≤ 500, single line, plus input-robustness errors for missing/malformed JSON / non-string completion), writes `extracted_completion.json`.

### Step 2 — execute completion bash

Dispatch `verifier_execute_step2.md` with `RUN_ID`. **Bash tool access GRANTED for this step ONLY** (Steps 1, 3, 4 do NOT receive Bash). Sub-agent:
- skips execution if `extracted_completion.json["errors"]` is non-empty (records `skipped: true` + `skip_reasons` array + `skip_reason` scalar)
- otherwise runs `subprocess.run(["bash", "-c", completion], timeout=30, capture_output=True, text=True)` with 100KB stdout/stderr cap each
- writes `execution_result.json` (skipped/skip_reasons/skip_reason/exit_code/stdout/stderr/duration_ms/timed_out/truncated)

See `SECURITY.md` for the full threat model + mitigation surface.

### Step 3 — classify execution result

Dispatch `verifier_classify_step3.md` with `RUN_ID`. Sub-agent reads execution_result.json, applies the deterministic verdict rule above (NO LLM judgment), writes `verify_result.json` (verdict/reason/exit_code/duration_ms/truncated/timed_out/skipped).

### Step 4 — render VERIFY_REPORT.md

Dispatch `verifier_report_step4.md` with `RUN_ID`. Sub-agent reads all 3 prior JSONs + the template at `bundled/verifier/templates/VERIFY_REPORT.md.template`, substitutes 14 placeholders via `str.replace`, writes `VERIFY_REPORT.md` with all 7 canonical sections.

### Step 5 — iteration round-trip (optional)

If user revises `parsed_scope.json` (e.g. amends completion command) and asks for re-verification, load `verifier_iter_revisit.md` (orchestrator helper) and re-run Steps 2~4 (Step 1 only re-runs if parsed_scope changed). Each iteration appends `## Iteration N` to VERIFY_REPORT.md without overwriting prior trail.

## Iteration audit invariant

Every iteration produces exactly **4** rows in `dispatches.jsonl` with step names `step1.iter{N}.extract`, `step2.iter{N}.execute`, `step3.iter{N}.classify`, `step4.iter{N}.report`. Step 1 is skipped on subsequent iterations unless parsed_scope.json changed; in that case the row count is 4, otherwise 3.

## Sub-agent matrix

See `## CRITICAL — orchestrator-only enforcement` above for the canonical 4-file allowlist. Roles use `general-purpose` as the default sub-agent type for all 4 steps.

| Step | Prompt file | Sub-agent type | Tools granted |
|---|---|---|---|
| 1 | `verifier_extract_step1.md` | `general-purpose` | Read, Write |
| 2 | `verifier_execute_step2.md` | `general-purpose` | Read, Write, **Bash** |
| 3 | `verifier_classify_step3.md` | `general-purpose` | Read, Write |
| 4 | `verifier_report_step4.md` | `general-purpose` | Read, Write |

Iteration helper `verifier_iter_revisit.md` is loaded by main directly (NOT in subagent allowlist).

## Security

See `SECURITY.md` for threat model + mitigation surface. Key mitigations:
- Length cap 500 (Step 1)
- Timeout 30s (Step 2)
- Output cap 100KB stdout/stderr each (Step 2)
- Bash scoped to Step 2 only
- Skip-if-errors (Step 2 honors Step 1's error labels)

The `Bash tool access GRANTED` substring marker in `verifier_execute_step2.md` is the canonical grep target for security audits.

## Identity guards

- ✅ orchestrator-only: main Claude does NOT read parsed_scope content, execution result content, or call Bash directly during the dispatch chain.
- ✅ harness preamble v3 prepended on every dispatch (canonical sha `858e9ff1cdc05ca73bb4009aab3acfc841169b30873d2fb00f2dfd546b86e159`).
- ✅ `record_dispatch` mandatory — minimum 4 rows in dispatches.jsonl per run.
- ✅ Bash tool scoped to Step 2 sub-agent ONLY (allowlist + harness preamble v3).
- ✅ Deterministic verdict — no LLM-judged pass/fail.

## Quick mode flow

Mode-gate 가 `quick` 으로 답한 경우만 진입 (full 이면 이 section 미사용).

### 단일 dispatch 단축

`server.dispatch_prompt('verifier_quick.md')` 로 단일 sub-agent dispatch:

```python
prompt = server.dispatch_and_record(
    run_id,
    prompt_file="verifier_quick.md",
    step="verifier.quick",
    description="verifier quick mode — single-dispatch fallback",
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
