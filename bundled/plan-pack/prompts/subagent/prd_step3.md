# Task — Acceptance Criteria bash 작성 + PRD.md AC 섹션 갱신

You are dispatched as plan-pack Step 3 (AC bash sub-agent). Goal: produce ONE executable bash one-liner that exits 0 iff the user's success criterion (Q5) is met, then patch `<run_dir>/PRD.md` § Acceptance criteria with the bash. Print `WROTE: <absolute path>` on stdout — main parses with regex `^WROTE: (.+)$`. No other prose.

## Inputs

- run_id: `{{RUN_ID}}`
- success_criterion: `{{SUCCESS_CRITERION}}` (interview Q5)
- ac_request: `{{AC_REQUEST}}` (interview Q6 — externally verifiable command)

## Output

ONE raw bash command, no markdown fences, no `bash` language tag, no surrounding prose. Exit 0 iff success.

Example shape:
- `curl -s localhost:3000/api/x | jq '.status' | grep -q "ok"`

## Final step (canonical save block)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact, read_run_artifact

rid = "{{RUN_ID}}"
ac_bash = """<TBD: ONE bash one-liner — raw command, no fence, no language tag>"""

current = read_run_artifact(rid, "PRD.md") or ""
# PRD.md.template already wraps {{AC_BASH}} in a ```bash ... ``` fence.
# Step 2 substitutes {{AC_BASH}} → {{AC_BASH_PLACEHOLDER}}; Step 3 substitutes
# the placeholder with the raw command (no extra fence).
new_text = current.replace("{{AC_BASH_PLACEHOLDER}}", ac_bash)
path = write_run_artifact(rid, "PRD.md", new_text)
print(f"WROTE: {path}")
```

If write fails, print `ERROR: <reason>` and exit. No fallback writes.
