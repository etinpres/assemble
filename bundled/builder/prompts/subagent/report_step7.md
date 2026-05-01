# builder Step 7 — commit message + IMPL_REPORT finish
You are dispatched as builder Step 7 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Inputs

- run_id: `{{RUN_ID}}`

## Goal

Read full IMPL_REPORT.md. Validate all sections complete. Add `## Commit message` + `## TL;DR`. Flip `status: complete`.

## Section validation

Check all body sections are filled (no `<TBD:` remaining):
- `## Test (red)` — Step 3
- `## Implementation` — Steps 4/5
- `## Verify (green)` — Step 5
- `## Self-review` — Step 6

If any `<TBD:` found in a section body: print `ERROR: IMPL_REPORT has unfilled sections — <section name>` and exit.

## Commit message format

Conventional commit:
```
<type>(<scope>): <subject>

<optional body — 1-3 lines>
```
Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.

## Final step (canonical save block — DO NOT MODIFY THE STRUCTURE)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact, read_run_artifact

rid = "{{RUN_ID}}"
existing = read_run_artifact(rid, "IMPL_REPORT.md")

# Validate — no <TBD: in body sections
tbd_sections = re.findall(r"^## ([^\n]+)\n[^#]*?<TBD:", existing, re.MULTILINE | re.DOTALL)
if tbd_sections:
    print(f"ERROR: IMPL_REPORT has unfilled sections — {tbd_sections}")
    sys.exit(1)

commit_message = """<TBD: conventional commit — type(scope): subject>"""
tldr = """<TBD: 2-line summary of what was built and how it was verified>"""

new_text = (
    existing
    .replace("<TBD: filled by Step 7 sub-agent — conventional commit format>", commit_message)
    .replace("<TBD: filled by Step 7 sub-agent — 2-line summary>", tldr)
    .replace("status: in-progress", "status: complete")
)
path = write_run_artifact(rid, "IMPL_REPORT.md", new_text)
print(f"WROTE: {path}")
```
