# Task — 4-way cross-doc review + ADR.md ## Cross-doc review 추가

You are dispatched as plan-pack Step 9 (cross-doc sub-agent). Goal: read all 4 docs, produce verified findings under 7 categories, append (or suffix) `## Cross-doc review` section to ADR.md. Return file path.

## Inputs

- run_id: `{{RUN_ID}}`
- iteration_count: `{{ITERATION_COUNT}}` (0 for first-pass; ≥1 for iterations)

## Required 7 finding categories (full list — see spec §3 Step 9 for prompts)

1. PRD ↔ ARCH (gap detection)
2. ARCH ↔ ADR (decision integrity)
3. PRD ↔ ADR (motivation traceability)
4. PRD ↔ UI_GUIDE (design direction audit; antipattern violations = CRITICAL)
5. ARCH ↔ UI_GUIDE (component coverage)
6. ADR ↔ UI_GUIDE (UX decision integrity)
7. Numerical / unit consistency cross-doc

## Triage protocol

Apply Step 4b protocol — verify runtime claims with 1-shot Bash, drop speculation. Track `n_kept` / `n_dropped`. Compute `RESOLVED` / `UNRESOLVED` / `NEW` counts (used by orchestrator's iteration_state.json).

## Output (stdout — exact form)

Print exactly two lines, in this order:

```
WROTE: <absolute-path-to-ADR.md>
COUNTS: resolved=<int> unresolved=<int> new=<int>
```

The COUNTS line schema is verbatim — **no extra keys, no different keys**:
- ✗ `COUNTS: NEW=10 WARN=3 INFO=6 CRITICAL=0` (B-6 dogfood iteration 0 — wrong)
- ✗ `COUNTS: resolved=8 unresolved=1` (missing `new`)
- ✓ `COUNTS: resolved=8 unresolved=1 new=0`

`resolved` = findings from prior Cross-doc review now closed by this iteration's edits.
`unresolved` = findings from prior review still open.
`new` = findings introduced this iteration (regression — should trend to 0).
First-pass (`iteration_count == 0`): all findings are NEW, but report them as `new=<count>` with `resolved=0 unresolved=0`. Do NOT use other keys.

## Final step (canonical save block)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
from pathlib import Path
from datetime import date
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact, read_run_artifact

rid = "{{RUN_ID}}"
iteration_count = int("{{ITERATION_COUNT}}")

# read 4 docs
prd_text = read_run_artifact(rid, "PRD.md") or ""
arch_text = read_run_artifact(rid, "ARCHITECTURE.md") or ""
adr_text = read_run_artifact(rid, "ADR.md") or ""
ui_text = read_run_artifact(rid, "UI_GUIDE.md") or ""

# (compute findings, triage, build bullets — sub-agent fills)
n_kept = ...
n_dropped = ...
n_resolved = ...
n_new = ...
n_unresolved = ...
bullets = """
- <TBD: 1 verified finding, prefixed with category tag — `[PRD↔ARCH]`, `[ARCH↔ADR]`, `[PRD↔ADR]`, `[PRD↔UI]`, `[ARCH↔UI]`, `[ADR↔UI]`, or `[NUMERIC]` — describing the gap/violation/inconsistency and a 1-line remediation pointer>
""".strip()

audit = f"> 4-way cross-doc verified on {date.today().isoformat()} — {n_kept} kept / {n_dropped} dropped"
counts_line = f"> counts — RESOLVED: {n_resolved}, UNRESOLVED: {n_unresolved}, NEW: {n_new}"
heading = "## Cross-doc review" if iteration_count == 0 else f"## Cross-doc review (iteration {iteration_count})"

# Pre-condition check (spec §3 Step 9 assert)
assert heading not in adr_text, (
    f"contract violation: heading {heading!r} already in ADR.md; "
    "Step 11 should have overwritten the file from scratch"
)

new_text = adr_text + "\n\n" + heading + "\n\n" + audit + "\n" + counts_line + "\n\n" + bullets + "\n"
path = write_run_artifact(rid, "ADR.md", new_text)
print(f"WROTE: {path}")
print(f"COUNTS: resolved={n_resolved} unresolved={n_unresolved} new={n_new}")
```

The `COUNTS:` line is parsed by orchestrator for `iteration_state.json` update.

If write fails, print `ERROR: <reason>` and exit. No fallback writes.
