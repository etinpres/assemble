# Task — PRD second-opinion review + ## Review notes 섹션 추가

You are dispatched as plan-pack Step 4 (PRD consistency review sub-agent). Goal: read `<run_dir>/PRD.md`, produce verified critique, append `## Review notes` section with audit header, return file path.

## Inputs

- run_id: `{{RUN_ID}}`

## Required behavior

1. Load PRD: `prd = read_run_artifact("{{RUN_ID}}", "PRD.md")`.
2. Identify potential flaws, missing constraints, tradeoffs not yet acknowledged. Never bare agreement.
3. **Triage** each candidate bullet (Step 4b protocol from spec):
   - Runtime claim (e.g. "this bash one-liner doesn't work") → run a 1-shot Bash test, capture stdout/exit, keep/drop/rewrite.
   - PRD internal contradiction → re-read both cited sentences, confirm.
   - Drop unverifiable speculation.
4. Track `n_kept` and `n_dropped`.

## Final step (canonical save block)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
from pathlib import Path
from datetime import date
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact, read_run_artifact

rid = "{{RUN_ID}}"
current = read_run_artifact(rid, "PRD.md") or ""

n_kept = ...    # int
n_dropped = ... # int
audit = f"> verified by sub-agent on {date.today().isoformat()} — {n_kept} kept / {n_dropped} dropped"
bullets = """
- ...
- ...
""".strip()
section = f"\n\n## Review notes\n\n{audit}\n\n{bullets}\n"

new_text = current + section
path = write_run_artifact(rid, "PRD.md", new_text)
print(f"WROTE: {path}")
```

If write fails, print `ERROR: <reason>` and exit. No fallback writes.
