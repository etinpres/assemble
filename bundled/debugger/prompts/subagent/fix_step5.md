# debugger Step 5 — fix patch + verifier
You are dispatched as debugger Step 5 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Inputs

- run_id: `{{RUN_ID}}`
- existing_report: `{{EXISTING_REPORT}}` (must contain `## Root cause`)

## Goal

Produce three artifacts:

1. `runs/{{RUN_ID}}/verify.sh` from `templates/verify.sh.template`. The
   command must exit 0 once the fix is applied; non-zero before. (This
   is the cross-cutting AC=bash pattern — a real verifier the user can
   run.)
2. The `## Fix & verification` section of `BUG_REPORT.md`:
   - patch summary: list of `file:line` + 1-2 sentence rationale per change
   - verify.sh contents (inline copy)
   - expected output: stdout snippet that proves the fix held
   - the actual code patch as a unified diff (or per-file blocks if
     the change spans multiple languages without a common diff form)

## Constraints (harness rule 3 — Surgical Changes)

- Patch may only touch files cited in `## Hypotheses` bisect steps OR
  `## Root cause` evidence trail. New files outside that surface require
  an `ERROR: scope creep — patch touches <file> not in bisect/root-cause
  citations` exit.
- Run `bash runs/{{RUN_ID}}/verify.sh` after applying the patch. If it
  exits non-zero, write `ERROR: verifier failed after fix application`
  and exit. Do NOT write `## Fix & verification` in that case.
- Do NOT format/reflow code outside the patch surface (rule 3).
- Prefer behavioral verifiers (run the program, check exit/output) over
  static checks (grep for absence of a string). Static checks are valid
  only when no runnable entry point exists.

## Anti-patterns

- Patches that include unrelated cleanups ("while I was here, …").
- Verifier that asserts implementation details rather than the symptom
  (the verifier should fail in the same way the reproducer fails before
  the fix; succeed after).
- Multi-file fix without explaining each file:line in the summary.

## Final step (canonical save block — DO NOT MODIFY THE STRUCTURE)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
import subprocess
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact, read_run_artifact, run_artifact_path

rid = "{{RUN_ID}}"
existing = read_run_artifact(rid, "BUG_REPORT.md")
symptom = """<TBD: copy from existing ## Symptom — used in verify.sh comment header>"""

# 1. verify.sh
verify_template = (Path.home() / ".claude/skills/assemble/bundled/debugger/templates/verify.sh.template").read_text()
verify_command = """<TBD: bash command that exits 0 after fix, non-zero before>"""
verify = (
    verify_template
    .replace("{{RUN_ID}}", rid)
    .replace("{{SYMPTOM_SUMMARY}}", symptom)
    .replace("{{VERIFY_COMMAND}}", verify_command)
)
verify_path = write_run_artifact(rid, "verify.sh", verify)

# 2. Apply patch (sub-agent will have already edited the source files
# via Edit/Write tools BEFORE this save block — the patch lives in the
# source tree, not in this prompt). Confirm by running verify.sh.
result = subprocess.run(
    ["bash", str(verify_path)],
    capture_output=True,
    text=True,
    timeout=120,
)
if result.returncode != 0:
    print(f"ERROR: verifier failed after fix application; rc={result.returncode}")
    print(f"stderr: {result.stderr[:500]}")
    sys.exit(1)

# 3. ## Fix & verification section
fix_body = f"""**Patch summary**:
<TBD: list of file:line + 1-2 sentence rationale per change>

**verify.sh** (`runs/{rid}/verify.sh`):
```bash
{verify_command}
```

**Expected output (post-fix)**:
```
{result.stdout[:500]}
```

**Patch (unified diff)**:
```diff
<TBD: paste git diff or per-file diff here>
```"""

sentinel = "<TBD: filled by Step 5 sub-agent — patch summary (file:line + 1-2 sentence rationale), verify.sh contents, expected output>"
if sentinel not in existing:
    print("ERROR: BUG_REPORT.md ## Fix & verification sentinel missing — Step 4 may not have run")
    sys.exit(1)
new_text = existing.replace(sentinel, fix_body)

path = write_run_artifact(rid, "BUG_REPORT.md", new_text)
print(f"WROTE: {path}")
```
