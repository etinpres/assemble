---
name: plan-pack
description: Plan stage ★ bundle — produce a PRD with iteration. Spec, requirements, plan, design doc — bundled plan tool. (Phase B-1: PRD only; ARCH/ADR/UI_GUIDE arrive in Phase B-2..B-4.)
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
| 5 | Combine + write `<run_dir>/PRD.md` | `text-summarize` | `gemma-worker` | `general-purpose` |

Steps 2 and 3 fire as a *single message with two Agent calls* — this is the
parallel-dispatch verification location.

## Workflow

> NOTE — Phase B-1 implements **steps 1, 2, 3, 5 only**. Steps 4
> (consistency review) and 6 (iteration) arrive in Phase B-1 Tasks 6 and
> 7 of `docs/plans/2026-04-28-v4-phase-b-1.md`.

### Step 0 — resolve run_dir

Read `<rid>` from the active assemble run. The artifact lives at
`~/.claude/channels/assemble/runs/<rid>/PRD.md`. If the file already
exists, treat the workflow as iteration mode (load existing PRD as input).

### Step 1 — interview (main Claude, AskUserQuestion)

Ask the user 8 questions in a single batched `AskUserQuestion`:

1. What are you building? (one sentence)
2. Who uses it? (1–3 user types)
3. Three core features?
4. Three things explicitly excluded from MVP? (harness #2 enforcement)
5. One-line success criterion?
6. One AC bash command — how do you externally verify "it works"?
7. One-line design direction? (seed for UI_GUIDE later)
8. One risk or open question?

### Step 2 — PRD body draft + Step 3 — AC bash draft (parallel dispatch)

Wrap the interview answers + template skeleton via
`server.harness.wrap_with_preamble` once for the body sub-task and once for
the AC bash sub-task. Then **fire both in a single message with two Agent
calls** (true parallel dispatch — this is the Phase B-1 parallel-dispatch
verification location *a*):

- Sub-task A — PRD body. Role `plan-implementation` (preferred `Plan`,
  fallback `general-purpose`). Returns Goal / Users / Core features /
  Excluded from MVP / Design direction / Risks.
- Sub-task B — AC bash. Role `plan-implementation` (preferred `Plan`,
  fallback `general-purpose`). Given the success criterion (interview Q5)
  and the externally-verifiable command request (Q6), returns *one
  executable bash one-liner* that exits 0 iff the success criterion is
  met. No prose — just the command.

The main Claude waits for both calls to return, then proceeds to Step 5.

### Step 5 — combine + write (main Claude)

Fill `bundled/plan-pack/templates/PRD.md.template` with the sub-agent
output, then call:

```python
from server import write_run_artifact
write_run_artifact(rid, "PRD.md", filled)
```

The function returns the absolute path; show that path to the user.
