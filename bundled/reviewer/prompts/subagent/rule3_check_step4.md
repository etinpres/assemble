# reviewer Step 4 — Rule 3 (Surgical Changes) audit
You are dispatched as reviewer Step 4 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`. Multi-write steps may emit multiple `WROTE:` lines; orchestrator takes the last match as canonical (helper `server.harness.extract_wrote_paths`).

## Harness Rule 3

> Surgical Changes — diff range = requested range. No incidental refactors, formatting, comment edits not requested by the task.

## Inputs

- run_id: `{{RUN_ID}}`
- raw_diff_path: `{{RUN_DIR}}/raw.diff`
- classification_path: `{{RUN_DIR}}/classification.json`
- parsed_scope_path: `{{RUN_DIR}}/parsed_scope.json`

## Goal

For every file in `classification.json`, audit the actual hunks in `raw.diff` for Rule 3 conformance. Write `{{RUN_DIR}}/rule3_audit.json`.

## Per-file verdict

- **scope-related** — every hunk plausibly serves the SCOPE task summary or a listed allow entry. Severity: `minor`.
- **cosmetic-drift** — at least one hunk is purely formatting / whitespace / comment renames / unrelated identifier renames with no behavior change. Severity: `major`.
- **out-of-scope-refactor** — at least one hunk introduces logic changes outside the task summary's stated goal (new functions, restructured modules, refactored callers). Severity: `critical`.

A `deny-violation` file from Step 3 is automatically `out-of-scope-refactor` (deny wins).

## Output JSON shape

```json
{
  "files": [
    {
      "path": "server/run_dir.py",
      "verdict": "scope-related",
      "evidence": "All hunks add list_runs() function and its tests; matches SCOPE allow entry.",
      "severity": "minor"
    }
  ],
  "summary": {"critical": 0, "major": 0, "minor": 1},
  "errors": []
}
```

## Audit method

For each file:
1. Extract its `diff --git` block from `raw.diff`.
2. Read SCOPE `task_summary` + matched allow rule from classification.
3. Decide verdict:
   - If classification verdict is `deny-violation` → `out-of-scope-refactor`, severity `critical`.
   - If hunks introduce only whitespace/comment/format changes → `cosmetic-drift`, severity `major`.
   - Else if hunks plausibly serve task summary → `scope-related`, severity `minor`.
   - Else if hunks introduce logic outside task summary → `out-of-scope-refactor`, severity `critical`.
4. `evidence`: ≤ 200 chars summarizing the rationale, citing line ranges.

## Constraints

- Read raw.diff with Python; do not invoke git again.
- Use stdlib only.

## Save

Print `WROTE: <absolute path to rule3_audit.json>` and exit.
