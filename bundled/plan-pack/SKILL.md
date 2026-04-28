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
`server.harness.wrap_with_preamble`, then writes the combined result to
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

> NOTE — steps 1–6 implemented (Phase B-1 complete).

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
  met. **Return only the raw command — no markdown fences, no `bash`
  language tag, no surrounding prose.** Step 5 will substitute the result
  into the template's pre-existing fenced bash block.

The main Claude waits for both calls to return, then proceeds to Step 5.

### Step 4 — consistency review (second-opinion)

Take the combined PRD body + AC bash from Step 2/3 and dispatch it as a
*challenge* prompt to a `second-opinion` role (preferred:
`codex:codex-rescue`, then `superpowers:code-reviewer`; fallback:
`general-purpose` with the bare task prompt. (V4 spec memory describes a
future `roles.json` carrying `fallback_context` per role; until that lands
in a later phase, dispatches use the prompt as-is.)

The dispatched prompt explicitly asks for *flaws, rebuttals, missing
constraints, and tradeoffs not yet acknowledged* — never bare agreement.
Wrap with `server.harness.wrap_with_preamble`.

The main Claude takes the response and either:
- Appends a `## Review notes` section to the PRD body, **or**
- Absorbs the critique by re-running Steps 2/3 in iteration mode.

Phase B-1 takes the simpler path: append `## Review notes`. Iteration-mode
absorption arrives in Step 6 (Task 7).

### Step 5 — combine + write (main Claude)

If the AC bash sub-agent returned a fenced block (despite Sub-task B's
instruction), strip leading/trailing triple-backtick fences and any
`bash` language tag before substituting `{{AC_BASH}}`. Then fill
`bundled/plan-pack/templates/PRD.md.template` with the sub-agent output
and call:

```python
from server import write_run_artifact
write_run_artifact(rid, "PRD.md", filled)
```

The function returns the absolute path; show that path to the user.

### Step 6 — iteration round-trip (one cycle)

After writing PRD.md, ask the user via `AskUserQuestion`:

> "PRD draft saved to `<path>`. Run one iteration?"
> options: ["yes — refine", "no — done"]

- **no exits the workflow.** The user is never forced into a second
  pass. (V4 identity rule — see `project_assemble_v4_spec.md` § "절대 금지
  사항".)
- **yes → re-runs Steps 2–4** with the existing `PRD.md` loaded as input
  context, plus a follow-up `AskUserQuestion` collecting the user's new
  emphases ("what feels off?", "what to expand?"). Step 5 overwrites
  PRD.md with the refined version.

Phase B-1 covers exactly **one iteration**. After the iteration completes
(yes-path), the workflow exits unconditionally — even if the user wants
another pass, the main Claude must reply "iteration cap reached for
Phase B-1; rerun `/assemble` to start a new run" and stop. Multi-iteration
support with stop conditions is a Phase B post-tuning track.
