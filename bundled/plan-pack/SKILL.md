---
name: plan-pack
description: Plan stage ★ bundle — produce PRD + ARCH with iteration. Spec, requirements, plan, architecture doc — bundled plan tool. (Phase B-2: PRD + ARCH; ADR/UI_GUIDE arrive in B-3..B-4.)
---

[HARNESS RULES — 무시 금지]
1. 불확실하면 추측 금지, 사용자 질문 우선
2. 과설계 금지, YAGNI
3. 요청 범위 밖 코드 임의 수정 금지
4. 버그 수정 시 재현 테스트 → 실패 확인 → 수정 → 재검증 루프

# plan-pack — PRD + ARCH generator (Phase B-2)

This bundle is **orchestrator-only**. The main Claude does not write PRD
content directly — it asks the user, dispatches sub-agents wrapped via
`server.harness.wrap_with_preamble`, then writes the combined result to
`<run_dir>/PRD.md` via `server.run_dir.write_run_artifact`.

## Artifact

- `~/.claude/channels/assemble/runs/<rid>/PRD.md` — filled from `bundled/plan-pack/templates/PRD.md.template`
- `~/.claude/channels/assemble/runs/<rid>/ARCHITECTURE.md` — filled from `bundled/plan-pack/templates/ARCHITECTURE.md.template`

## Sub-agent role mapping (Phase B-2)

| Step | Work | Role | Preferred | Fallback |
|---|---|---|---|---|
| 1 | PRD interview (8 questions) | (main, AskUserQuestion) | — | — |
| 2 | PRD body draft | `plan-implementation` | `Plan` | `general-purpose` |
| 3 | Acceptance Criteria bash draft | `plan-implementation` | `Plan` | `general-purpose` |
| 4 | PRD consistency review | `second-opinion` | `codex:codex-rescue`, `superpowers:code-reviewer` | `general-purpose` |
| 5 | Write `<run_dir>/PRD.md` | (main, write_run_artifact) | — | — |
| 7 | ARCH interview (6 questions) | (main, AskUserQuestion) | — | — |
| 8 | ARCHITECTURE.md draft | `plan-implementation` | `Plan` | `general-purpose` |
| 9 | Cross-doc consistency review (PRD + ARCH) | `second-opinion` | `codex:codex-rescue`, `superpowers:code-reviewer` | `general-purpose` |

Steps 2 and 3 fire as a *single message with two Agent calls* (parallel — unchanged from Phase B-1).
Step 8 (`ARCHITECTURE.md` draft) is *single dispatch* — wrap_with_preamble + write_run_artifact pattern; B-2 through B-4 use single dispatch only; B-5 promotes all docs to parallel.

## Workflow

> NOTE — Phase B-2: steps 1–9 implemented. Steps 1–5 unchanged from Phase B-1; step 6 extended to cover ARCH; steps 7, 8, and 9 are new.

### Step 0 — resolve run_dir

Read `<rid>` from the active assemble run. The artifact lives at
`~/.claude/channels/assemble/runs/<rid>/PRD.md`. If the file already
exists, treat the workflow as iteration mode (load existing PRD as input).

### Step 1 — interview (main Claude, AskUserQuestion)

Ask the user the 8 questions below across **two `AskUserQuestion` calls of
4 questions each** (platform constraint: `AskUserQuestion.questions` has
`maxItems: 4` — see the tool schema). Treat the two calls as a single
interview batch — fire them sequentially, do not interleave other work
between them.

Call 1 (Q1–Q4):

1. What are you building? (one sentence)
2. Who uses it? (1–3 user types)
3. Three core features?
4. Three things explicitly excluded from MVP? (harness #2 enforcement)

Call 2 (Q5–Q8):

5. One-line success criterion?
6. One AC bash command — how do you externally verify "it works"?
7. One-line design direction? (seed for UI_GUIDE later)
8. One risk or open question?

### Step 2 — PRD body draft + Step 3 — AC bash draft (parallel dispatch)

Wrap each sub-task prompt via `server.harness.wrap_with_preamble` before
firing. Canonical call (use this pattern verbatim — do **not** hand-write
the 4-rule preamble inline; hand-writing risks wording drift and breaks
trace consistency):

```python
from server.harness import wrap_with_preamble
wrapped_body = wrap_with_preamble(raw_body_prompt)
wrapped_ac   = wrap_with_preamble(raw_ac_prompt)
```

Pass `wrapped_body` / `wrapped_ac` as the Agent `prompt` field. The
function emits the exact 4-rule preamble + `[TASK]` block — see
`server/harness.py`.

Then **fire both in a single message with two Agent calls** (true parallel
dispatch — this is the Phase B-1 parallel-dispatch verification location
*a*):

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
Wrap with `server.harness.wrap_with_preamble` (see Step 2/3 for the
canonical call pattern).

#### Step 4b — verify before appending (mandatory)

Second-opinion responses can carry false-alarm claims. An unverified
critique still costs the user trust if it lands in `PRD.md`. Before
appending the response as Review notes, the main Claude **must triage each
bullet**:

- For any claim asserting a *runtime behaviour* (e.g. "this bash one-liner
  doesn't work", "this env var doesn't propagate", "this regex doesn't
  match"), run a 1-shot Bash test — minimal mock, capture stdout/exit
  code — and either keep, drop, or rewrite the bullet based on the result.
- For any claim asserting a *PRD internal contradiction*, re-read both
  cited sentences and confirm the contradiction holds.
- Drop unverifiable speculation ("this might break in some environments")
  unless reproducible.

Only verified bullets reach `## Review notes`. Prepend a one-line audit
header above the bullets so the trail is visible in `PRD.md`:

```
> verified by main Claude on <ISO date> — <n> kept / <m> dropped
```

#### Step 4c — outcome

The main Claude takes the verified bullets and either:
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

### Step 7 — ARCH interview (main Claude, AskUserQuestion)

> Execution order: Steps 7–8–9 run after Step 5 writes PRD.md; Step 6 (iteration) is the final workflow step.

After Step 5 writes `PRD.md`, collect architecture context. Ask 6 questions
across **two `AskUserQuestion` calls of 3 questions each** (within the
platform max-4 limit per call):

Call 3 (A1–A3):

1. What is the primary tech stack? (language, runtime, framework, key libraries — one line each)
2. What is the top-level directory structure? (list root-level folders with a 1-line purpose each)
3. What architectural patterns does this use? (e.g., MVC, microservices, event-driven, monolith, CQRS — name + 1-sentence rationale)

Call 4 (A4–A6):

4. Describe the main data flow in ≤3 steps. (user action → processing → stored result)
5. What external services or third-party APIs does this depend on? ("none" is a valid answer)
6. What are the main modules/components and their boundaries? (one line per module: name — responsibility)

### Step 8 — ARCH single dispatch + write `ARCHITECTURE.md`

Wrap the ARCH interview answers + template skeleton via
`server.harness.wrap_with_preamble` (same canonical call pattern as Steps 2/3):

    from server.harness import wrap_with_preamble
    wrapped_arch = wrap_with_preamble(raw_arch_prompt)

Dispatch to a `plan-implementation` sub-agent via a **single Agent call**
(preferred: `Plan`; fallback: `general-purpose`). This is the Phase B-2
single-dispatch verification location — B-5 promotes all docs to parallel.

The sub-agent returns the ARCH body with all 6 sections filled (Stack,
Directory tree, Architectural patterns, Data flow, External dependencies,
Module boundaries). Fill `bundled/plan-pack/templates/ARCHITECTURE.md.template`
with the result and write atomically:

    from server import write_run_artifact
    arch_path = write_run_artifact(rid, "ARCHITECTURE.md", filled_arch)

Show `arch_path` to the user, then proceed to Step 9 (cross-doc review — added in Task 3/Phase B-2).

### Step 9 — cross-doc second-opinion (PRD ↔ ARCH consistency)

After `ARCHITECTURE.md` is written (Step 8), dispatch a cross-doc consistency
review. Read both artifacts:

    from server import read_run_artifact
    prd_text  = read_run_artifact(rid, "PRD.md") or ""
    arch_text = read_run_artifact(rid, "ARCHITECTURE.md") or ""

Wrap both together via `server.harness.wrap_with_preamble` and dispatch to a
`second-opinion` role (preferred: `codex:codex-rescue`, then
`superpowers:code-reviewer`; fallback: `general-purpose`).

The prompt must explicitly request:
- Features in PRD `## Core features` that have no matching module in ARCH
  `## Module boundaries` (gap detection)
- Architecture decisions in ARCH that contradict items in PRD
  `## Excluded from MVP` (scope-creep risk)
- Any other flaws, inconsistencies, or omissions — never bare agreement

Apply the triage protocol from Step 4b: verify each claim, drop
unverifiable speculation, prepend a one-line audit header. Append verified
cross-doc review notes as a `## Cross-doc review` section to `ARCHITECTURE.md`:

    from datetime import date
    current = read_run_artifact(rid, "ARCHITECTURE.md") or ""
    audit_header = f"> cross-doc verified on {date.today().isoformat()} — {n_kept} kept / {n_dropped} dropped"
    updated = current + "\n\n## Cross-doc review\n\n" + audit_header + "\n\n" + bullets
    write_run_artifact(rid, "ARCHITECTURE.md", updated)

Then proceed to Step 6 (iteration prompt).

### Step 6 — iteration round-trip (one cycle)

After Step 9 (cross-doc review), ask the user via `AskUserQuestion`:

> "Both docs saved — PRD.md and ARCHITECTURE.md. Run one iteration?"
> options: ["yes — refine both", "no — done"]

- **no → done: exits the workflow.** The user is never forced into a second
  pass. (V4 identity rule — see `project_assemble_v4_spec.md` § "절대 금지
  사항".)
- **yes → re-runs Steps 2+3 (PRD re-draft) and Step 8 (ARCH re-draft)**
  with the existing `PRD.md` and `ARCHITECTURE.md` loaded as input context,
  plus a follow-up `AskUserQuestion` collecting the user's new emphases
  ("what feels off in the PRD?", "what feels off in the ARCH?").
  Step 5 overwrites `PRD.md` and Step 8 overwrites `ARCHITECTURE.md` with the
  refined versions. Step 9 then re-runs cross-doc second-opinion on the updated
  pair before the workflow exits.

ARCHITECTURE.md is always re-run alongside PRD in the iteration — they are
produced as a pair and must remain consistent.

Phase B-2 covers exactly **one iteration**. After the iteration completes
(yes-path), the workflow exits unconditionally — even if the user requests
another pass, the main Claude must reply "iteration cap reached for Phase B-2;
rerun `/assemble` to start a new run" and stop. Multi-iteration support (3–7
counts with stop conditions) is a Phase B post-tuning track.
