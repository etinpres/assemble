# builder Step 8 — iteration revisit helper
This file is loaded by main Claude to construct a re-entry prompt for Step 2 or Step 4. Main reads this file, substitutes tokens, then prepends the result to the target step's dispatch prompt.

## Inputs (substituted by main before prepend)

- `{{RUN_ID}}` — active run
- `{{REVISIT_TARGET}}` — `step2` or `step4`
- `{{FAILURE_SUMMARY}}` — what failed or what new work is needed
- `{{EXISTING_REPORT}}` — current IMPL_REPORT.md text

## Output (prepended to target step prompt)

```
[ITERATION REVISIT — Step 8 re-entry for {{REVISIT_TARGET}}]
Previous attempt notes: {{FAILURE_SUMMARY}}
Existing IMPL_REPORT:
---
{{EXISTING_REPORT}}
---
Continue from {{REVISIT_TARGET}} with the above context. Do not repeat work already marked complete in IMPL_REPORT.md.
```
