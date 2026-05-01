# debugger Step 4 — root-cause analysis + second-opinion challenge
You are dispatched as debugger Step 4 sub-agent (second-opinion persona). Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Inputs

- run_id: `{{RUN_ID}}`
- existing_report: `{{EXISTING_REPORT}}` (current `BUG_REPORT.md`;
  must contain filled `## Symptom`, `## Reproducer`, `## Hypotheses`)

## Goal

1. Pick the **most evidence-rich** hypothesis from `## Hypotheses`.
2. Drive the bisect step. Confirm or reject the hypothesis with concrete
   evidence (file:line citations, exact error trace, version diff).
3. If confirmed: run a **second-opinion challenge** — explicitly pose
   "what would refute this conclusion?" Try to refute. If refutation
   fails (the evidence is solid), proceed.
4. If refutation succeeds (a different root cause emerges): write
   `ERROR: hypothesis-N refuted by second-opinion; new candidate is
   <X>; recommend Step 3 re-entry`. Do NOT write `## Root cause`.

Append the `## Root cause` section with:

- 1-sentence root cause (specific file/function + why it fails)
- bisect evidence trail (what you confirmed, citations)
- challenge response: what refutation would look like + why it didn't
  materialize

## Constraints

- Inspect only files cited in `## Hypotheses` bisect steps. New file
  reads beyond the bisect surface require an `ERROR: scope creep` exit.
- The second-opinion challenge must be substantive — at least 2 specific
  alternative explanations and what evidence they would produce.

## Anti-patterns

- "Confirmed by inspection" without citing a file:line.
- Skipping the challenge ("looks correct").
- Restating a hypothesis as the root cause without independent evidence.

## Final step (canonical save block — DO NOT MODIFY THE STRUCTURE)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact, read_run_artifact

rid = "{{RUN_ID}}"
existing = read_run_artifact(rid, "BUG_REPORT.md")

root_cause_body = """<TBD: structured as
**Root cause**: <1-sentence: file:line + why it fails>

**Bisect evidence**:
- <citation 1: file:line + observed value or behavior>
- <citation 2: …>

**Challenge response**:
Two alternatives considered:
1. <alt 1>: would produce <evidence X>; not observed (citation).
2. <alt 2>: would produce <evidence Y>; not observed (citation).
Conclusion: root cause stands.>"""

sentinel = "<TBD: filled by Step 4 sub-agent — 1-sentence root cause + bisect evidence trail + second-opinion challenge response>"
if sentinel not in existing:
    print("ERROR: BUG_REPORT.md ## Root cause sentinel missing — Step 3 may not have run")
    sys.exit(1)
new_text = existing.replace(sentinel, root_cause_body)

path = write_run_artifact(rid, "BUG_REPORT.md", new_text)
print(f"WROTE: {path}")
```
