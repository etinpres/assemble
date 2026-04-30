# Task — PRD body 작성 + PRD.md write

You are dispatched as plan-pack Step 2 (PRD body sub-agent). Goal: produce a PRD body for the user task and write `<run_dir>/PRD.md`. Print `WROTE: <absolute path>` on stdout — main parses with regex `^WROTE: (.+)$`. No other prose.

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

# Build each PRD section as its own variable from interview answers above.
# Replace every <TBD: ...> sentinel with the actual content before writing.
goal = """<TBD: 1-paragraph success-framed goal from Q1 + Q5 success criterion>"""
users = """<TBD: 1-paragraph user description from Q2>"""
core_features = """<TBD: 3 bullets, one per Q3 feature>"""
mvp_excluded = """<TBD: 3 bullets, one per Q4 exclusion (harness rule #2)>"""
design_direction = """<TBD: 1-paragraph design direction from Q7 — seed for UI_GUIDE>"""
risks = """<TBD: 1 paragraph naming the Q8 risk and one mitigation question>"""

template_path = Path.home() / ".claude/skills/assemble/bundled/plan-pack/templates/PRD.md.template"
filled = (template_path.read_text()
  .replace("{{TASK}}", task)
  .replace("{{GOAL}}", goal)
  .replace("{{USERS}}", users)
  .replace("{{CORE_FEATURES}}", core_features)
  .replace("{{MVP_EXCLUDED}}", mvp_excluded)
  .replace("{{AC_BASH}}", "{{AC_BASH_PLACEHOLDER}}")
  .replace("{{DESIGN_DIRECTION}}", design_direction)
  .replace("{{RISKS}}", risks))

path = write_run_artifact(rid, "PRD.md", filled)
print(f"WROTE: {path}")
```

If the write fails, print `ERROR: <reason>` to stdout instead of `WROTE:` and exit. Do not attempt fallback writes.
