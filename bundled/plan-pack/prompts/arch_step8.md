# Task — ARCHITECTURE.md draft + write

You are dispatched as plan-pack Step 8 (ARCH sub-agent). Goal: produce ARCH body and write `<run_dir>/ARCHITECTURE.md`. Return file path.

## Inputs

- run_id: `{{RUN_ID}}`
- task: `{{TASK}}`
- arch_interview_answers (A1–A6): `{{INTERVIEW_ANSWERS}}`

## Required sections (each as `## ` heading)

1. `## Stack` (A1)
2. `## Directory tree` (A2)
3. `## Architectural patterns` (A3)
4. `## Data flow` (A4)
5. `## External dependencies` (A5; "none" valid)
6. `## Module boundaries` (A6)

## Final step (canonical save block)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact

rid = "{{RUN_ID}}"
task = """{{TASK}}"""

stack = """..."""
directory_tree = """..."""
patterns = """..."""
data_flow = """..."""
external_deps = """..."""
module_boundaries = """..."""

template = (Path.home() / ".claude/skills/assemble/bundled/plan-pack/templates/ARCHITECTURE.md.template").read_text()
filled = (template
  .replace("{{TASK}}", task)
  .replace("{{STACK}}", stack)
  .replace("{{DIRECTORY_TREE}}", directory_tree)
  .replace("{{PATTERNS}}", patterns)
  .replace("{{DATA_FLOW}}", data_flow)
  .replace("{{EXTERNAL_DEPS}}", external_deps)
  .replace("{{MODULE_BOUNDARIES}}", module_boundaries))

path = write_run_artifact(rid, "ARCHITECTURE.md", filled)
print(f"WROTE: {path}")
```

If write fails, print `ERROR: <reason>` and exit. No fallback writes.
