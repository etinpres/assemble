# debugger Step 3 — hypotheses + bisect plan
You are dispatched as debugger Step 3 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Inputs

- run_id: `{{RUN_ID}}`
- existing_report: `{{EXISTING_REPORT}}` (current `BUG_REPORT.md` text;
  must contain filled `## Symptom` and `## Reproducer` sections)

## Goal

Read `BUG_REPORT.md ## Symptom` + `## Reproducer`. Produce 3-5 ranked
hypotheses for the root cause. Each hypothesis carries:

- 1-line claim (one sentence — what is broken and where)
- bisect step (specific file, function, line range, or commit to inspect)
- expected evidence (what you would see on disk / in logs / in git
  history if this hypothesis is true)

Append the `## Hypotheses` section to `BUG_REPORT.md` (between existing
`## Reproducer` and the `<TBD: …>` `## Root cause` section).

## Constraints

- Minimum 3 hypotheses, maximum 5. (Spike II gate B3.2-style minSelected.)
- Rank by evidence-richness — most testable hypothesis first.
- Each hypothesis must be falsifiable. "Could be a race condition" is
  not enough; "verify that `Foo.bar()` holds the lock across the
  await on line 42" is.
- Do NOT propose fixes. Step 5 owns fixes.
- Do NOT inspect infrastructure code outside the bug surface (rule 7).

## Anti-patterns (do not do)

- Vague speculation ("maybe the cache is stale", "could be a TLS issue").
- Hypotheses that overlap (3 variants of "the import is wrong").
- Single-hypothesis output (you must produce ≥3).

## Final step (canonical save block — DO NOT MODIFY THE STRUCTURE)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact, read_run_artifact

rid = "{{RUN_ID}}"
existing = read_run_artifact(rid, "BUG_REPORT.md")

hypotheses_body = """<TBD: 3-5 hypotheses, each as numbered subsection
1. **Claim**: <1-line>
   - bisect: <file:line | commit | function>
   - expected evidence if true: <what to look for>

Repeat 3-5 times. Use markdown subheadings (### 1., ### 2., …) inside
the ## Hypotheses block.>"""

# Replace the <TBD: …> placeholder for ## Hypotheses
sentinel = "<TBD: filled by Step 3 sub-agent — 3-5 ranked hypotheses, each with bisect step + expected evidence>"
if sentinel not in existing:
    print("ERROR: BUG_REPORT.md ## Hypotheses sentinel missing — Step 2 may not have run")
    sys.exit(1)
new_text = existing.replace(sentinel, hypotheses_body)

path = write_run_artifact(rid, "BUG_REPORT.md", new_text)
print(f"WROTE: {path}")
```
