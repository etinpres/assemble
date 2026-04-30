# Task — UI_GUIDE.md draft + write

You are dispatched as plan-pack Step 13 (UI_GUIDE sub-agent). Goal: produce UI body and write `<run_dir>/UI_GUIDE.md`. Return file path.

## Inputs

- run_id: `{{RUN_ID}}`
- task: `{{TASK}}`
- ui_interview_answers (U1–U6): `{{INTERVIEW_ANSWERS}}`

## Required behavior

Load PRD: `prd_text = read_run_artifact("{{RUN_ID}}", "PRD.md")`. **Extract `## Design direction` section yourself** — slice from `## Design direction` header to next `## ` header.

Required body shape (5 `## ` sections in order):

```
## Visual identity
<one-paragraph aesthetic + bullet "feels like" references>

## Color tokens
<table or bullets — token name, hex, role, optional dark-mode pair>

## Typography
<bullets — family, weights, sizes, line-heights, primary use>

## Component patterns
<one section per Q3 component, ≥3>

## Priority screens
<numbered subsection per Q2 flow, ≥3, each composing components from above>
```

DO NOT emit any antipattern keyword from template's `## Antipatterns to avoid` section: `gradient-text`, `glass morphism`, `backdrop-blur`, `all-purple`, emoji-as-decoration, "Lorem ipsum", "TODO/FIXME", "innovative", "seamless", etc.

## Final step (canonical save block)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact, read_run_artifact

rid = "{{RUN_ID}}"
task = """{{TASK}}"""
prd_text = read_run_artifact(rid, "PRD.md") or ""

# Extract design direction
lines = prd_text.splitlines()
design_direction_lines = []
collecting = False
for line in lines:
    if line.startswith("## Design direction"):
        collecting = True
        continue
    if collecting:
        if line.startswith("## "):
            break
        design_direction_lines.append(line)
design_direction = "\n".join(design_direction_lines).strip() or "(not specified in PRD)"

ui_body = """
## Visual identity
...
## Color tokens
...
## Typography
...
## Component patterns
...
## Priority screens
...
""".strip()

template = (Path.home() / ".claude/skills/assemble/bundled/plan-pack/templates/UI_GUIDE.md.template").read_text()
filled = (template
  .replace("{{TASK}}", task)
  .replace("{{DESIGN_DIRECTION}}", design_direction)
  .replace("{{UI_BODY}}", ui_body))

path = write_run_artifact(rid, "UI_GUIDE.md", filled)
print(f"WROTE: {path}")
```

If write fails, print `ERROR: <reason>` and exit. No fallback writes.
