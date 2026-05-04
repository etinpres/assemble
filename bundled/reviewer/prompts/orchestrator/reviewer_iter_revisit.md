# reviewer iteration round-trip — orchestrator helper

This prompt is loaded by the orchestrator (main Claude) when the user asks for re-review after revising SCOPE.md or fixing the diff.

## Trigger

User says "re-run reviewer" / "review again" / "iter" while a `REVIEW_REPORT.md` exists in the current run dir.

## Steps (orchestrator-only)

1. Read existing `runs/<rid>/REVIEW_REPORT.md`. Extract prior verdict + iteration count from any `## Iteration N` headers (default N=1 if none).
2. Compute `next_iter = N + 1`.
3. Re-dispatch `diff_collect_step2.md` (Step 2) — fresh diff capture.
4. Re-dispatch `classify_files_step3.md` (Step 3).
5. Re-dispatch `rule3_check_step4.md` (Step 4).
6. Re-dispatch `severity_assess_step5.md` (Step 5).
7. Append new section to existing `REVIEW_REPORT.md`:

```
---

## Iteration {next_iter}

**Verdict**: {new verdict}

{new verdict reason}

[Sections 2~7 condensed for this iteration]
```

8. Do NOT overwrite Iteration 1's content. Each iteration is append-only.

## Constraints

- Step 1 (parse_scope) is NOT re-run unless the user explicitly says "SCOPE.md changed".
- dispatches.jsonl rows for iter N use step name `step{N}.iter{N}.<phase>`.
- Maximum 5 iterations per run dir; if user requests more, suggest creating a new run.
