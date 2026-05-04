# reviewer Step 1 — parse SCOPE.md
You are dispatched as reviewer Step 1 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`. Multi-write steps may emit multiple `WROTE:` lines; orchestrator takes the last match as canonical (helper `server.harness.extract_wrote_paths`).

## Inputs

- run_id: `{{RUN_ID}}`
- scope_path: `{{RUN_DIR}}/SCOPE.md`

## Goal

```python
import json
from pathlib import Path
from server.scope_parser import parse_scope_md

text = Path("{{RUN_DIR}}/SCOPE.md").read_text(encoding="utf-8")
result = parse_scope_md(text)
out = Path("{{RUN_DIR}}/parsed_scope.json")
out.write_text(json.dumps(result, indent=2, ensure_ascii=False),
               encoding="utf-8")
print(f"WROTE: {out}")
```

## SCOPE.md grammar

The parser is strict — only the following bullet shapes are accepted:

- **Form 1 (backtick-wrapped path + note)**: `` - `<path-token>` — <note> ``
- **Form 2 (plain path + note)**: `- <plain-token> — <note>`
- **Form 3 (note-less)**: `` - `<path-token>` `` or `- <plain-token>` (no em-dash)

`<path-token>` rules:
- no whitespace inside (rejects freeform prose with spaces)
- no backticks inside (rejects nested-backtick prose)
- dots, slashes, globs, dashes preserved verbatim
- outer backticks (form 1) stripped; inner content preserved verbatim

`<note>` separator MUST be ` — ` (U+2014 em-dash with single space on each side).
En-dash `–` (U+2013) and double-hyphen `--` are rejected with `*-entry-N-grammar`.

### Korean + backtick freeform — known failure mode

Freeform Korean prose with embedded backticks like
`` - `server/` 내 `run_dir.py` 외 모든 파일 (`__init__.py`, ...) — 변경 금지 ``
is **rejected** with `deny-entry-N-grammar` and the entry is **skipped**.

To deny multiple Korean files in one bullet, restructure as multiple form-1 bullets:
```
- `server/__init__.py` — 변경 금지
- `server/harness.py` — 변경 금지
```

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

Entry-level errors (in the `"errors"` array):

```json
{
  "errors": [
    "allow-entry-0-grammar",
    "deny-entry-2-grammar",
    "completion-fence-unclosed"
  ]
}
```

## Error modes

If SCOPE.md is missing → write JSON with `"errors": ["scope-missing"]` and empty arrays.
If `## Allow list` section absent → `"errors": ["allow-section-missing"]`.
If `## Completion criterion` fence empty → `"errors": ["completion-empty"]`.
If a bullet violates grammar → `"errors": ["allow-entry-N-grammar"]` or `"errors": ["deny-entry-N-grammar"]` (entry skipped, others kept).
If completion fence is opened but never closed → `"errors": ["completion-fence-unclosed"]` (captured content is kept as warning).

## Save

Write JSON via Python `json.dumps(..., indent=2, ensure_ascii=False)`. Print `WROTE: <absolute path>` and exit.
