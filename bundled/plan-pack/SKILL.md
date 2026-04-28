---
name: plan-pack
description: Plan stage ★ bundle — produce a PRD with iteration. Spec, requirements, plan, design doc — bundled plan tool. (Phase B-1: PRD only; ARCH/ADR/UI_GUIDE land in Phase B-2..B-4.)
---

[HARNESS RULES — 무시 금지]
1. 불확실하면 추측 금지, 사용자 질문 우선
2. 과설계 금지, YAGNI
3. 요청 범위 밖 코드 임의 수정 금지
4. 버그 수정 시 재현 테스트 → 실패 확인 → 수정 → 재검증 루프

# plan-pack — PRD generator (Phase B-1)

This bundle is **orchestrator-only**. The main Claude does not write PRD
content directly — it asks the user, dispatches sub-agents wrapped via
`server.harness.wrap_with_preamble`, then writes the merged result to
`<run_dir>/PRD.md` via `server.run_dir.write_run_artifact`.

## Artifact

`~/.claude/channels/assemble/runs/<rid>/PRD.md` — filled from
`bundled/plan-pack/templates/PRD.md.template`.

## Sub-agent role mapping (Phase B-1)

| Step | Work | Role | Preferred | Fallback |
|---|---|---|---|---|
| 1 | User interview (8 questions) | (main, AskUserQuestion) | — | — |
| 2 | PRD body draft | `plan-implementation` | `Plan` | `general-purpose` |
| 3 | Acceptance Criteria bash draft | `plan-implementation` | `Plan` | `general-purpose` |
| 4 | Consistency review | `second-opinion` | `codex:codex-rescue`, `superpowers:code-reviewer` | `general-purpose` |
| 5 | Merge + write `<run_dir>/PRD.md` | `text-summarize` | `gemma-worker` | `general-purpose` |

Steps 2 and 3 fire as a *single message with two Agent calls* — this is the
parallel-dispatch verification location.

## Workflow

(Workflow steps land in Tasks 4–7 of the Phase B-1 plan.)
