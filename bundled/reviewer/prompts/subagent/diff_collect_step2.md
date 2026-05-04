# reviewer Step 2 — git diff collection
You are dispatched as reviewer Step 2 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Inputs

- run_id: `{{RUN_ID}}`
- diff_range: `{{DIFF_RANGE}}` — git rev-spec, e.g., `HEAD`, `main..HEAD`, `abc123^..abc123`. Defaults to `HEAD` (working tree vs HEAD) if empty.
- repo_path: `{{REPO_PATH}}` — absolute path to the repo. Defaults to current working directory.

## Goal

Run `git diff` for the given range, write summary JSON to `{{RUN_DIR}}/diff_inventory.json` and the raw diff to `{{RUN_DIR}}/raw.diff`.

## Steps

1. cd to `{{REPO_PATH}}` (or stay in cwd if empty).
2. Resolve `{{DIFF_RANGE}}` → `range`. If empty/falsy → `range = "HEAD"`.
3. Run `git diff --numstat {range}` → parse into `[{"path": ..., "added": N, "removed": M}, ...]`.
4. Run `git diff --name-status {range}` → augment each entry with `status` (one of `A`, `M`, `D`, `R...`, etc.).
5. Run `git diff {range}` → save full output to `{{RUN_DIR}}/raw.diff`.
6. Compute totals: `total_files`, `total_added`, `total_removed`.
7. Write JSON:

```json
{
  "range": "<resolved range>",
  "repo_path": "<resolved repo path>",
  "files": [
    {"path": "server/run_dir.py", "added": 12, "removed": 0, "status": "M"}
  ],
  "totals": {"files": 1, "added": 12, "removed": 0},
  "raw_diff_path": "{{RUN_DIR}}/raw.diff",
  "errors": []
}
```

## Error modes

- Not a git repo → `"errors": ["not-a-git-repo"]`, empty `files`.
- Invalid range → `"errors": ["bad-range: <stderr>"]`, empty `files`.
- Empty diff (no changes) → `"errors": ["empty-diff"]` is NOT an error, just `files: []`.

## Save

Write `diff_inventory.json` and `raw.diff`. Print `WROTE: <absolute path to diff_inventory.json>` and exit.
