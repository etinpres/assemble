# reviewer Step 1 — parse SCOPE.md
You are dispatched as reviewer Step 1 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Inputs

- run_id: `{{RUN_ID}}`
- scope_path: `{{RUN_DIR}}/SCOPE.md`

## Goal

Read `{{RUN_DIR}}/SCOPE.md`, parse its three structured sections, and write the result to `{{RUN_DIR}}/parsed_scope.json`.

## SCOPE.md expected layout

````
# SCOPE — <task summary>

## Allow list

- <path/glob> — <note>
- ...

## Deny list

- <path/glob> — <note>
- ...

## Completion criterion

```bash
<one-liner>
```
````

## Output JSON shape

Write `{{RUN_DIR}}/parsed_scope.json` with this structure:

```json
{
  "task_summary": "<first H1 line, stripped of '# SCOPE — ' prefix>",
  "allow": [{"path": "<entry>", "note": "<note or empty>"}],
  "deny": [{"path": "<entry>", "note": "<note or empty>"}],
  "completion": "<bash one-liner from fenced block, stripped>",
  "errors": []
}
```

## Error modes

If SCOPE.md is missing → write JSON with `"errors": ["scope-missing"]` and empty arrays.
If `## Allow list` section absent → `"errors": ["allow-section-missing"]`.
If `## Completion criterion` fence empty → `"errors": ["completion-empty"]`.

## Constraints

- Allow/Deny entry parsing: split each bullet on the FIRST ` — ` (em-dash with surrounding spaces). Path is everything before; note is everything after (or empty if absent).
- Strip leading `- ` from bullets.
- Preserve path strings verbatim — do not normalize globs, do not resolve.
- Use `python3` and the standard library only. Do not call `Bash` for parsing.

## Save

Write JSON via Python `json.dumps(..., indent=2, ensure_ascii=False)`. Print `WROTE: <absolute path>` and exit.
