# verifier ★ — Iteration revisit (orchestrator helper)

> NOTE: This is an orchestrator helper, NOT a subagent prompt. Main Claude reads this directly when re-verification is requested.

## When loaded

User revises `parsed_scope.json` (e.g. amends completion command) or `extracted_completion.json` (rare — manual override) and asks for re-verification.

## Procedure

1. **Read parsed_scope.json change detection**: compute SHA256 of the current `<run_dir>/parsed_scope.json` and compare to the previous iteration's recorded hash (stored in `dispatches.jsonl` under `step1.iter{N-1}.parse.input_hash` if available; otherwise treat as changed).
2. **Determine iteration number N**: count existing `## Iteration N` headings in VERIFY_REPORT.md; if none, this is iteration 2 (Spike VIII initial run was iteration 1 — implicit).
3. **Re-dispatch**:
   - If parsed_scope.json changed: re-dispatch Steps 1, 2, 3, 4 with step labels `step1.iter{N}.extract`, ..., `step4.iter{N}.report` (4 rows in dispatches.jsonl).
   - If parsed_scope.json unchanged: re-dispatch Steps 2, 3, 4 only (3 rows in dispatches.jsonl).
4. **Append to VERIFY_REPORT.md**: Step 4 sub-agent reads the existing VERIFY_REPORT.md (if present) and appends `## Iteration N` heading + the new render. Do NOT overwrite prior iterations' trail.
5. **Record audit metadata**: orchestrator updates `iteration_state.json` via `server.run_dir.update_iteration_state` (one row per iteration).

## Audit invariant

Total `dispatches.jsonl` rows after N iterations = `4` (initial) + `(3 or 4) × (N - 1)` (subsequent), where the choice between 3 and 4 depends on parsed_scope.json change detection per iteration.
