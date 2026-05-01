# debugger Step 7 — iteration revisit (orchestrator helper)
This file is **orchestrator-facing** — main constructs per-step
revisit prompts before re-dispatching Step 3 or Step 4. The substituted
prompt is sent through the regular Step 3 / Step 4 sub-agent flow
(NOT loaded as a Step 7 sub-agent — there is no Step 7 sub-agent).

## Inputs

- run_id: `{{RUN_ID}}`
- revisit_target: `{{REVISIT_TARGET}}` (one of `step3` or `step4`)
- failure_summary: `{{FAILURE_SUMMARY}}` (1-2 sentences — what went
  wrong with the previous fix attempt; carried over to the re-entry
  prompt)
- existing_report: `{{EXISTING_REPORT}}` (current BUG_REPORT.md verbatim)

## Substitution behavior

Main reads this file via `dispatch_prompt("iter_revisit.md")`, then:

1. Substitutes `{{RUN_ID}}`, `{{REVISIT_TARGET}}`, `{{FAILURE_SUMMARY}}`,
   `{{EXISTING_REPORT}}` into the body below.
2. Wraps the result as the prompt body of either Step 3 or Step 4
   (matching `revisit_target`). Specifically, the produced text is
   prepended to the `hypothesis_step3.md` or `root_cause_step4.md`
   prompt body as a `## Revisit context` section.
3. Records `dispatch_and_record(... step="step7.iter{N}.{TARGET}",
   note="revisit: {failure_summary}", description="iter revisit
   targeting {REVISIT_TARGET}")` before sending to the Agent tool.

## Body (substituted into the target step prompt)

```markdown
## Revisit context (Spike IV §2.10 iteration)

The fix proposed by Step 5 in iteration N-1 did not hold. Reason:

> {{FAILURE_SUMMARY}}

You are now re-entering the workflow at `{{REVISIT_TARGET}}`. The
existing `BUG_REPORT.md` is provided in full below — keep all
already-filled sections verbatim. Only the section owned by your step
(`## Hypotheses` for step3, `## Root cause` for step4) and any
downstream sections may change.

Existing BUG_REPORT.md:
```
{{EXISTING_REPORT}}
```

Continue with your normal step contract from here.
```
