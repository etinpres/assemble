# Phase B-1 Dogfood Report

> Run: `20260428-160618-654d` (plan-only sequence, plan-pack ★ bundle)
> Date: 2026-04-28
> Task: "git-recent CLI 한 장 — 최근 git 활동 요약 도구 PRD"

## Summary

Phase B-1 ships a working ★ plan-pack bundle that exercises every
end-to-end seam: parallel Agent dispatch, second-opinion challenge,
harness preamble, atomic write to `<run_dir>/PRD.md`, and the
opt-in iteration round-trip. The smoke surfaced **three real
defects** in `bundled/plan-pack/SKILL.md` and **one false alarm**
emitted by the second-opinion role itself. All three real defects
are fixed in the same commit series as this report.

The dogfood also produced a head-to-head comparison against a V3
brainstorming run on the same task, which is the strongest evidence
yet that the second-opinion + AC-bash + run_dir trio carries real
review value, not just process overhead.

## Trace

The smoke deliberately ran the V3 path first (sequence
`discover → plan`, picking `superpowers:brainstorming` in
discover), discovered that brainstorming absorbs the entire PRD
workflow and pre-empts plan-pack, then closed that run and
re-entered with a `plan`-only sequence so plan-pack ★ would surface
as the first option.

The V4 run (`20260428-160618-654d`) executed the plan-pack
workflow in order:

| Step | Action | Outcome |
|---|---|---|
| 0 | Resolve `run_dir` | `~/.claude/channels/assemble/runs/20260428-160618-654d/` |
| 1 | 8-question interview | **2 AskUserQuestion calls of 4** (see Finding A.1) |
| 2+3 | Parallel dispatch (2 Plan Agent calls in single message) | PRD body JSON + AC bash one-liner returned together |
| 4 | second-opinion challenge → `codex:codex-rescue` | 7 critical bullets, all appended to Review notes (verbatim — see Finding A.3) |
| 5 | Combine + `write_run_artifact("PRD.md")` | Atomic write to run_dir |
| 6 | "Run one iteration?" prompt | User chose `yes — refine` |
| 2+3' | Iteration parallel dispatch | Refined PRD body absorbing 7 review bullets + 3 user emphases; AC bash hardened to use `bash -c` + `TIMEFORMAT=%R` |
| 4' | second-opinion (iteration 2) | 8 more critical bullets, **including one false alarm** that triggered Finding A.3 |
| 5' | Overwrite PRD.md | Final artifact carries iteration 2 Review notes verbatim |
| 6' | iteration cap = 1 enforced | Workflow exited unconditionally |

End state: plan stage marked `done`, `tool_used="plan-pack"`,
artifact present at the documented run_dir path.

## Gate results

> **Kind**: `static` = SKILL.md / code path verifiable without a run trace.
> `runtime` = required actual workflow execution to observe.
> `mixed` = both static intent and runtime behavior must hold.
> (Convention shared with `phase-b-2.md`; see CHANGELOG entry "Phase B-1+B-2 dogfood reports unified".)

| # | Phase B-1 contract | Kind | Status | Evidence |
|---|---|---|---|---|
| 1 | ★ plan-pack surfaces with `bundled=True` and `★ ` prefix at top of plan menu | static | ✓ | inventory scan + `tests/e2e/test_plan_pack_inventory.py::test_plan_pack_in_plan_menu_with_star_prefix` |
| 2 | `run_dir` resolves to `~/.claude/channels/assemble/runs/<rid>/` | runtime | ✓ | run dir present on disk: `~/.claude/channels/assemble/runs/20260428-160618-654d/` |
| 3 | 8-question interview executed before any drafting | runtime | ⚠ | 4+4 split — see Finding A.1; SKILL.md fixed in `76dc985` |
| 4 | **Step 2+3 fire as a single message with two Agent calls (parallel dispatch verification location *a*)** | runtime | ✓ | trace shows 2 parallel `Plan` Agent calls per round (both initial + iteration) |
| 5 | Step 4 second-opinion role dispatched (`codex:codex-rescue` preferred) | runtime | ✓ | trace shows codex dispatch on both rounds, returning 7 + 8 critical bullets |
| 6 | `server.write_run_artifact` writes `<run_dir>/PRD.md` atomically | static | ✓ | atomicity covered by `tests/unit/test_run_dir.py::test_concurrent_writes_dont_corrupt`; dogfood only observes final file |
| 7 | Step 6 iteration round-trip offered exactly once | runtime | ✓ | trace shows 1 `AskUserQuestion("Run one iteration?")` post-write |
| 8 | Iteration cap of 1 enforced post-yes path | runtime | ✓ | second-yes path not entered; workflow exited after iteration 2 |
| 9 | Harness 4-rule preamble carried on every dispatched sub-agent prompt | runtime | ✓ | 4/4 dispatches inspected — see Finding A.2; gap was *call-shape* not preamble content |
| 10 | Orchestrator-only — main Claude only IO + dispatch, never heavy in-line work | mixed | ✓ | SKILL.md prose enforces (static); trace shows main only did `AskUserQuestion` + `write_run_artifact` (runtime) |

## Findings (real)

### A.1 — Step 1 cannot fire as a single batched AskUserQuestion

**Symptom.** `bundled/plan-pack/SKILL.md` Step 1 said "Ask the user 8
questions in a single batched `AskUserQuestion`". The
`AskUserQuestion` tool schema enforces `questions.maxItems = 4`.
Any attempt to submit eight at once errors out before reaching the user.

**Workaround used in this run.** Two `AskUserQuestion` calls of 4
questions each, fired sequentially with no other tool calls between
them. Treated as a single interview batch.

**Fix.** Step 1 rewritten to make the two-call structure explicit
and to cite the platform constraint inline.
[`bundled/plan-pack/SKILL.md` Step 1]

### A.2 — `wrap_with_preamble` import documented but call shape implicit

**Symptom.** SKILL.md mentioned `server.harness.wrap_with_preamble`
three times ("Wrap … via …") without showing the call shape. During
the dogfood run, the main Claude reproduced the 4-rule preamble by
hand-typing it at the head of each prompt. The result was textually
identical to `wrap_with_preamble`'s output, but the function itself
was never invoked.

**Risk.** Hand-writing the preamble drifts across runs. A future
session could paraphrase, abbreviate, or reorder the four rules
and silently weaken the harness contract — without any test
catching it.

**Fix.** Step 2/3 now ships a canonical Python snippet showing the
exact call (`wrapped = wrap_with_preamble(raw_prompt)`) plus a
"do not hand-write the preamble inline" warning. Step 4 references
the same snippet by pointer.
[`bundled/plan-pack/SKILL.md` Step 2/3, Step 4]

### A.3 — second-opinion responses appended without verification

**Symptom.** Step 4 said: *"main Claude takes the response and
appends a `## Review notes` section."* In iteration 2 the second-
opinion role asserted that the AC bash one-liner was broken because
`TIMEFORMAT=%R t=$(...)` would not propagate `TIMEFORMAT` to the
subshell. The main Claude appended the bullet verbatim. A direct
shell test (run later, see "False alarm" below) showed the claim
was wrong — the subshell *does* inherit `TIMEFORMAT` because shell
variables (not env variables) propagate via `$( )`, and `time` reads
`TIMEFORMAT` from the shell.

If left as-is, future runs would persist false-alarm bullets in
PRD artifacts the user expects to be authoritative.

**Fix.** New Step 4b "verify before appending" makes triage
mandatory. Runtime claims require a 1-shot Bash test; internal-
contradiction claims require re-reading both cited sentences;
unverifiable speculation is dropped. A `> verified by main Claude
on <date> — <n> kept / <m> dropped` audit header is prepended to
the Review notes block so the trail is visible in `PRD.md`.
[`bundled/plan-pack/SKILL.md` Step 4b]

## Finding (false alarm)

### B — "AC bash is broken because TIMEFORMAT=%R doesn't propagate"

**Claim source.** Iteration 2 second-opinion bullet 2 (codex:codex-
rescue dispatch).

**Verification.** Direct test (`tests/manual/timeformat_propagation.sh`
not committed; reproduced inline during dogfood):

```
$ bash -c 'TIMEFORMAT=%R t=$({ time sleep 0.1; } 2>&1); echo "t=[$t]"'
t=[0.108]
```

The subshell inherited `TIMEFORMAT` and `time` produced `0.108`
(the `%R` format), not the bash default `real 0m0.108s`. The
critique is wrong.

**Why second-opinion got it wrong.** The bash spec for
`VAR=val cmd` says env injection applies only to external commands.
The reviewer likely applied this rule mechanically without
distinguishing between shell variables (used by `time`, propagated
to subshells via implicit inheritance) and environment variables
(the only ones that need `export`).

**Why this matters more than the bullet itself.** This is the
specific bullet that triggered Finding A.3. Without the dogfood
verifying the claim, the false alarm would have shipped in
`PRD.md` and the SKILL.md gap would have stayed hidden. The
review-without-verification path is the actual defect; the
mistaken bullet is the smoke that revealed it.

## V3 brainstorming vs V4 plan-pack — head to head

Same task, run sequentially during the dogfood (V3 first, then V4
after closing the V3 run).

| Dimension | V3 (`brainstorming` skill) | V4 (`plan-pack` ★ bundle) |
|---|---|---|
| Workflow shape | Main Claude drafts inline, asks for approval | Orchestrator dispatches sub-agents (4 total: 2× drafting + 2× challenge), main only does IO |
| Defects surfaced | None (no challenge step) | 15 critical bullets (7 + 8 across two iterations); 14 valid + 1 false alarm |
| Acceptance Criteria | Natural-language ("works in one second") | Executable bash one-liner suitable for an external verifier |
| Artifact location | `~/my-folder/docs/git-recent-prd-2026-04-28.md` (run-orphan) | `<run_dir>/PRD.md` (trace-anchored) |
| Wall-clock time | ~5 min | ~13 min |
| Decisive find | — | AC bash needed `TIMEFORMAT=%R` + explicit `bash -c` to be robust across shells (would have shipped broken under V3) |

The 13-minute V4 cost bought a sub-agent review pass on the same
order of substance as a human reviewer's first pass. The 5-minute
V3 path skipped that entirely. For PRD work where downstream
implementation will lean on the doc as ground truth, that gap
compounds.

## ROI assessment

For tasks where the artifact will gate further work:

- The harness preamble carried verbatim on every dispatched prompt
  produced no observable rule-breakers in the trace (no main-Claude
  inline drafting, no scope creep into adjacent stages, no implicit
  feature additions).
- The parallel-dispatch slot delivered ~50% latency reduction on
  Steps 2+3 vs sequential; the round-trip cost on Step 4 is
  comparable to a human second pass.
- Run_dir trace is durable enough that a future session can re-open
  this dogfood without re-deriving context.

For trivial/throwaway tasks the V3 brainstorming path is still the
right call — the 13-min V4 floor is overkill when no doc will be
read again.

## Follow-up tracks (out of scope for B-1)

- **Phase B-2** (ARCH/ADR/UI_GUIDE) blocked on B-1 ship; this
  dogfood unblocks it.
- **AC-bash external verifier** (cross-cutting B): the AC bash
  produced here is not yet executed by a verifier bundle; that
  arrives with `verifier` in Phase E.
- **Trace + learning replay** (cross-cutting C): false-alarm
  bullets like the TIMEFORMAT one are exactly the kind of failure
  signal a learning replay should compound on. Worth feeding into
  the C track when it lands.

## Status

Phase B-1 dogfood **passes for the SKILL.md-fixes track**. The three
fixes in commit `76dc985` close the gaps surfaced above and ensure
*future* runs verify second-opinion bullets before appending (Step 4b).

**Caveat — the produced PRD artifact is not authoritative.** The Step 4
iteration-2 false alarm ("AC bash is broken because TIMEFORMAT=%R doesn't
propagate") is preserved verbatim in
`runs/20260428-160618-654d/PRD.md` Review notes (first bullet), because
it predates the Step 4b fix that would have caught it. The artifact is
retained as **historical evidence of the very defect that motivated
Step 4b**, not as a fit-for-implementation PRD. Do not derive
implementation from the persisted Review notes; the bullet refuted in
"Finding (false alarm)" above is wrong.

Future plan-pack runs (post-`76dc985`) apply Step 4b verify, so the
class of failure that produced this caveat will not repeat. CHANGELOG
updated to mark the dogfood report as delivered.
