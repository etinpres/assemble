# Task — PRD body 작성 + PRD.md write

You are dispatched as plan-pack Step 2 (PRD body sub-agent). Goal: produce a PRD body for the user task and write `<run_dir>/PRD.md`. Return only the file path.

## Inputs (substituted by orchestrator)

- run_id: `{{RUN_ID}}`
- task: `{{TASK}}`
- interview_answers (Q1–Q8 from Step 1): `{{INTERVIEW_ANSWERS}}`

## Required body sections

PRD body must contain these `## ` sections in order:
1. `## Goal` (Q1 + one-line success criterion from Q5)
2. `## Users` (Q2)
3. `## Core features` (Q3, 3 bullets)
4. `## Excluded from MVP` (Q4 — explicit harness rule #2 enforcement)
5. `## Design direction` (Q7 — seed for UI_GUIDE)
6. `## Risks` (Q8)
7. `## Acceptance criteria` (placeholder block — actual bash command filled by Step 3 sub-agent)

## Final step (canonical save block — DO NOT MODIFY THE STRUCTURE)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact

rid = "{{RUN_ID}}"
task = """{{TASK}}"""

# Build PRD body sections from interview answers above
body = """## Goal
...
## Users
...
## Core features
...
## Excluded from MVP
...
## Design direction
...
## Risks
...
## Acceptance criteria
{{AC_BASH_PLACEHOLDER}}
"""

# Load + fill template
template_path = Path.home() / ".claude/skills/assemble/bundled/plan-pack/templates/PRD.md.template"
filled = template_path.read_text().replace("{{TASK}}", task).replace("{{PRD_BODY}}", body)

path = write_run_artifact(rid, "PRD.md", filled)
print(f"WROTE: {path}")
```

If the write fails, print `ERROR: <reason>` to stdout instead of `WROTE:` and exit. Do not attempt fallback writes.
