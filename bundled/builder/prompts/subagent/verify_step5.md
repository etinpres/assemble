# builder Step 5 — verify.sh (green phase) + IMPL_REPORT draft
You are dispatched as builder Step 5 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Inputs

- run_id: `{{RUN_ID}}`
- existing_report: `{{EXISTING_REPORT}}` (must contain `## Implementation`)

## Goal

1. Write `{{RUN_DIR}}/verify.sh` — exits 0 after implementation, non-zero before.
2. Run `bash verify.sh` — confirm exit 0.
3. Fill `## Verify (green)` in IMPL_REPORT.md.

## Constraints (harness rule 4)

- Prefer behavioral verifiers (run the program, check exit/output) over static checks (grep for absence of a string). Static checks are valid only when no runnable entry point exists.
- Run `bash verify.sh` after writing. If exit non-zero: print `ERROR: verifier failed after implementation; rc=<code>` and exit.
- Do NOT reformat/reflow code outside the patch surface (rule 3).

## Anti-patterns (do not do)

- Verifier that checks the wrong thing (file existence instead of behavior).
- Static grep-only verifier when a behavioral check is possible.
- Non-bash runtimes (dart, python, node) with heredoc stdin syntax — use `dart run <file>` or temp file.

## Final step (canonical save block — DO NOT MODIFY THE STRUCTURE)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
import subprocess
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact, read_run_artifact

rid = "{{RUN_ID}}"
existing = read_run_artifact(rid, "IMPL_REPORT.md")
task_summary = """<TBD: copy from ## Task section of existing IMPL_REPORT.md>"""

# 1. verify.sh
verify_template = (Path.home() / ".claude/skills/assemble/bundled/builder/templates/verify.sh.template").read_text()
verify_command = """<TBD: bash command that exits 0 after implementation, non-zero before>"""
verify = (
    verify_template
    .replace("{{RUN_ID}}", rid)
    .replace("{{TASK_SUMMARY}}", task_summary)
    .replace("{{VERIFY_COMMAND}}", verify_command)
)
verify_path = write_run_artifact(rid, "verify.sh", verify)

# 2. Run — confirm exit 0
result = subprocess.run(["bash", str(verify_path)], capture_output=True, text=True, timeout=120)
if result.returncode != 0:
    print(f"ERROR: verifier failed after implementation; rc={result.returncode}")
    print(f"stderr: {result.stderr[:500]}")
    sys.exit(1)

# 3. ## Verify (green)
verify_body = (
    f"```bash\n$ bash verify.sh\n```\n"
    f"Exit code: 0 ✅\nOutput:\n```\n{result.stdout[:300]}\n```\n"
    f"Verifier: `verify.sh` (behavioral check)."
)
sentinel = "<TBD: filled by Step 5 sub-agent — verify.sh exit code + output snippet>"
if sentinel not in existing:
    print("ERROR: IMPL_REPORT.md ## Verify (green) sentinel missing")
    sys.exit(1)
new_text = existing.replace(sentinel, verify_body)
path = write_run_artifact(rid, "IMPL_REPORT.md", new_text)
print(f"WROTE: {path}")
```
