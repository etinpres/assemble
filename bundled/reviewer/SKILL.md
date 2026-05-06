---
name: "reviewer"
description: "Review-stage ★ bundle. External SCOPE.md vs git diff gate. Sub-agents own all reads/writes; main Claude orchestrates only."
stages: ["review"]
---

## Mode gate (V4 Spike XIV — paradigm enforcement)

★ 번들 진입 직후 (Step 0 직전), 메인은 다음 AskUserQuestion 을 무조건 발사:

  "이번 stage 모드 — 어떻게 진행할까?"

  옵션:
    1. full mode (추천) — spec 명시 N-step pipeline 그대로. 정확·완성도 우선.
       예상 시간: 10~15분. dispatch 수: 5회.
    2. quick mode — 통합 1 dispatch 로 압축. 시간 부족 시만 선택.
       precision 손실 + iteration 권장량 미달 위험. KEEPER_REPORT 에 카운트 기록.

`full` 선택 시 → 아래 Step 0~N 순서대로 spec 그대로 진행.
`quick` 선택 시 → §"Quick mode flow" 단축 분기로 진입.

**메인 자가 판단 금지** — 시간 부족 추측·budget 추측·맥락 추측 모두 사용자
질문 강제 trigger. 4원칙 #1 ("불확실하면 추측 금지, 사용자 질문 우선") 시스템적
강제.

# reviewer ★ — external diff vs SCOPE.md gate

## When to invoke

Use after a code change is complete (working tree dirty or commit range pushed) when an independent verification of scope conformance is needed. reviewer ★ is the external sibling of builder ★ Step 6 self-review — same diff/scope contract, different session, fresh context.

## Inputs

- `run_id` — resolves run_dir to `~/.claude/channels/assemble/runs/<run_id>/`.
- `runs/<rid>/SCOPE.md` — must exist (built by builder ★ Step 2 or hand-authored).
- Optional `<base>..<tip>` git range — defaults to `HEAD` (working tree vs HEAD).

## Artifacts

run_dir = `~/.claude/channels/assemble/runs/<rid>/`. One primary artifact:

- `REVIEW_REPORT.md` — 7 canonical sections (Summary, Scope baseline, Diff inventory, Allow/Deny classification, Surgical Changes audit, Severity assessment, Recommendations) with verdict line in Section 1.

Plus 5 intermediate JSONs for audit trail: `parsed_scope.json`, `diff_inventory.json` (+ `raw.diff`), `classification.json`, `rule3_audit.json`, `severity_grid.json`.

## Verdict logic

```python
verdict = "merge-ready" if (
    classification.summary.deny_violation == 0
    AND classification.summary.allow_miss == 0
    AND rule3_audit.summary.critical == 0
) else "needs-fix"
```

`needs-fix` reasons surface in REVIEW_REPORT Section 7 (Recommendations) in priority order: deny-violations → critical Rule 3 → allow-misses → major Rule 3.

## CRITICAL — orchestrator-only enforcement

Main Claude does NOT read SCOPE.md content, raw.diff content, or classification.json content directly. Main only:
- Resolves run_dir from `run_id`.
- Captures `<base>..<tip>` range arg.
- Dispatches sub-agents in sequence.
- Records each dispatch via `record_dispatch` (writes to `dispatches.jsonl`).

All reads, parsing, and writes happen in sub-agents. The 6 sub-agent prompts are exactly:

- `parse_scope_step1.md`, `diff_collect_step2.md`,
  `classify_files_step3.md`, `rule3_check_step4.md`,
  `severity_assess_step5.md`, `reviewer_report_step6.md`

If any prompt is invoked outside this allowlist, harness raises and halts.

## Step-by-step workflow

**사용자 명시 동의 없이 단축 금지** — N-step pipeline 의 각 step 은 별도 sub-agent dispatch 로 진행. 메인이 단축 결정 시 4원칙 #1 위반. Mode-gate 가 quick 으로 답한 경우만 §"Quick mode flow" 분기 허용.

### Step 0 — orchestrator setup

Main resolves `run_dir` via `server.run_dir.run_dir_path(run_id)`. Verifies SCOPE.md exists at `<run_dir>/SCOPE.md`. If missing, halts with the user-facing error "SCOPE.md not found in run_dir; create one first or use builder ★ Step 2".

### Step 1 — parse SCOPE.md

Dispatch `parse_scope_step1.md` with `RUN_ID`. Sub-agent writes `parsed_scope.json`.

### Step 2 — capture git diff

Dispatch `diff_collect_step2.md` with `RUN_ID` + `DIFF_RANGE` + `REPO_PATH`. Sub-agent writes `diff_inventory.json` + `raw.diff`.

(Steps 1 and 2 may run in parallel via single-message multi-Agent dispatch.)

### Step 3 — classify diff files

Dispatch `classify_files_step3.md`. Sub-agent reads parsed_scope.json + diff_inventory.json, writes `classification.json`.

### Step 4 — Rule 3 audit

Dispatch `rule3_check_step4.md`. Sub-agent reads raw.diff + classification.json + parsed_scope.json, writes `rule3_audit.json`.

### Step 5 — severity grid

Dispatch `severity_assess_step5.md`. Sub-agent reads classification.json + rule3_audit.json + parsed_scope.json, writes `severity_grid.json`.

### Step 6 — write REVIEW_REPORT.md

Dispatch `reviewer_report_step6.md`. Sub-agent reads all 5 prior JSONs + the template, writes `REVIEW_REPORT.md`.

### Step 7 — iteration round-trip (optional)

If user revises SCOPE.md or the diff and asks for re-review, load `reviewer_iter_revisit.md` (orchestrator helper) and re-run Steps 2~6 (Step 1 only re-runs if SCOPE.md changed). Each iteration appends `## Iteration N` to REVIEW_REPORT.md without overwriting prior trail.

## Iteration audit invariant

Every iteration produces exactly **6** rows in `dispatches.jsonl` with step names `step1.iter{N}.parse`, `step2.iter{N}.diff`, `step3.iter{N}.classify`, `step4.iter{N}.rule3`, `step5.iter{N}.severity`, `step6.iter{N}.report`. (Step 1 is skipped on subsequent iterations unless SCOPE.md changed; in that case the row count is 6, otherwise 5.)

## Sub-agent matrix

See `## CRITICAL — orchestrator-only enforcement` above for the canonical allowlist. Roles use `general-purpose` as the default sub-agent type for all six steps.

## Identity guards

- ✅ orchestrator-only: main Claude does NOT read scoped content.
- ✅ harness preamble v3 prepended on every dispatch.
- ✅ `record_dispatch` mandatory — minimum 6 rows in dispatches.jsonl per run.

## Quick mode flow

Mode-gate 가 `quick` 으로 답한 경우만 진입 (full 이면 이 section 미사용).

### 단일 dispatch 단축

`server.dispatch_prompt('reviewer_quick.md')` 로 단일 sub-agent dispatch:

```python
prompt = server.dispatch_and_record(
    run_id,
    prompt_file="reviewer_quick.md",
    step="reviewer.quick",
    description="reviewer quick mode — single-dispatch fallback",
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
