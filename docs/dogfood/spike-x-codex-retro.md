# Spike X Codex Retro

## Summary table
| # | Target | Severity | Status |
|---|--------|----------|--------|
| 1 | extract_rules.py R1-R5 deterministic logic | Important | R2 ignores real parsed_scope.deny schema |
| 2 | prune_ledger 4-rule order | Confirmed non-finding | TTL -> skiplist -> dedup -> FIFO cap is explicit and deterministic |
| 3 | Track B body-prefix fence splice | Confirmed non-finding | First-delimiter splice and preamble sha invariant hold |
| 4 | Ledger schema durability for V5 | Minor | V5 should add schema/hash versioning |
| 5 | dispatch_and_record routing | Confirmed non-finding | Cross-bundle injection is intentional and map-covered |
| 6 | extract_rules.py and ledger_update.py imports | Confirmed non-finding | Imports/subprocess use match spec |

## Finding 1 - R2 ignores real parsed_scope deny entries
Severity: Important (V4 fix required)

Evidence: `bundled/keeper/scripts/extract_rules.py:260-263` reads `parsed_scope["deny"]` and keeps only string entries. `bundled/keeper/scripts/extract_rules.py:271` passes those strings into R2. But the production parser schema is object-based: `server/scope_parser.py:394-395` documents `allow`/`deny` as `{"path": str, "note": str}`, and `server/scope_parser.py:470-473` returns `deny_entries`.

Tests missed this because `tests/unit/test_keeper_extract_rules.py:80-84` writes `deny: list[str]`, and R2 tests at `tests/unit/test_keeper_extract_rules.py:253-284` use string fixtures.

Impact: R2 silently false-negatives for normal V4 `parsed_scope.json`, so keeper misses core deny-list scope deviations.

Remediation: accept both shapes in `_load_deny_patterns(parsed_scope)`:
- Iterate `parsed_scope.get("deny", [])`
- For each item: if `isinstance(item, str)` → use as pattern; if `isinstance(item, dict)` and has `"path"` key with str value → use `item["path"]`; else skip silently.

Add 2+ regression tests with the production schema (object-based deny entries).

V4-vs-V5 scope: V4 fix. Blocks a Spike X core rule with the existing parser contract.

Cross-ref: Same class as Spike VI deny-list parsing fragility.

## Finding 2 - Ledger hash/schema versioning
Severity: Minor (V5)

Evidence: schema documented in `server/learnings.py:20-24`, materialized in `bundled/keeper/scripts/ledger_update.py:92-100`. Hashing deterministic at `bundled/keeper/scripts/extract_rules.py:60-68`.

Recommendation: V5 should add `schema_version` and `hash_version` fields before changing evidence normalization or concurrent-write behavior. Document current as `evidence-json-v1`.

V4-vs-V5 scope: V5. Not Spike X blocker.

## Confirmed non-findings

### Target 1 deeper - R1/R3/R4/R5 determinism + R2 rename hypothesis
R1/R5 deterministic over dispatch rows. R3 single predicate. R4 argv-list `git diff --unified=0` scans `+` lines, skips headers. Output sort + JSON `sort_keys=True` make idempotency provable.

R2 rename hypothesis: Step 1 records only HEAD~..HEAD diff; intermediate rename → denied path → renamed away wouldn't appear unless in compared endpoint. Consistent with code.

### Target 2 - prune_ledger order
TTL `server/learnings.py:358-367`, skiplist `368-372`, dedup `374-397`, FIFO cap `399-417`. All combinations covered by tests.

### Target 3 - Track B fence splice
`wrap_with_preamble` constructs `<pre>\n[TASK]\n<body>` at `server/harness.py:197-213`. Fence splice first-delim only at `server/harness.py:264-269`. Tests verify at `tests/unit/test_wrap_with_preamble_and_learnings.py:132-157`. Preamble sha invariant intact. Degraded no-preamble mode silently drops fence — acceptable V4 behavior.

### Target 5 - dispatch_and_record routing
New route `server/harness.py:812-835`. Allowlist gate `824-830`. `_PROMPT_TO_STAGE` covers all allowed prompts. No per-bundle opt-out missed; cross-bundle injection is intended Track B semantic.

### Target 6 - imports and subprocess safety
`extract_rules.py` stdlib only. `ledger_update.py` PYTHONPATH documented, one `server.learnings` import. Subprocess argv-list/no shell.
