# reviewer Step 3 — classify diff files vs allow/deny
You are dispatched as reviewer Step 3 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`. Multi-write steps may emit multiple `WROTE:` lines; orchestrator takes the last match as canonical (helper `server.harness.extract_wrote_paths`).

## Inputs

- run_id: `{{RUN_ID}}`
- parsed_scope_path: `{{RUN_DIR}}/parsed_scope.json`
- diff_inventory_path: `{{RUN_DIR}}/diff_inventory.json`

## Goal

For every file in `diff_inventory.json`, classify against allow + deny lists in `parsed_scope.json`. Write `{{RUN_DIR}}/classification.json`.

## Classification rules

For each diff file `f`:

1. **deny-violation**: `f` matches any deny entry (path prefix, exact match, or glob). Highest precedence — deny wins over allow.
2. **allow-hit**: `f` matches any allow entry. Record which allow entry matched.
3. **unrelated**: `f` matches neither.

Match logic (in order):
- If allow/deny entry ends with `/` → prefix match.
- If allow/deny entry contains `*` → fnmatch.
- Else → exact path match.

## Output JSON shape

```json
{
  "files": [
    {
      "path": "server/run_dir.py",
      "verdict": "allow-hit",
      "matched_rule": "server/run_dir.py — list_runs added"
    },
    {
      "path": "server/__init__.py",
      "verdict": "deny-violation",
      "matched_rule": "server/ — outside run_dir.py"
    }
  ],
  "allow_misses": [
    {"path": "tests/unit/test_run_dir.py", "note": "expected diff hit, none observed"}
  ],
  "summary": {
    "allow_hit": 1,
    "deny_violation": 1,
    "unrelated": 0,
    "allow_miss": 1
  },
  "errors": []
}
```

## Allow misses

After classifying all diff files, walk allow entries. Any allow entry that did NOT have at least one diff file matching it goes into `allow_misses`. (allow misses are not always failures — verdict logic decides.)

## Constraints

- Use `python3` + `json` + `fnmatch` standard library only.
- Read both input JSONs before classifying.
- Write classification.json with `json.dumps(..., indent=2, ensure_ascii=False)`.

## Save

Print `WROTE: <absolute path to classification.json>` and exit.
