# debugger Step 6 — BUG_REPORT.md integration check
You are dispatched as debugger Step 6 sub-agent (text-summarize persona).
Print `WROTE: <absolute path>` on stdout when done. No other prose.
Main parses with regex `^WROTE: (.+)$`.

## Inputs

- run_id: `{{RUN_ID}}`

## Goal

Read `BUG_REPORT.md`. Validate that all 5 sections exist in order, with
no `<TBD: …>` literals or bare `...` lines remaining (Spike III §C1
contract). If any gap is found, ERROR back to main with the gap source.

If all sections are filled:

- Update front matter `status: ` from `in-progress` to `complete`.
- Add a 1-paragraph executive summary at the top (between front matter
  and `# Bug report — …`), titled `## TL;DR`. The summary names the
  symptom, the root cause in one phrase, and the fix surface in one
  phrase. ≤ 4 sentences.
- Write back via `write_run_artifact`.

## Constraints

- Do NOT alter the body of any existing section. Step 6 only adds the
  front-matter status update + the TL;DR.
- Do NOT add new sections beyond TL;DR.
- Do NOT inspect infrastructure code (rule 7).

## Anti-patterns

- Rewriting hypothesis/root-cause/fix prose for "clarity" — that breaks
  Step 4/5 evidence trails.
- TL;DR longer than 4 sentences.

## Final step (canonical save block — DO NOT MODIFY THE STRUCTURE)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact, read_run_artifact

rid = "{{RUN_ID}}"
existing = read_run_artifact(rid, "BUG_REPORT.md")

# Validate no TBD or bare ... remain
gaps = re.findall(r"<TBD:[^>]*>", existing)
bare_ellipses = re.findall(r"^\s*\.\.\.\s*$", existing, re.MULTILINE)
if gaps:
    print(f"ERROR: BUG_REPORT.md still has unfilled sections: {gaps[:3]}")
    sys.exit(1)
if bare_ellipses:
    print(f"ERROR: BUG_REPORT.md has bare ellipsis lines (Spike III §C1)")
    sys.exit(1)

tldr = """## TL;DR

<TBD: ≤4 sentences. Symptom + root cause + fix surface.>"""

# Insert TL;DR after the front matter (between `---\n` close and `# Bug report`)
parts = existing.split("\n---\n", 1)
if len(parts) != 2:
    print("ERROR: BUG_REPORT.md front matter delimiters not found")
    sys.exit(1)
front, body = parts
front_with_complete = front.replace("status: in-progress", "status: complete")
new_text = front_with_complete + "\n---\n\n" + tldr + "\n\n" + body.lstrip()

path = write_run_artifact(rid, "BUG_REPORT.md", new_text)
print(f"WROTE: {path}")
```
