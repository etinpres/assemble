---
name: plan-pack
description: Plan stage ★ bundle — produce PRD + ARCH + ADR + UI_GUIDE with iteration. Spec, requirements, plan, architecture doc, decision record, UI guide — bundled plan tool. (Phase B-4: PRD + ARCH + ADR + UI_GUIDE.)
---

[HARNESS RULES — 무시 금지]
1. 불확실하면 추측 금지, 사용자 질문 우선
2. 과설계 금지, YAGNI
3. 요청 범위 밖 코드 임의 수정 금지
4. 버그 수정 시 재현 테스트 → 실패 확인 → 수정 → 재검증 루프

# plan-pack — PRD + ARCH + ADR + UI_GUIDE generator (Phase B-4)

This bundle is **orchestrator-only**. The main Claude does not write PRD,
ARCHITECTURE, ADR, or UI_GUIDE content directly — it asks the user,
dispatches sub-agents wrapped via `server.harness.wrap_with_preamble`,
then writes the combined results to `<run_dir>/{PRD,ARCHITECTURE,ADR,UI_GUIDE}.md`
via `server.run_dir.write_run_artifact`.

## Artifact

- `~/.claude/channels/assemble/runs/<rid>/PRD.md` — filled from `bundled/plan-pack/templates/PRD.md.template`
- `~/.claude/channels/assemble/runs/<rid>/ARCHITECTURE.md` — filled from `bundled/plan-pack/templates/ARCHITECTURE.md.template`
- `~/.claude/channels/assemble/runs/<rid>/ADR.md` — filled from `bundled/plan-pack/templates/ADR.md.template`
- `~/.claude/channels/assemble/runs/<rid>/UI_GUIDE.md` — filled from `bundled/plan-pack/templates/UI_GUIDE.md.template`

## Sub-agent role mapping (Phase B-4)

| Step | Work | Role | Preferred | Fallback |
|---|---|---|---|---|
| 1 | PRD interview (8 questions) | (main, AskUserQuestion) | — | — |
| 2 | PRD body draft | `plan-implementation` | `general-purpose` | `Plan` |
| 3 | Acceptance Criteria bash draft | `plan-implementation` | `general-purpose` | `Plan` |
| 4 | PRD consistency review | `second-opinion` | `codex:codex-rescue`, `superpowers:code-reviewer` | `general-purpose` |
| 5 | Write `<run_dir>/PRD.md` | (main, write_run_artifact) | — | — |
| 7 | ARCH interview (6 questions) | (main, AskUserQuestion) | — | — |
| 8 | ARCHITECTURE.md draft | `plan-implementation` | `general-purpose` | `Plan` |
| 10 | ADR interview (6 questions) | (main, AskUserQuestion) | — | — |
| 11 | ADR.md draft | `plan-implementation` | `general-purpose` | `Plan` |
| 12 | UI_GUIDE interview (6 questions) | (main, AskUserQuestion) | — | — |
| 13 | UI_GUIDE.md draft | `plan-implementation` | `general-purpose` | `Plan` |
| 9 | 4-way cross-doc review (PRD + ARCH + ADR + UI_GUIDE) | `second-opinion` | `codex:codex-rescue`, `superpowers:code-reviewer` | `general-purpose` |

Steps 2 and 3 fire as a *single message with two Agent calls* (parallel — unchanged from Phase B-1).
Steps 8, 11, and 13 are *single dispatch each* — B-2 through B-4 use single dispatch only; B-5 promotes all docs to parallel.

> **Note — `plan-implementation` role: preferred `general-purpose`, fallback `Plan`.**
> Phases B-1 and B-2 used `Plan` as preferred for PRD/AC/ARCH drafting.
> `Plan`'s built-in description is "Software architect agent for designing
> implementation plans", which empirically returned clean markdown for the
> bulk of dispatches across the B-2 (`20260428-194703-f5dd`) and B-3
> (`20260428-214502-6b79`) dogfoods, but exhibited the predicted drift
> at least once — B-3 Finding #3: `Plan` appended an unrequested
> `### Critical Files for Implementation` section to a PRD body draft. The
> orchestrator stripped it, but the drift was real and reproducible. Hot-fix
> branch `v4-plan-pack-content-role-fix` (commit `85366f1`) swapped the
> mapping post-B-3: `general-purpose` is now preferred, `Plan` is fallback
> for environments where `general-purpose` is absent or unstable. Phase B-4
> inherits this swap into the new UI_GUIDE row without re-acting on it; the
> Phase B-4 dogfood will produce the first 4-doc trace under
> `general-purpose`-as-preferred.

## Workflow

> NOTE — Phase B-4: steps 1–13 implemented. Steps 1–11 unchanged from Phase B-3; step 6 extended to cover UI_GUIDE; step 9 extended to 4-way cross-doc review (with antipattern audit); steps 12 and 13 are new.

> **Execution sequence (canonical — do not infer from step numbers):**
>
> ```
> 0 → 1 → (2 + 3 in parallel) → 4 → 5 → 7 → 8 → 10 → 11 → 12 → 13 → 9 → 6
> ```
>
> Step numbers reflect *historical addition order*, not execution order. Steps 7–13 are run in the sequence shown above (ARCH interview → ARCH dispatch → ADR interview → ADR dispatch → UI interview → UI dispatch). Step 9 (cross-doc review) runs *after* all four docs are written. Step 6 (iteration loop) is the final step. Do NOT run steps in numeric order.

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
firing. Canonical call (this is the recommended pattern):

```python
from server.harness import wrap_with_preamble
wrapped_body = wrap_with_preamble(raw_body_prompt)
wrapped_ac   = wrap_with_preamble(raw_ac_prompt)
```

Pass `wrapped_body` / `wrapped_ac` as the Agent `prompt` field. The
function emits the exact 4-rule preamble + `[TASK]` block — see
`server/harness.py`. Inlining the preamble literal is permitted as an
alternative to the function call; both must produce byte-identical
preamble bytes, verified at dogfood time via gate B5.7.

#### Preamble byte-identity

> The orchestrator may dispatch a sub-agent prompt either by (a) calling `wrap_with_preamble(prompt)` and passing the result, or (b) inlining the preamble block literally as the prompt prefix. Both forms are acceptable. The contract is byte-identity: every dispatched prompt's preamble block, when isolated and hashed, MUST match the sha256 of `bundled/_shared/harness-preamble.md`. Drift in either direction (rewording, missing newline, added text) is a contract violation. Dogfood gate B5.7 verifies this.

##### Replayable on-disk evidence (`runs/<rid>/dispatches.jsonl`)

After every dispatch, the orchestrator MUST also call `record_dispatch` to
append a hash-only record to `runs/<rid>/dispatches.jsonl`. This converts
the byte-identity contract from orchestrator self-report into a replayable
disk audit — gate B5.7 verifies via `verify_dispatches(rid)` reading the
JSONL, not by trusting orchestrator narration.

```python
from server.harness import wrap_with_preamble, record_dispatch
wrapped = wrap_with_preamble(raw_prompt)
record_dispatch(rid, "step6.iter2.PRD", wrapped,
                subagent_type="general-purpose",
                description="iter2 PRD re-draft")
# then dispatch via Agent(prompt=wrapped, ...)
```

The recorded payload is hashes only (no full prompt text), so
`dispatches.jsonl` is privacy-safe and compact: `{ts, step, subagent_type,
description, preamble_sha256, preamble_bytes, body_sha256, body_bytes}`.
Audit constant lives at `server.harness.canonical_preamble_sha256()`.

Then **fire both in a single message with two Agent calls** (true parallel
dispatch — this is the Phase B-1 parallel-dispatch verification location
*a*):

> Sequential fallback is permitted only if a documented orchestrator constraint blocks parallel dispatch (e.g. dependent inputs); the platform itself does not constrain to <2. See `docs/research/2026-04-29-platform-limit.md`.

- Sub-task A — PRD body. Role `plan-implementation` (preferred `general-purpose`,
  fallback `Plan`). Returns Goal / Users / Core features /
  Excluded from MVP / Design direction / Risks.
- Sub-task B — AC bash. Role `plan-implementation` (preferred `general-purpose`,
  fallback `Plan`). Given the success criterion (interview Q5)
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
`general-purpose`). The dispatch uses the bare task prompt — V4 spec
memory describes a future `roles.json` carrying `fallback_context` per
role; until that lands in a later phase, dispatches use the prompt as-is.

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

On the first pass, take the simpler path: append `## Review notes` to
the PRD body. Iteration-mode absorption is the responsibility of Step 6
(see §"Iteration round-trip" + §"Multi-iteration loop"). Step 4 itself
never re-dispatches Steps 2/3 — append-only on every invocation.

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

> Execution order: Steps 7–8–10–11–12–13–9 run after Step 5 writes PRD.md; Step 6 (iteration) is the final workflow step.

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
(preferred: `general-purpose`; fallback: `Plan`). This is the Phase B-2
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
(preferred: `general-purpose`; fallback: `Plan`). This is one of the two
Phase B-3 single-dispatch verification locations (the other is Step 8 — ARCH).

Substitute the returned block into the ADR template:

    from pathlib import Path
    from server import write_run_artifact

    template = Path.home() / ".claude/skills/assemble/bundled/plan-pack/templates/ADR.md.template"
    filled_adr = (template.read_text()
        .replace("{{TASK}}", task)
        .replace("{{DECISIONS_BLOCK}}", adr_sub_agent_output.strip()))
    adr_path = write_run_artifact(rid, "ADR.md", filled_adr)

Show `adr_path` to the user, then proceed to Step 12 (UI_GUIDE interview).

### Step 12 — UI_GUIDE interview (main Claude, AskUserQuestion)

After Step 11 writes `ADR.md`, collect UI guide context. Ask 6 questions
across **two `AskUserQuestion` calls of 3 questions each** (within the
platform max-4 limit per call):

Call 7 (U1–U3):

1. Visual identity / aesthetic in one line — what should this UI feel like to a first-time user? (e.g. "high-density information panel, low-chrome", "playful editorial, big typography")
2. Primary user flows you want to UI-prototype as priority screens — list 3 flows in one line each (e.g. "first-run onboarding", "main daily-use loop", "error/empty state")
3. Required component patterns — list 3 components or interaction patterns the UI must include (e.g. "data table with inline edit", "command palette", "tabbed settings", "modal wizard")

Call 8 (U4–U6):

4. Brand color tokens (hex or named) — list up to 5 with role (e.g. "#0F1115 primary surface", "amber accent for warnings"). "no preference" is a valid answer (the sub-agent will then propose neutral tokens consistent with the design direction).
5. Typography — primary font family + 1 supporting (e.g. "Inter UI / JetBrains Mono mono"). "no preference" is a valid answer.
6. Antipattern emphasis — beyond the baseline list in the template, are there any project-specific things the UI must avoid? (e.g. "no skeuomorphic shadows", "no carousel home-page hero"). "none" is a valid answer.

The interview deliberately surfaces antipattern emphasis (Q6) so gate B4.3
(no antipattern artifacts in the rendered UI body) has user-supplied
project-specific signal beyond the canonical baseline shipped in the
template.

### Step 13 — UI_GUIDE single dispatch + write `UI_GUIDE.md`

Single Agent dispatch then `write_run_artifact(rid, "UI_GUIDE.md", filled)` —
same orchestrator-only pattern as Steps 8 and 11.

Wrap the UI interview answers + PRD `## Design direction` (already on disk)
+ template skeleton via `server.harness.wrap_with_preamble` (same canonical
call pattern as Steps 2/3/8/11):

    from server.harness import wrap_with_preamble
    from server import read_run_artifact
    prd_text = read_run_artifact(rid, "PRD.md") or ""
    wrapped_ui = wrap_with_preamble(raw_ui_prompt)

The dispatched prompt instructs the sub-agent to return the *entire UI guide
body* as markdown, ready to substitute into the template's `{{UI_BODY}}`
placeholder. The required emitted shape is the following five `## Section`
headings in order (the sub-agent must emit each as a `## ` heading; do not
emit `# ` or `### `):

    ## Visual identity
    <one-paragraph aesthetic statement, plus a short bullet list of "feels like" reference points>

    ## Color tokens
    <table or bullet list — token name, hex value, role, optional dark-mode pair>

    ## Typography
    <bullet list — family, weights, sizes, line-heights, primary use case>

    ## Component patterns
    <one section per component pattern from interview Q3 — describe layout, primary states, behavior. ≥3 components total.>

    ## Priority screens
    <one numbered subsection per priority flow from interview Q2 — describe screen layout in prose with explicit reference to which Component patterns it composes. ≥3 screens.>

The sub-agent contract additionally requires: do NOT emit any of the
antipattern keywords already enumerated in the template's `## Antipatterns
to avoid` section (gradient-text, glass morphism, backdrop-blur,
all-purple, emoji-as-decoration, Lorem ipsum, TODO/FIXME, "innovative",
"seamless", etc.). Gate B4.3 enforces this on the rendered file.

The Step 12 interview only collects user-side input for visual identity (Q1),
priority flows (Q2), required components (Q3), color preferences (Q4),
typography preferences (Q5), and project-specific antipatterns (Q6). The
sub-agent must **synthesize the full content of all five sections from the
loaded `prd_text` (`## Design direction` and `## Core features`) plus the
interview answers** — no stub sections like "TBD: fill in colors". If a
section cannot be synthesized (e.g. user said "no preference" for color and
no PRD signal exists), the sub-agent must propose a defensible neutral
default and document the choice in the section's first sentence.

Dispatch to a `plan-implementation` sub-agent via a **single Agent call**
(preferred: `general-purpose`; fallback: `Plan`). This is one of the three
Phase B-4 single-dispatch verification locations (the others are Step 8 — ARCH
and Step 11 — ADR). The role swap from B-3 Finding #3 hot-fix is inherited
verbatim — the dispatched prompt does not need any extra negative wording
about `### Critical Files`; `general-purpose` does not exhibit the drift
that motivated the swap.

Substitute the returned body into the UI_GUIDE template:

    from pathlib import Path
    from server import write_run_artifact

    template = Path.home() / ".claude/skills/assemble/bundled/plan-pack/templates/UI_GUIDE.md.template"
    # Pull design direction from PRD §6 — same string the sub-agent received as context
    design_direction_lines: list[str] = []
    collecting = False
    for line in prd_text.splitlines():
        if line.startswith("## Design direction"):
            collecting = True
            continue
        if collecting:
            if line.startswith("## "):
                break
            design_direction_lines.append(line)
    design_direction = "\n".join(design_direction_lines).strip() or "(not specified in PRD)"

    filled_ui = (template.read_text()
        .replace("{{TASK}}", task)
        .replace("{{DESIGN_DIRECTION}}", design_direction)
        .replace("{{UI_BODY}}", ui_sub_agent_output.strip()))
    ui_path = write_run_artifact(rid, "UI_GUIDE.md", filled_ui)

Show `ui_path` to the user, then proceed to Step 9 (4-way cross-doc review).

### Step 9 — 4-way cross-doc second-opinion (PRD ↔ ARCH ↔ ADR ↔ UI_GUIDE consistency)

After `UI_GUIDE.md` is written (Step 13), dispatch a 4-way cross-doc
consistency review. Read all four artifacts:

    from server import read_run_artifact
    prd_text  = read_run_artifact(rid, "PRD.md") or ""
    arch_text = read_run_artifact(rid, "ARCHITECTURE.md") or ""
    adr_text  = read_run_artifact(rid, "ADR.md") or ""
    ui_text   = read_run_artifact(rid, "UI_GUIDE.md") or ""

Wrap all four together via `server.harness.wrap_with_preamble` and dispatch
to a `second-opinion` role (preferred: `codex:codex-rescue`, then
`superpowers:code-reviewer`; fallback: `general-purpose`).

The prompt must explicitly request six categories of finding (the three
B-3 categories + three new UI_GUIDE-specific categories):

- **PRD ↔ ARCH (gap detection)**: features in PRD `## Core features` that
  have no matching module in ARCH `## Module boundaries`, and
  architecture decisions in ARCH that contradict items in PRD
  `## Excluded from MVP` (scope-creep risk).
- **ARCH ↔ ADR (decision integrity)**: any architectural choice in ARCH
  that is not backed by a Decision in ADR (missing rationale), and any
  Decision in ADR that contradicts ARCH's stated patterns or module
  boundaries.
- **PRD ↔ ADR (motivation traceability)**: any Decision in ADR whose
  Context cannot be traced to a need stated in PRD `## Goal` /
  `## Core features` / `## Risks`, and any PRD risk that has no Decision
  addressing it.
- **PRD ↔ UI_GUIDE (design direction audit)**: every choice the UI guide
  makes in `## Visual identity`, `## Color tokens`, `## Typography`, and
  `## Component patterns` must be consistent with PRD §6 `## Design direction`.
  Contradictions ("PRD says low-chrome / UI uses heavy
  decoration") are findings; **violations of the antipattern list in the
  UI_GUIDE template's `## Antipatterns to avoid` section are
  CRITICAL findings** and seed gate B4.3.
- **ARCH ↔ UI_GUIDE (component coverage)**: every priority screen in
  UI_GUIDE `## Priority screens` must compose at least one ARCH
  `## Module boundaries` module — orphan UI screens that don't map to a
  module are findings (either UI overreach or missing ARCH module).
- **ADR ↔ UI_GUIDE (UX decision integrity)**: any UI choice that is in
  scope for an ADR Decision (e.g. accessibility floor, dark-mode support,
  i18n) but is not addressed there is a finding (either an ADR gap or a
  UI assumption that should be promoted to a Decision).
- **Numerical / unit consistency (cross-doc)**: any numerical constraint
  that appears in two or more docs (resolution, pixel size, time budget,
  accuracy threshold, sample count, byte size) MUST use consistent units.
  Example: PRD `≥1080p` vs ARCH `≤1920px long edge` is inconsistent
  (resolution standard vs pixel length, even if numerically equivalent
  in landscape). PRD `30초 SLA` vs ARCH `30s timeout budget` vs ARCH
  `30000ms watchdog` would each need normalization. Flag as a finding;
  the resolution lives in whichever doc owns the constraint (typically
  PRD for user-visible budgets, ARCH for internal budgets). Addresses
  B-5 dogfood Finding #4 (1080p ↔ 1920px iter1 drift).

Plus any other flaws, inconsistencies, or omissions — never bare agreement.

Apply the triage protocol from Step 4b: verify each claim, drop unverifiable
speculation, prepend a one-line audit header. Append verified review notes
as a `## Cross-doc review` section to **`ADR.md`** (the last-written doc
*before* UI_GUIDE was added in B-4; keeping cross-doc context co-located
with ADR.md preserves the B-3 convention and the same "doc most likely to
be edited during iteration" reasoning still applies — design decisions ride
on ADR, and that is where reviewers will look first):

    from datetime import date
    from server import read_run_artifact, write_run_artifact
    current = read_run_artifact(rid, "ADR.md") or ""
    audit_header = f"> 4-way cross-doc verified on {date.today().isoformat()} — {n_kept} kept / {n_dropped} dropped"
    # First-pass uses bare heading; iterations use suffixed heading.
    # `iteration_count` is 0 for first-pass, 1+ for iterations (read from
    # runs/<rid>/iteration_state.json — see Step 6 multi-iteration loop).
    heading = "## Cross-doc review" if iteration_count == 0 else f"## Cross-doc review (iteration {iteration_count})"
    # Precondition: the chosen heading must not already exist in `current`.
    # If it does, Step 11 (continued) failed to overwrite cleanly — abort
    # rather than create a duplicate section.
    assert heading not in current, (
        f"contract violation: heading {heading!r} already in ADR.md; "
        "Step 11 should have overwritten the file from scratch (see Step 6 step 7)"
    )
    updated = current + "\n\n" + heading + "\n\n" + audit_header + "\n\n" + bullets
    write_run_artifact(rid, "ADR.md", updated)

> Note on heading semantics: first-pass (`iteration_count == 0`) uses bare `## Cross-doc review`. Each iteration appends a NEW section with suffix `(iteration N)`. Phase B-5 multi-iteration loop runs up to 7 iterations, so ADR.md may end up with `## Cross-doc review`, `## Cross-doc review (iteration 1)`, `## Cross-doc review (iteration 2)`, … each fresh. The assert above guards against duplicate same-named sections (which would signal Step 11's overwrite failed).

Then proceed to Step 6 (iteration prompt).

### Step 6 — iteration round-trip (one cycle)

**After the FIRST Step 9 cross-doc review only** (`iteration_count == 0`), ask the user via `AskUserQuestion`:

> "All four docs saved — PRD.md, ARCHITECTURE.md, ADR.md, UI_GUIDE.md. Run one iteration?"
> options: ["yes — refine all four", "no — done"]

For `iteration_count ≥ 1`, the entry prompt is replaced by §"User exit override" below (`"Continue iterating?"`). The two prompts never both fire on the same iteration boundary.

- **no → done: exits the workflow.** The user is never forced into a second
  pass. (V4 identity rule — see `project_assemble_v4_spec.md` § "절대 금지
  사항".)
- **yes → re-runs Steps 2+3 (PRD re-draft), Step 8 (ARCH re-draft),
  Step 11 (ADR re-draft), and Step 13 (UI_GUIDE re-draft)** with the
  existing `PRD.md`, `ARCHITECTURE.md`, `ADR.md`, and `UI_GUIDE.md` loaded
  as input context, plus a follow-up `AskUserQuestion` collecting the
  user's new emphases ("what feels off in the PRD?", "what feels off in
  the ARCH?", "what feels off in the ADR?", "what feels off in the
  UI_GUIDE?").

  > The constraint below applies to every iteration in the loop above, not only the first.

  **Iteration scope discipline** (mandatory constraint on all iteration sub-agent prompts — addresses B-4 Findings #4 + #5 and B-5 Findings #1 + #2):

  When constructing the iteration prompts for Steps 2/3, 8, 11, and 13, the orchestrator MUST include this constraint verbatim in every dispatched prompt's `[TASK]` block:

  > Scope discipline: PRD `## Core features` is the authoritative scope. Do not introduce new features, modules, components, screens, or token sets that have no counterpart in the existing PRD `## Core features`. If iteration emphasis suggests a feature not yet in PRD, escalate to the user via the orchestrator instead of silently adding it. Items the ADR has explicitly deferred (e.g. via a `> **Future ADRs**` blockquote) MUST NOT be pre-emptively decided in this iteration's ARCH/ADR/UI_GUIDE re-drafts. Existing sections that are not the explicit target of the iteration emphasis MUST be returned verbatim — do not reword Reasoning/Tradeoffs/Rejected-alternatives blocks just because you are re-emitting the document. Pre-existing identifiers (variable names, token names, module names, component names) MUST NOT be renamed unless the rename IS the requested change; maintain identifier continuity across iterations.

  This guard combines two guards. **B-4 origin (scope-creep)**: UI_GUIDE iter1 added dark-mode token pairs that ADR explicitly deferred, and ARCH iter1 added `edit`/`toggleAll` actions without a PRD signal which UI_GUIDE then composed Screen C around. **B-5 origin (cosmetic drift)**: iter1 ADR sub-agent reworded the Reasoning/Tradeoffs prose in Decisions 1–3 despite explicit "preserve verbatim" instructions, and iter1 UI_GUIDE renamed pre-existing color tokens (`--color-text-primary` → `--color-text`) without a request — both are cosmetic edits the sub-agent volunteered, not contract violations on PRD scope, but they break trace-byte stability across iterations. The verbatim+no-rename clauses close that latitude.

  **Orchestrator enforcement (concrete steps):**
  1. After a sub-agent returns its iteration re-draft (a string), the orchestrator scans the return for feature/module/component/screen/token names.
  2. For each name found, check whether it has a PRD anchor: (a) the name appears verbatim in PRD `## Core features` bullet text, OR (b) the name appears verbatim in the sub-bullet/elaboration text directly under one of those bullets. String-match only — no semantic-similarity inference.
  3. If the name has NO PRD anchor: delete the corresponding section/block from the returned string before passing it to the template-fill step. Do NOT write the unstripped return to disk.
  4. Record stripped item names in a local `stripped_items: list[str]` (orchestrator-side, in-memory for this run).
  5. When Step 9 (continued) constructs the audit header (the `> 4-way cross-doc verified on {date} — {n_kept} kept / {n_dropped} dropped` line), append a second blockquote line *only if* `stripped_items` is non-empty:
     `> scope-discipline: {len(stripped_items)} items stripped — {', '.join(stripped_items)}`
  6. If `stripped_items` is empty, omit the second line entirely (no need to broadcast a no-op).

  **Iteration write order** (explicit — do not improvise):
  1. Run Steps 2+3 in parallel (single message, two Agent calls): PRD body
     re-draft + AC bash re-draft.
  2. Run Step 8 (ARCH re-draft) — single dispatch. MUST fire in the same
     parallel message as Steps 2+3 (inputs are independent: existing
     PRD + ARCH + ADR + UI_GUIDE + emphases). Sequential fallback is
     restricted to the two cases listed in step 4 below.
  3. Run Step 11 (ADR re-draft) — single dispatch. Same independence
     argument as Step 8; can be parallel with Steps 2+3 + 8.
  4. Run Step 13 (UI_GUIDE re-draft) — single dispatch. Same independence
     argument; can be parallel with Steps 2+3 + 8 + 11. **This is the
     true 4-way parallel-dispatch surface that B-5 formalizes** — fire all
     four iteration dispatches in a single message with four Agent calls.

     > Empirical evidence (`docs/research/2026-04-29-platform-limit.md`): a controlled platform-limit experiment dispatched 2 / 3 / 4 / 5 `general-purpose` Agent calls in a single message. All four trials returned successful — no reject, no rate-limit, no silent-degrade. The platform tolerates at least 5-way parallel dispatch in a single response. Sequential fallback is therefore an orchestrator timing choice, not a platform constraint, and MUST NOT be the default at the iteration write surface (Step 6 step 4).

     Sequential fallback at this step is restricted to two cases: (a) a
     documented input dependency exists between iteration dispatches, or
     (b) the orchestrator detects a retry-after on a previous attempt.
     General "Agent-call budget caution" is no longer sufficient grounds.
  5. **Step 5 overwrites `PRD.md`** with the new body + new AC bash.
  6. **Step 8 (continued) overwrites `ARCHITECTURE.md`** with the new
     sections. (Cross-doc review lives on ADR.md only — no leftover to
     discard here.)
  7. **Step 11 (continued) overwrites `ADR.md`** with the new decisions
     block. Overwrite from scratch — re-run the Step 11 template fill
     (template + new decisions block + `{{TASK}}`) and `write_run_artifact`
     the result. Do NOT read the existing `ADR.md` first; the file is
     rewritten in full so the prior `## Cross-doc review` section
     vanishes naturally. Step 9 (continued) re-introduces a fresh
     `## Cross-doc review (iteration N)` section in step 10 below.
  8. **Step 13 (continued) overwrites `UI_GUIDE.md`** with the new
     sections.
  9. Run Step 9 again on the refreshed quadruple
     (PRD ↔ ARCH ↔ ADR ↔ UI_GUIDE).
  10. Step 9 (continued) appends `## Cross-doc review (iteration 1)` to
      `ADR.md` (note the iteration suffix to distinguish from the
      first-pass review).

  **Step 4 (intra-PRD consistency review) is intentionally skipped on the
  iteration yes-path** — same reasoning as Phase B-2/B-3: the 4-way
  cross-doc review in Step 9 provides the second-opinion coverage for the
  refined PRD ↔ ARCH ↔ ADR ↔ UI_GUIDE quadruple. Re-running Step 4 would
  double-pay for review without checking the new dimensions that matter
  most after iteration.

UI_GUIDE.md is always re-run alongside PRD, ARCH, and ADR in the iteration
— they are produced as a quadruple and must remain consistent.

#### Multi-iteration loop with stop conditions (Phase B-5)

Phase B-5 replaces the prior 1-iteration cap (B-1 through B-4) with an
explicit stop-condition loop. Three consecutive phases (B-2, B-3, B-4) all
showed the same recurrence — iteration resolves prior findings (4/4 → 9/10
→ 12/12) but introduces NEW findings that exit unresolved at the cap. The
loop below is the contracted answer.

**Stop condition (verbatim — do not paraphrase in implementations):**

> The orchestrator continues iterating while either condition holds: (a) Step 9 review reports `NEW ≥ 1` for the just-completed iteration, OR (b) the most recent two iterations have not both satisfied `RESOLVED ≥ 80% AND NEW ≤ 0`. Iteration stops when two consecutive iterations both satisfy `RESOLVED ≥ 80% AND NEW ≤ 0`, or when the iteration counter reaches 7, whichever comes first.

**Iteration state tracking (verbatim):**

> The orchestrator maintains a per-run state file at
> `runs/<rid>/iteration_state.json` with shape
> `{"iterations": [{"index": N, "resolved_pct": F, "new_count": N,
> "stopped": bool, "reason": "..."}, ...]}`. The file is updated after
> each Step 9 cross-doc review. Termination reason is one of
> `stop-condition-met`, `cap-reached`, `user-requested-stop`.

After each Step 9 review, the main Claude parses the RESOLVED/UNRESOLVED/NEW
counts (Step 9 already produces these), computes `resolved_pct = RESOLVED /
(RESOLVED + UNRESOLVED + NEW)`, appends a new entry to
`iteration_state.json`, and decides whether to continue.

##### User exit override

After every iteration (including iterations 1 and 2 before the stop
condition can have fired), the orchestrator asks via `AskUserQuestion`:

> "Continue iterating?"
> options: ["yes — run another iteration", "no — stop here"]

A "no — stop here" answer terminates the loop unconditionally and records
`reason: "user-requested-stop"` in `iteration_state.json`. The user is
never forced through additional iterations to satisfy the stop condition
(V4 identity rule — user agency is preserved).

##### Iteration cap exceeded

If the iteration counter reaches 7 without the stop condition firing and
without a user no-answer, the orchestrator emits a one-line warning to the
user citing the cap and the unresolved finding count from the most recent
Step 9 review (e.g. "iteration cap (7) reached with 2 unresolved findings;
exiting"), records `reason: "cap-reached"` in `iteration_state.json`, and
stops. The user can still rerun `/assemble` for a fresh run.

> **Dogfood evidence (Phase B-5, run `20260429-135600-3b6d` —
> `docs/dogfood/phase-b-5.md`):** the multi-iteration loop is exercised
> end-to-end under `ASSEMBLE_BUNDLED_ONLY=1` (blank-Mac sim) with true
> 4-way parallel iteration dispatch and sha256 preamble byte-identity
> verification. iter1 resolved 5/5 first-pass findings, introduced 3 NEW;
> user-override path terminated the loop with `reason: user-requested-stop`,
> recorded in `runs/20260429-135600-3b6d/iteration_state.json`.
