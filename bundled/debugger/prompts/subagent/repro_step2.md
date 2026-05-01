# debugger Step 2 — reproducer construction
You are dispatched as debugger Step 2 sub-agent. Print `WROTE: <absolute path>`
on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.


## Inputs

- run_id: `{{RUN_ID}}`
- symptom_summary: `{{SYMPTOM_SUMMARY}}` (1-line)
- env: `{{ENV}}` (OS / runtime / dependency versions)
- last_known_good: `{{LAST_KNOWN_GOOD}}` (commit / version, or "모름")
- tried_fixes: `{{TRIED_FIXES}}` (list, or "없음")

## Goal

Build the minimal `bash repro.sh` command that reproduces the symptom on
a clean checkout. Then write:

1. `runs/{{RUN_ID}}/repro.sh` from `templates/repro.sh.template`,
   substituting `{{RUN_ID}}`, `{{SYMPTOM_SUMMARY}}`, and
   `{{REPRO_COMMAND}}` (the command itself).
2. `runs/{{RUN_ID}}/BUG_REPORT.md` from `templates/BUG_REPORT.md.template`,
   substituting `{{RUN_ID}}`, `{{STARTED_AT}}` (ISO8601 UTC),
   `{{SYMPTOM_SUMMARY}}`, and filling the `## Reproducer` section.
   Other sections stay as `<TBD: …>`.

## Constraints (harness rule 4)

- Run `bash runs/{{RUN_ID}}/repro.sh` after writing it. Confirm the
  exit code is non-zero (the bug must reproduce). Record the observed
  exit code and the first 3 lines of stderr in the `## Reproducer`
  section.
- Do NOT propose fixes. Step 5 owns fixes.
- Do NOT inspect infrastructure code outside the bug surface (rule 7).

## Anti-patterns (do not do)

- Multi-step setup that requires manual intervention. Reproducer must
  be one `bash repro.sh` invocation.
- Reproducer that depends on hidden state ("run after deleting cache").
  If a precondition is required, it goes inside `repro.sh` as the first
  line.
- Non-bash runtimes (dart, python, node) with heredoc stdin syntax.
  Use `dart run <file>` or write a temp script file instead of `dart - <<EOF`.
  Heredoc stdin piping exits non-zero on many runtimes even on success.

## Final step (canonical save block — DO NOT MODIFY THE STRUCTURE)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
import subprocess
import datetime
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact, run_artifact_path

rid = "{{RUN_ID}}"
symptom = """<TBD: 1-line symptom summary, copy from {{SYMPTOM_SUMMARY}}>"""
started_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

# 1. repro.sh
repro_template = (Path.home() / ".claude/skills/assemble/bundled/debugger/templates/repro.sh.template").read_text()
repro_command = """<TBD: minimal one-or-multi-line bash that triggers the bug>"""
repro = (
    repro_template
    .replace("{{RUN_ID}}", rid)
    .replace("{{SYMPTOM_SUMMARY}}", symptom)
    .replace("{{REPRO_COMMAND}}", repro_command)
)
repro_path = write_run_artifact(rid, "repro.sh", repro)

# 2. Run repro to confirm failure
result = subprocess.run(
    ["bash", str(repro_path)],
    capture_output=True,
    text=True,
    timeout=60,
)
exit_code = result.returncode
stderr_head = "\n".join(result.stderr.splitlines()[:3])

# 3. BUG_REPORT.md
report_template = (Path.home() / ".claude/skills/assemble/bundled/debugger/templates/BUG_REPORT.md.template").read_text()
reproducer_body = f"""```bash
$ bash repro.sh
```
Exit code: {exit_code}
First 3 lines of stderr:
```
{stderr_head}
```
Reproducer file: `repro.sh` (written by Step 2 sub-agent)."""
report = (
    report_template
    .replace("{{RUN_ID}}", rid)
    .replace("{{STARTED_AT}}", started_at)
    .replace("{{SYMPTOM_SUMMARY}}", symptom)
    .replace("<TBD: filled by Step 2 sub-agent — minimal `bash repro.sh` command + observed failure exit code>", reproducer_body)
)
report_path = write_run_artifact(rid, "BUG_REPORT.md", report)

print(f"WROTE: {report_path}")
```

If the reproducer succeeds (exit code 0), print
`ERROR: reproducer did not fail — symptom not reproducible from {{ENV}}`
and exit. Do NOT write `BUG_REPORT.md` in that case.
