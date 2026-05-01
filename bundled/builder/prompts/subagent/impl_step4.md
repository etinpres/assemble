# builder Step 4 — implementation
You are dispatched as builder Step 4 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Inputs

- run_id: `{{RUN_ID}}`
- scope_content: `{{SCOPE_CONTENT}}`
- existing_report: `{{EXISTING_REPORT}}` (IMPL_REPORT.md, must contain `## Test (red)`)

## Goal

Implement the feature described in `## Task breakdown` of `{{SCOPE_CONTENT}}`.

1. Work through each sub-task in `## Task breakdown` in order.
2. Edit/Write source files — stay within `## Allow list` only.
3. Append `## Implementation` section draft to IMPL_REPORT.md.
4. Do NOT run tests. Step 5 owns verification.

## Constraints (harness rule 3 — Surgical Changes)

- Edit ONLY files listed in `## Allow list` of SCOPE.md. Any edit outside triggers:
  `ERROR: scope creep — patch touches <file> not in allow-list`
- Do NOT reformat/reflow code outside the patch surface.
- Do NOT add error handling for cases not in `## Task breakdown`.
- Do NOT run tests — Step 5 owns verification.

## Anti-patterns (do not do)

- Refactoring surrounding code "while you're here".
- Adding new files not in allow-list without surfacing to user first.
- Implementing beyond what `## Task breakdown` specifies (YAGNI).
- Running the test suite to confirm your work (Step 5's job).

## Final step (canonical save block — DO NOT MODIFY THE STRUCTURE)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact, read_run_artifact

rid = "{{RUN_ID}}"
existing = read_run_artifact(rid, "IMPL_REPORT.md")

patch_summary = """<TBD: list of file:line + 1-2 sentence rationale per change>"""
files_changed = """<TBD: list of changed files>"""
impl_body = f"""**Patch summary**:
{patch_summary}

**Files changed**: {files_changed}"""

sentinel = "<TBD: filled by Step 4/5 sub-agent — task breakdown execution + patch summary (file:line + 1-2 sentence rationale)>"
if sentinel not in existing:
    print("ERROR: IMPL_REPORT.md ## Implementation sentinel missing — Step 3 may not have run")
    sys.exit(1)
new_text = existing.replace(sentinel, impl_body)
path = write_run_artifact(rid, "IMPL_REPORT.md", new_text)
print(f"WROTE: {path}")
```
