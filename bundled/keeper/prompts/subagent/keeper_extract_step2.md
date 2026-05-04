# keeper Step 2 — deterministic rule extraction

You are dispatched as keeper Step 2 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$` last-match (Spike VII F7 inheritance — multi-write steps may emit multiple `WROTE:` lines; orchestrator takes the last).

## Inputs

- run_id: `{{RUN_ID}}`
- run_dir: `{{RUN_DIR}}` (auto-derived per Spike VII Track A)
- audit_inventory_path: `{{RUN_DIR}}/audit_inventory.json` (REQUIRED — Step 1 output)

## Bash tool access GRANTED

Scope: **ONE canned invocation only** — the version-controlled extractor script:

```
python3 $HOME/.claude/skills/assemble/bundled/keeper/scripts/extract_rules.py {{RUN_DIR}}
```

The script is stdlib-only (no `server.*` imports, no LLM, no network) so it runs from any cwd. It reads `audit_inventory.json`, optional `parsed_scope.json`, optional `dispatches.jsonl`, optional `verify_result.json`, applies five deterministic rules (R1-R5), and writes `learning_candidates.json` with candidates sorted by `(rule_id, evidence_hash)` for byte-identical idempotency.

**Forbidden** in this step (defense in depth):

- ANY other Bash command — no `ls`, no `cat`, no exploratory probes, no other scripts
- `shell=True` invocation patterns or argument interpolation beyond the literal `{{RUN_DIR}}` substitution
- editing the script (`scripts/extract_rules.py`) or any other file at runtime
- any form of `git` invocation outside the script (the script's R4 rule handles its own `git diff` probe)

If the script exits non-zero (typically: `audit_inventory.json` missing in run_dir), forward the script's stderr verbatim and exit non-zero. Do NOT write a placeholder `learning_candidates.json` — the upstream Step 1 should have produced `audit_inventory.json` already; its absence is a hard error.

## Goal

Invoke the canned extractor with `{{RUN_DIR}}` as its single argument. Forward the script's `WROTE:` line to stdout. The script handles all five rules, deterministic sorting, evidence_hash canonicalization, and atomic write — your only job is to invoke and forward.

## Save block

```bash
python3 "$HOME/.claude/skills/assemble/bundled/keeper/scripts/extract_rules.py" "{{RUN_DIR}}"
```

Capture stdout, parrot the trailing `WROTE: <abs path>` line. The script prints exactly one `WROTE:` line on success; emit it as your final output.

## Output discipline

Single trailing line:

```
WROTE: <abs path to learning_candidates.json>
```

Orchestrator parses with regex `^WROTE: (.+)$` and takes the last match (Spike VII F7 inheritance). Do NOT print prose, banners, progress dots, or warning text on stdout. Errors/diagnostics from the script come on stderr; forward those without injecting your own prose.

## Rule reference (informational — implemented in extract_rules.py)

| Rule | Category | Detection |
|---|---|---|
| R1 | rule-violation | per failed dispatch row in `dispatches.jsonl` |
| R2 | scope-deviation | `parsed_scope.deny` ∩ `audit_inventory.git_probes.git_diff_files` (fnmatch) |
| R3 | ac-failure | `verify_result.verdict == "fail"` |
| R4 | todo-leakage | TODO/FIXME/XXX markers added in `git diff --unified=0 HEAD~..HEAD` |
| R5 | dispatch-failure | aggregate enumeration of failed dispatch steps |

R1 vs R5: same data source (`dispatches.jsonl`) at different granularities — R1 is per-row detail, R5 is the aggregate dispatch-discipline summary. Track B's STAGE_CATEGORY_PRIORITY uses both as separate ranking categories; the duplication is intentional.
