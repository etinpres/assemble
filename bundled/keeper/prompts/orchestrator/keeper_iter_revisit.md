# keeper ★ — Iteration revisit (orchestrator helper)

> NOTE: This is an orchestrator helper, NOT a subagent prompt. Main Claude reads
> this directly when re-keeping is requested. NOT loaded via `dispatch_prompt`.
> Tools inherit from main Claude's access — no `Bash tool access GRANTED` marker.

## When to load this

User revises something after a prior keeper run and asks for re-keeping. Common triggers:

- User edits `parsed_scope.json` (e.g. corrected deny pattern that was producing R2 false positives) and wants keeper to re-audit.
- User edits `learnings.skip` to add an evidence_hash and wants keeper to re-prune the ledger (drop the now-skipped entry).
- A new bundle ran AFTER the initial keeper run (e.g. shipper deposited new artifacts) and user wants keeper to re-audit with the larger surface.
- Re-asking with no amendment is a **no-op** — see §Idempotency.

## Iteration semantics

| Step | Re-run condition |
|---|---|
| Step 1 (audit) | always re-run — run_dir contents may have changed |
| Step 2 (extract) | always re-run — depends on Step 1's audit_inventory |
| Step 3 (summarize) | only if Step 2 produced different `learning_candidates.json` (compare evidence_hash set vs prior iter); skip if identical (idempotent) |
| Step 4 (ledger) | always re-run — even with no new entries, prune may now drop more (skiplist updated) |

`dispatches.jsonl` row counts per iteration N:

- Standard iteration (Step 3 has new candidates): **4 rows** — `step1.iter{N}.audit`, `step2.iter{N}.extract`, `step3.iter{N}.summarize`, `step4.iter{N}.ledger`.
- Step 3 skipped (no candidate change): **3 rows** — Step 3 reuses prior `learnings_to_emit.json`.
- Audit-skipped iteration (Step 1 verdict=audit-skipped → Steps 2/3/4 not dispatched): **1 row** only.

Each iteration appends `## Iteration N` to KEEPER_REPORT.md without overwriting the prior trail (verifier ★ Spike VIII pattern).

## Idempotency

If user invokes keeper twice with NO change to `run_dir` / `parsed_scope.json` / `learnings.skip` → second run is a no-op:

- Step 1 `audit_inventory.json` byte-identical.
- Step 2 `learning_candidates.json` byte-identical (script idempotent — verified by B3 test).
- Step 3 skipped (Step 4 detects no candidate change).
- Step 4 prune detects 100% dedup of new entries (same evidence_hash) → ledger byte-identical.

This is the audit-trail invariant: no-change keeper runs do NOT pollute the ledger.

## Decision tree (main Claude follows)

```
prior_iter = highest N from `## Iteration N` headings in KEEPER_REPORT.md (0 if none)
new_iter_N = prior_iter + 1

if user supplied no amendment AND run_dir contents unchanged:
    # Idempotency: still re-run all 4 steps to confirm no drift,
    # but expect ledger byte-count delta = 0

dispatch Step 1 (audit) — always
dispatch Step 2 (extract) — always
read learning_candidates.json
if previous iter exists:
    compare evidence_hash set with prior — if identical, skip Step 3 (use prior learnings_to_emit.json)
else:
    dispatch Step 3 (summarize)
dispatch Step 4 (ledger) — always (re-prunes ledger with current skiplist)

each iteration appends `## Iteration N` block to KEEPER_REPORT.md
```

## Sub-agent prompts

The four keeper subagent prompts dispatched by this helper (in order):

1. `keeper_audit_step1.md` — audit run_dir contents → `audit_inventory.json`.
2. `keeper_extract_step2.md` — extract candidate learnings → `learning_candidates.json`.
3. `keeper_summarize_step3.md` — summarize candidates → `learnings_to_emit.json`.
4. `keeper_ledger_step4.md` — prune + append to `learnings.jsonl` ledger.

## Hand-off

keeper is a **terminal** bundle — there is no downstream stage. After the iteration completes, the user inspects:

- `KEEPER_REPORT.md` (cumulative `## Iteration N` blocks).
- `learnings.jsonl` (ledger — appended/pruned in Step 4).

No follow-up dispatch. If the user wants to amend skiplist / scope and re-prune, they re-invoke keeper with this orchestrator helper.
