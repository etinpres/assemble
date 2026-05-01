# builder Step 6 — self-review diff vs SCOPE
You are dispatched as builder Step 6 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Inputs

- run_id: `{{RUN_ID}}`
- scope_content: `{{SCOPE_CONTENT}}`
- existing_report: `{{EXISTING_REPORT}}`

## Goal

Compare `git diff` against SCOPE.md Allow list and Deny list. Append `## Self-review` to IMPL_REPORT.md.

1. Run `git diff HEAD` (or `git diff HEAD~1 HEAD` if already committed).
2. Parse changed file paths from diff output.
3. Compare against `## Allow list` and `## Deny list` from `{{SCOPE_CONTENT}}`.
4. Report deviation count and recommendation.

## Self-review section format

```markdown
**Scope check**:
- Changed files: <list>
- Allow-list hits: <N>/<total> files in allow-list
- Deny-list violations: <N> (0 = clean)
- Off-allow-list changes: <N> (0 = clean)

**Harness rule 3 (Surgical Changes)**:
- Unrelated reformats: <yes/no>
- Added features beyond task breakdown: <yes/no>

**Recommendation**: merge-ready / needs fix (<reason if needs fix>)
```

## Constraints

- Report violations factually. Do NOT auto-fix them — Step 4 re-run owns fixes.
- If `git diff HEAD` is empty, use `git diff HEAD~1 HEAD`.

## Final step (canonical save block — DO NOT MODIFY THE STRUCTURE)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact, read_run_artifact

rid = "{{RUN_ID}}"
existing = read_run_artifact(rid, "IMPL_REPORT.md")

review_body = """<TBD: structured self-review as per ## Self-review section format above>"""
sentinel = "<TBD: filled by Step 6 sub-agent — scope deviation count + recommendation>"
if sentinel not in existing:
    print("ERROR: IMPL_REPORT.md ## Self-review sentinel missing")
    sys.exit(1)
new_text = existing.replace(sentinel, review_body)
path = write_run_artifact(rid, "IMPL_REPORT.md", new_text)
print(f"WROTE: {path}")
```
