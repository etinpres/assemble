# builder Step 3 — test_first.sh (red phase)
You are dispatched as builder Step 3 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Inputs

- run_id: `{{RUN_ID}}`
- scope_content: `{{SCOPE_CONTENT}}`

## Goal

Write `{{RUN_DIR}}/test_first.sh` that **exits non-zero** before the feature is implemented.

1. Read `## Completion criterion` from `{{SCOPE_CONTENT}}` to understand what "done" looks like.
2. Write the inverse as `test_first.sh` — a command that fails when the feature is absent.
3. Run `bash {{RUN_DIR}}/test_first.sh` — confirm non-zero exit.
4. Fill `## Test (red)` in IMPL_REPORT.md with exit code + stderr head.

## Constraints (harness rule 4)

- Run `bash test_first.sh` after writing. Exit code MUST be non-zero (feature not yet built).
- If exit code is 0 (feature already works): print `ERROR: test already passes — feature may already be implemented` and exit.
- Do NOT begin implementation. Step 4 owns implementation.
- Prefer behavioral commands (run the program, check exit/output) over static file-existence checks.

## Anti-patterns (do not do)

- Writing a test that trivially fails for the wrong reason (file-not-found instead of feature-not-implemented).
- Non-bash runtimes (dart, python, node) with heredoc stdin syntax — use `dart run <file>` or temp file pattern.
- Starting implementation "to confirm the test is meaningful".

## Final step (canonical save block — DO NOT MODIFY THE STRUCTURE)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
import subprocess
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact, read_run_artifact

rid = "{{RUN_ID}}"
task_summary = """<TBD: copy task_summary from IMPL_REPORT.md ## Task section>"""

# 1. test_first.sh
test_template = (Path.home() / ".claude/skills/assemble/bundled/builder/templates/test_first.sh.template").read_text()
test_command = """<TBD: bash command that exits non-zero before feature is built>"""
test_sh = (
    test_template
    .replace("{{RUN_ID}}", rid)
    .replace("{{TASK_SUMMARY}}", task_summary)
    .replace("{{TEST_COMMAND}}", test_command)
)
test_path = write_run_artifact(rid, "test_first.sh", test_sh)

# 2. Run — confirm non-zero exit
result = subprocess.run(["bash", str(test_path)], capture_output=True, text=True, timeout=60)
exit_code = result.returncode
if exit_code == 0:
    print("ERROR: test already passes — feature may already be implemented")
    sys.exit(1)
stderr_head = "\n".join(result.stderr.splitlines()[:3])

# 3. Fill ## Test (red) in IMPL_REPORT.md
existing = read_run_artifact(rid, "IMPL_REPORT.md")
sentinel = "<TBD: filled by Step 3 sub-agent — test_first.sh exit code + command used>"
if sentinel not in existing:
    print("ERROR: IMPL_REPORT.md ## Test (red) sentinel missing — Step 2 may not have run")
    sys.exit(1)
red_body = (
    f"```bash\n$ bash test_first.sh\n```\n"
    f"Exit code: {exit_code} (non-zero — feature not yet implemented)\n"
    f"First 3 lines of stderr:\n```\n{stderr_head}\n```"
)
new_text = existing.replace(sentinel, red_body)
report_path = write_run_artifact(rid, "IMPL_REPORT.md", new_text)

print(f"WROTE: {report_path}")
```
