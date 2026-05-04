# verifier Step 1 — extract completion bash

You are dispatched as verifier Step 1 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`. Multi-write steps may emit multiple `WROTE:` lines; orchestrator takes the last match as canonical (helper `server.harness.extract_wrote_paths`).

## Inputs

- run_id: `{{RUN_ID}}`
- parsed_scope_path: `{{RUN_DIR}}/parsed_scope.json`

## Goal

Read `{{RUN_DIR}}/parsed_scope.json`, validate the `completion` field, write `{{RUN_DIR}}/extracted_completion.json`.

Run with `python3 -c "..."` (or write to a temp file then `python3 <file>`) from the assemble repo root — the harness sets that as CWD. `python3` + stdlib only. NO Bash.

```python
import json
from pathlib import Path

scope = json.loads(Path("{{RUN_DIR}}/parsed_scope.json").read_text(encoding="utf-8"))
completion = (scope.get("completion") or "").strip()

errors = []
if not completion:
    errors.append("completion-empty")
if len(completion) > 500:
    errors.append("completion-too-long")
if "\n" in completion:
    errors.append("completion-multiline")

result = {
    "completion": completion,
    "length": len(completion),
    "errors": errors,
}
out = Path("{{RUN_DIR}}/extracted_completion.json")
out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"WROTE: {out}")
```

## Validation rules

1. completion must be non-empty after `.strip()` — else `errors: ["completion-empty"]`
2. `len(completion) <= 500` (security cap, see verifier SKILL.md § Security — A4 lands the security model doc)
3. completion must be a single line (no embedded `\n`) — else `errors: ["completion-multiline"]`

If any rule violated, write the JSON with `errors` populated and exit 0. Orchestrator detects via the `errors` field, not via exit code. **Step 2 will skip execution if errors is non-empty** (per A3 contract).

## Output JSON shape

```json
{
  "completion": "<bash one-liner stripped>",
  "length": 142,
  "errors": []
}
```

Or with errors:

```json
{
  "completion": "<original — preserved verbatim for audit trail>",
  "length": 612,
  "errors": ["completion-too-long"]
}
```

## Constraints

- python3 + stdlib only. Do NOT call Bash.
- Preserve completion verbatim — do not normalize quotes, do not reformat.
- Do NOT execute the completion command (Step 2's responsibility).
- ensure_ascii=False — Korean characters in completion (e.g. for completion criteria with Korean test descriptions) must round-trip.

## Save

Write JSON via Python `json.dumps(..., indent=2, ensure_ascii=False)`. Print `WROTE: <absolute path>` and exit.
