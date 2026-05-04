# builder Step 2 — SCOPE + task decomposition
You are dispatched as builder Step 2 sub-agent. Print `WROTE: <absolute path>`
on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Inputs

- run_id: `{{RUN_ID}}`
- task_summary: `{{TASK_SUMMARY}}`
- known_files: `{{KNOWN_FILES}}`
- test_cmd: `{{TEST_CMD}}`
- ac_cmd: `{{AC_CMD}}`

## Goal

Write two artifacts under `{{RUN_DIR}}/`:

1. `SCOPE.md` — scope contract for this implementation task.
2. `IMPL_REPORT.md` — skeleton from template with front-matter filled; body sections as `<TBD: filled by Step N>`.

## SCOPE.md constraints

- `## Allow list`: files/functions/modules you may change. If `{{KNOWN_FILES}}` is '모름', explore the codebase first before writing.
- `## Deny list`: MUST include infrastructure dirs (`bundled/_shared/`, `server/`) unless the task is infrastructure-level. Never empty.
- `## Completion criterion`: one bash one-liner that exits 0 when done. Use `{{AC_CMD}}` if provided; derive from `{{TEST_CMD}}`; else write a `grep`/`stat` check. No "verify manually".
- `## Task breakdown`: numbered sub-tasks, each ≤ 1 function/file scope, in implementation order.

## Constraints

- Allow list MUST NOT be empty — explore to identify candidates if `{{KNOWN_FILES}}` is '모름'.
- Completion criterion MUST be a bash one-liner.
- Deny list MUST NOT be empty.

## Anti-patterns (do not do)

- Allow-list so broad it includes an entire directory tree.
- Completion criterion that requires human judgement ("looks good").
- Non-bash runtimes (dart, python, node) with heredoc stdin syntax in completion criterion — use `dart run <file>` or temp file pattern.

## Final step (canonical save block — DO NOT MODIFY THE STRUCTURE)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
import datetime
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact

rid = "{{RUN_ID}}"
task_summary = """<TBD: copy from {{TASK_SUMMARY}}>"""
started_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

# 1. SCOPE.md
scope_template = (Path.home() / ".claude/skills/assemble/bundled/builder/templates/SCOPE.md.template").read_text()
allow_list = """<TBD: bulleted list of files/functions to change>"""
deny_list = """<TBD: bulleted list of files/patterns off-limits>"""
completion_criterion = """<TBD: one bash command that exits 0 when done>"""
task_breakdown = """<TBD: numbered sub-tasks, each ≤ 1 file/function>"""
scope = (
    scope_template
    .replace("{{TASK_SUMMARY}}", task_summary)
    .replace("{{ALLOW_LIST}}", allow_list)
    .replace("{{DENY_LIST}}", deny_list)
    .replace("{{COMPLETION_CRITERION}}", completion_criterion)
    .replace("{{TASK_BREAKDOWN}}", task_breakdown)
)
scope_path = write_run_artifact(rid, "SCOPE.md", scope)

# 2. IMPL_REPORT.md skeleton
report_template = (Path.home() / ".claude/skills/assemble/bundled/builder/templates/IMPL_REPORT.md.template").read_text()
report = (
    report_template
    .replace("{{RUN_ID}}", rid)
    .replace("{{STARTED_AT}}", started_at)
    .replace("{{TASK_SUMMARY}}", task_summary)
)
report_path = write_run_artifact(rid, "IMPL_REPORT.md", report)

print(f"WROTE: {report_path}")
```
