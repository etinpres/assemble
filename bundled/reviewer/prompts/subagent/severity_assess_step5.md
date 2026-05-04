# reviewer Step 5 — severity assessment + verdict computation
You are dispatched as reviewer Step 5 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`. Multi-write steps may emit multiple `WROTE:` lines; orchestrator takes the last match as canonical (helper `server.harness.extract_wrote_paths`).

## Inputs

- run_id: `{{RUN_ID}}`
- classification_path: `{{RUN_DIR}}/classification.json`
- rule3_audit_path: `{{RUN_DIR}}/rule3_audit.json`
- parsed_scope_path: `{{RUN_DIR}}/parsed_scope.json`

## Goal

Aggregate Step 3 + Step 4 outputs into a deterministic verdict. Write `{{RUN_DIR}}/severity_grid.json`.

## Verdict logic (deterministic)

```
verdict = "merge-ready" if (
    classification.summary.deny_violation == 0
    AND classification.summary.allow_miss == 0
    AND rule3_audit.summary.critical == 0
) else "needs-fix"
```

`needs-fix` reasons listed in order: deny-violations first, then critical Rule 3, then allow-misses, then major Rule 3 only if user opts to weight them, else `merge-ready`.

## Severity grid

Buckets:
- **critical**: deny-violations, out-of-scope-refactors.
- **major**: cosmetic-drift Rule 3 verdicts.
- **minor**: scope-related Rule 3 verdicts.

## Output JSON shape

```json
{
  "critical": [
    {"path": "server/__init__.py", "reason": "deny-violation: server/ outside run_dir.py"}
  ],
  "major": [],
  "minor": [
    {"path": "server/run_dir.py", "reason": "scope-related minor change"}
  ],
  "verdict": "needs-fix",
  "verdict_reason": "1 deny-violation; resolve before merge.",
  "errors": []
}
```

`verdict_reason` is a single-sentence summary of the dominant cause.

## Constraints

- Pure aggregation. No new judgment beyond combining inputs.
- Use stdlib only.

## Save

Print `WROTE: <absolute path to severity_grid.json>` and exit.
