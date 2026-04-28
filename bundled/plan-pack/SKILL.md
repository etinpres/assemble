---
name: plan-pack
description: Plan stage ★ bundle — produce PRD + ARCH + ADR with iteration. Spec, requirements, plan, architecture doc, decision record — bundled plan tool. (Phase B-3: PRD + ARCH + ADR; UI_GUIDE arrives in B-4.)
---

[HARNESS RULES — 무시 금지]
1. 불확실하면 추측 금지, 사용자 질문 우선
2. 과설계 금지, YAGNI
3. 요청 범위 밖 코드 임의 수정 금지
4. 버그 수정 시 재현 테스트 → 실패 확인 → 수정 → 재검증 루프

# plan-pack — PRD + ARCH + ADR generator (Phase B-3)

This bundle is **orchestrator-only**. The main Claude does not write PRD or
ARCHITECTURE content directly — it asks the user, dispatches sub-agents
wrapped via `server.harness.wrap_with_preamble`, then writes the combined
results to `<run_dir>/PRD.md` and `<run_dir>/ARCHITECTURE.md` via
`server.run_dir.write_run_artifact`.

## Artifact

- `~/.claude/channels/assemble/runs/<rid>/PRD.md` — filled from `bundled/plan-pack/templates/PRD.md.template`
- `~/.claude/channels/assemble/runs/<rid>/ARCHITECTURE.md` — filled from `bundled/plan-pack/templates/ARCHITECTURE.md.template`
- `~/.claude/channels/assemble/runs/<rid>/ADR.md` — filled from `bundled/plan-pack/templates/ADR.md.template`

## Sub-agent role mapping (Phase B-3)

| Step | Work | Role | Preferred | Fallback |
|---|---|---|---|---|
| 1 | PRD interview (8 questions) | (main, AskUserQuestion) | — | — |
| 2 | PRD body draft | `plan-implementation` | `Plan` | `general-purpose` |
| 3 | Acceptance Criteria bash draft | `plan-implementation` | `Plan` | `general-purpose` |
| 4 | PRD consistency review | `second-opinion` | `codex:codex-rescue`, `superpowers:code-reviewer` | `general-purpose` |
| 5 | Write `<run_dir>/PRD.md` | (main, write_run_artifact) | — | — |
| 7 | ARCH interview (6 questions) | (main, AskUserQuestion) | — | — |
| 8 | ARCHITECTURE.md draft | `plan-implementation` | `Plan` | `general-purpose` |
| 10 | ADR interview (6 questions) | (main, AskUserQuestion) | — | — |
| 11 | ADR.md draft | `plan-implementation` | `Plan` | `general-purpose` |
| 9 | 3-way cross-doc review (PRD + ARCH + ADR) | `second-opinion` | `codex:codex-rescue`, `superpowers:code-reviewer` | `general-purpose` |

Steps 2 and 3 fire as a *single message with two Agent calls* (parallel — unchanged from Phase B-1).
Steps 8 and 11 are *single dispatch each* — B-2 through B-4 use single dispatch only; B-5 promotes all docs to parallel.

> **Caveat — `Plan` agent for content drafting.** `Plan`'s built-in description is
> "Software architect agent for designing implementation plans", which doesn't
> perfectly match content drafting (PRD/AC/ARCH). Empirically (run
> `20260428-194703-f5dd`) `Plan` returned clean markdown for all 5 dispatches
> when prompted with explicit "do not call ExitPlanMode, return markdown only"
> instructions, but the role mapping is fragile — a future Claude may
> short-circuit into plan-mode UX. If drift appears, fall back to
> `general-purpose`. Phase B-3 is the place to revisit whether a dedicated
> content-draft role is warranted.

## Workflow

> NOTE — Phase B-3: steps 1–11 implemented. Steps 1–8 unchanged from Phase B-2; step 6 extended to cover ADR; step 9 extended to 3-way cross-doc review; steps 10 and 11 are new.

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

The main Claude waits for both calls to return, then proceeds to **Step 4
(consistency review)** — *not* directly to Step 5. Step 4 verifies the bullets,
Step 5 then combines + writes.

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

> Execution order: Steps 7–8–10–11–9 run after Step 5 writes PRD.md; Step 6 (iteration) is the final workflow step.

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

The sub-agent returns the ARCH body as markdown with `## Stack`, `## Directory
tree`, ... headings (one per section). The template *already* contains those
same headings, so a naive concatenation would duplicate them — instead, parse
the sub-agent output into a `{heading: body}` dict and substitute *bodies*
into the template placeholders.

Heading→placeholder map: `Stack`→`{{STACK}}`, `Directory tree`→`{{DIRECTORY_TREE}}`,
`Architectural patterns`→`{{PATTERNS}}`, `Data flow`→`{{DATA_FLOW}}`,
`External dependencies`→`{{EXTERNAL_DEPS}}`, `Module boundaries`→`{{MODULE_BOUNDARIES}}`.
Plus `task`→`{{TASK}}`.

Canonical fill + write:

    import re
    from pathlib import Path
    from server import write_run_artifact

    def split_sections(text):
        """Parse `## Heading\\n<body>\\n## Heading\\n<body>...` into a dict."""
        sections, current_h, buf = {}, None, []
        for line in text.splitlines():
            m = re.match(r'^## (.+?)\\s*$', line)
            if m:
                if current_h:
                    sections[current_h] = '\\n'.join(buf).strip()
                current_h, buf = m.group(1), []
            else:
                buf.append(line)
        if current_h:
            sections[current_h] = '\\n'.join(buf).strip()
        return sections

    s = split_sections(arch_sub_agent_output)
    template = Path.home() / ".claude/skills/assemble/bundled/plan-pack/templates/ARCHITECTURE.md.template"
    filled_arch = (template.read_text()
        .replace("{{TASK}}", task)
        .replace("{{STACK}}", s["Stack"])
        .replace("{{DIRECTORY_TREE}}", s["Directory tree"])
        .replace("{{PATTERNS}}", s["Architectural patterns"])
        .replace("{{DATA_FLOW}}", s["Data flow"])
        .replace("{{EXTERNAL_DEPS}}", s["External dependencies"])
        .replace("{{MODULE_BOUNDARIES}}", s["Module boundaries"]))
    arch_path = write_run_artifact(rid, "ARCHITECTURE.md", filled_arch)

Show `arch_path` to the user, then proceed to Step 10 (ADR interview).

### Step 10 — ADR interview (main Claude, AskUserQuestion)

After Step 8 writes `ARCHITECTURE.md`, collect decision context. Ask 6 questions
across **two `AskUserQuestion` calls of 3 questions each** (within the
platform max-4 limit per call):

Call 5 (D1–D3):

1. Decision #1 — what is the most consequential design choice you made? (one sentence — title only)
2. Decision #2 — what is the second-most consequential choice?
3. Decision #3 — what is the third-most consequential choice?

Call 6 (D4–D6):

4. For each of the three decisions, what is the strongest *rejected alternative* you considered? (number them 1/2/3, one sentence each)
5. For each of the three decisions, what is the main *tradeoff* you are accepting by choosing this path? (number them 1/2/3, one sentence each)
6. Are there any decision-specific risks, unknowns, or constraints we must capture? (one paragraph; "none" is a valid answer)

Three decisions are the minimum to satisfy gate B3.2; the user may volunteer
more, in which case the next step should produce N decisions where N ≥ 3.

### Step 11 — ADR single dispatch + write `ADR.md`

Single Agent dispatch then `write_run_artifact(rid, "ADR.md", filled)` —
same orchestrator-only pattern as Step 8.

Wrap the ADR interview answers + ARCH context (already on disk) + template
skeleton via `server.harness.wrap_with_preamble` (same canonical call pattern
as Steps 2/3/8):

    from server.harness import wrap_with_preamble
    from server import read_run_artifact
    arch_text = read_run_artifact(rid, "ARCHITECTURE.md") or ""
    wrapped_adr = wrap_with_preamble(raw_adr_prompt)

The dispatched prompt instructs the sub-agent to return the *entire decisions
block* as markdown, ready to substitute into the template's `{{DECISIONS_BLOCK}}`
placeholder. The required emitted shape is **three or more** `## Decision N: <title>`
sections, each containing five sub-headings in order:

    ## Decision 1: <title>

    ### Context
    <one paragraph>

    ### Decision
    <one paragraph>

    ### Reasoning
    <one paragraph — why this beats the alternatives>

    ### Rejected alternatives
    <bulleted list — at least one alternative with a one-line reason for rejection>

    ### Tradeoffs
    <bulleted list — at least one tradeoff with a one-line consequence>

    ## Decision 2: …
    ## Decision 3: …

The Step 10 interview only collects user-side input for `### Decision` (the title and one-sentence summary), `### Rejected alternatives`, and `### Tradeoffs`. The sub-agent must **synthesize `### Context` and `### Reasoning` from the loaded `arch_text` plus the PRD's `## Goal` / `## Risks` content** — these two sub-headings are the sub-agent's job, never the user's. Do not emit stubs like "This decision was important." for these sections; if the synthesis cannot be grounded, drop the decision entirely (the user can re-supply on iteration).

The "one-line reason for rejection" + "one-line tradeoff consequence" wording
is what gate B3.2 measures (each decision has *both* a tradeoff and a rejected
alternative subsection populated, beyond the bare gate of "tradeoff *or*
rejected-alternative"). Carrying both reduces the chance the sub-agent emits a
stub like "N/A" that would fail gate B3.3.

Dispatch to a `plan-implementation` sub-agent via a **single Agent call**
(preferred: `Plan`; fallback: `general-purpose`). This is one of the two
Phase B-3 single-dispatch verification locations (the other is Step 8 — ARCH).

Substitute the returned block into the ADR template:

    from pathlib import Path
    from server import write_run_artifact

    template = Path.home() / ".claude/skills/assemble/bundled/plan-pack/templates/ADR.md.template"
    filled_adr = (template.read_text()
        .replace("{{TASK}}", task)
        .replace("{{DECISIONS_BLOCK}}", adr_sub_agent_output.strip()))
    adr_path = write_run_artifact(rid, "ADR.md", filled_adr)

Show `adr_path` to the user, then proceed to Step 9 (3-way cross-doc review).

### Step 9 — 3-way cross-doc second-opinion (PRD ↔ ARCH ↔ ADR consistency)

After `ADR.md` is written (Step 11), dispatch a 3-way cross-doc consistency
review. Read all three artifacts:

    from server import read_run_artifact
    prd_text  = read_run_artifact(rid, "PRD.md") or ""
    arch_text = read_run_artifact(rid, "ARCHITECTURE.md") or ""
    adr_text  = read_run_artifact(rid, "ADR.md") or ""

Wrap all three together via `server.harness.wrap_with_preamble` and dispatch to a
`second-opinion` role (preferred: `codex:codex-rescue`, then
`superpowers:code-reviewer`; fallback: `general-purpose`).

The prompt must explicitly request three categories of finding:

- **PRD ↔ ARCH (gap detection)**: features in PRD `## Core features` that have no
  matching module in ARCH `## Module boundaries`, and architecture decisions in
  ARCH that contradict items in PRD `## Excluded from MVP` (scope-creep risk).
- **ARCH ↔ ADR (decision integrity)**: any architectural choice in ARCH that is
  not backed by a Decision in ADR (missing rationale), and any Decision in ADR
  that contradicts ARCH's stated patterns or module boundaries.
- **PRD ↔ ADR (motivation traceability)**: any Decision in ADR whose Context
  cannot be traced to a need stated in PRD `## Goal` / `## Core features` /
  `## Risks`, and any PRD risk that has no Decision addressing it.

Plus any other flaws, inconsistencies, or omissions — never bare agreement.

Apply the triage protocol from Step 4b: verify each claim, drop unverifiable
speculation, prepend a one-line audit header. Append verified review notes
as a `## Cross-doc review` section to **`ADR.md`** (the last-written doc;
keeps cross-doc context co-located with the doc most likely to be edited
during iteration):

    from datetime import date
    from server import read_run_artifact, write_run_artifact
    current = read_run_artifact(rid, "ADR.md") or ""
    audit_header = f"> 3-way cross-doc verified on {date.today().isoformat()} — {n_kept} kept / {n_dropped} dropped"
    updated = current + "\n\n## Cross-doc review\n\n" + audit_header + "\n\n" + bullets
    write_run_artifact(rid, "ADR.md", updated)

> Note: when running on the iteration yes-path (Step 6), use header `## Cross-doc review (iteration N)` instead of bare `## Cross-doc review`, where N is the current iteration count (Phase B-3 caps at N=1). The first-pass review uses no suffix.

Then proceed to Step 6 (iteration prompt).

### Step 6 — iteration round-trip (one cycle)

After Step 9 (3-way cross-doc review), ask the user via `AskUserQuestion`:

> "All three docs saved — PRD.md, ARCHITECTURE.md, ADR.md. Run one iteration?"
> options: ["yes — refine all three", "no — done"]

- **no → done: exits the workflow.** The user is never forced into a second
  pass. (V4 identity rule — see `project_assemble_v4_spec.md` § "절대 금지
  사항".)
- **yes → re-runs Steps 2+3 (PRD re-draft), Step 8 (ARCH re-draft), and
  Step 11 (ADR re-draft)** with the existing `PRD.md`, `ARCHITECTURE.md`,
  and `ADR.md` loaded as input context, plus a follow-up `AskUserQuestion`
  collecting the user's new emphases ("what feels off in the PRD?", "what
  feels off in the ARCH?", "what feels off in the ADR?").

  **Iteration write order** (explicit — do not improvise):
  1. Run Steps 2+3 in parallel (single message, two Agent calls): PRD body
     re-draft + AC bash re-draft.
  2. Run Step 8 (ARCH re-draft) — single dispatch. Can fire in the same
     parallel message as Steps 2+3 since the inputs are independent
     (existing PRD + ARCH + ADR + emphases), or sequentially after Steps 2+3
     if you prefer simpler control flow.
  3. Run Step 11 (ADR re-draft) — single dispatch. Same independence
     argument as Step 8; can be parallel with Steps 2+3 + 8.
  4. **Step 5 overwrites `PRD.md`** with the new body + new AC bash.
  5. **Step 8 (continued) overwrites `ARCHITECTURE.md`** with the new
     sections. (Cross-doc review lives on ADR.md only — no leftover to
     discard here.)
  6. **Step 11 (continued) overwrites `ADR.md`** with the new decisions
     block — discard the old `## Cross-doc review` section here; Step 9
     will regenerate it.
  7. Run Step 9 again on the refreshed triple (PRD ↔ ARCH ↔ ADR).
  8. Step 9 (continued) appends `## Cross-doc review (iteration 1)` to
     `ADR.md` (note the iteration suffix to distinguish from the first-pass
     review).

  **Step 4 (intra-PRD consistency review) is intentionally skipped on the
  iteration yes-path** — same reasoning as Phase B-2: the 3-way cross-doc
  review in Step 9 provides the second-opinion coverage for the refined
  PRD ↔ ARCH ↔ ADR triple. Re-running Step 4 would double-pay for review
  without checking the new dimensions that matter most after iteration.

ADR.md is always re-run alongside PRD and ARCH in the iteration — they are
produced as a triple and must remain consistent.

Phase B-3 covers exactly **one iteration**. After the iteration completes
(yes-path), the workflow exits unconditionally — even if the user requests
another pass, the main Claude must reply "iteration cap reached for Phase B-3;
rerun `/assemble` to start a new run" and stop. Multi-iteration support (3–7
counts with stop conditions) is a Phase B post-tuning track.

> **Dogfood evidence carried forward** (run `20260428-194703-f5dd`, Phase B-2):
> a single iteration resolved 4 prior CRITICALs and *introduced 1 new CRITICAL*.
> The new CRITICAL exited unresolved when the workflow hit the cap. Phase B-3
> dogfood (run id captured in `docs/dogfood/phase-b-3.md`) re-tests this with
> the 3-way review surface.
