# shipper Step 1 — pre-flight check

You are dispatched as shipper Step 1 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$` last-match (Spike VII F7 inheritance — multi-write steps may emit multiple `WROTE:` lines; orchestrator takes the last).

## Inputs

- run_id: `{{RUN_ID}}`
- run_dir: `{{RUN_DIR}}` (auto-derived per Spike VII Track A)
- parsed_scope_path: `{{RUN_DIR}}/parsed_scope.json`
- verify_result_path: `{{RUN_DIR}}/verify_result.json` (optional — may be missing)

## Bash tool access GRANTED

Read-only git probes only, invoked through `server.git_helpers`:

- `git_status_porcelain(cwd)` — `git status --porcelain`
- `git_head_sha(cwd)` — `git rev-parse HEAD`
- `git_branch(cwd)` — `git rev-parse --abbrev-ref HEAD`

These wrappers use argv-list `subprocess.run` (no shell, no string interpolation — T8 mitigation from the Spike IX threat table). Do NOT call `git` directly via Bash — always go through the helpers.

**Forbidden** in this step (defense in depth):

- write-side git ops (`git tag`, `git commit`, `git add`, `git checkout`, `git reset`, etc.)
- any form of `git push`
- `shell=True`, `os.system`, backtick interpolation, or any path that lets caller-controlled strings reach a shell

Sub-agent always treats missing `verify_result.json` as `verify_check = "missing"` and lets the deterministic verdict logic below handle it.

## Goal

Read `parsed_scope.json` (sanity), read `verify_result.json` (optional), run three read-only git probes, compute deterministic verdict, write `{{RUN_DIR}}/preflight.json`, emit a single `WROTE:` line.

Run from the assemble repo root (the harness sets that as CWD). Use `python3` + stdlib + `server.git_helpers` only.

```python
import json
from pathlib import Path

from server.git_helpers import git_branch, git_head_sha, git_status_porcelain

run_dir = Path("{{RUN_DIR}}")
errors = []

# 1. parsed_scope.json — sanity + scope_summary capture
scope_path = run_dir / "parsed_scope.json"
scope_summary = ""
try:
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    raw_summary = scope.get("task_summary", "")
    if isinstance(raw_summary, str):
        scope_summary = raw_summary[:200]
except FileNotFoundError:
    errors.append("parsed-scope-missing")
    scope = None
except json.JSONDecodeError:
    errors.append("parsed-scope-malformed")
    scope = None

# 2. verify_result.json — optional
verify_path = run_dir / "verify_result.json"
verify_verdict = None
verify_check = "present"
if verify_path.exists():
    try:
        verify = json.loads(verify_path.read_text(encoding="utf-8"))
        verify_verdict = verify.get("verdict")
    except json.JSONDecodeError:
        verify_check = "malformed"
else:
    verify_check = "missing"

# 3. Repo root — trust caller
cwd = Path.cwd()

# 4-6. Git probes (argv-list, read-only — T8 mitigation)
status = git_status_porcelain(cwd)
clean_tree = status["ok"] and status["stdout"].strip() == ""
dirty_files = []
if not clean_tree and status["ok"]:
    for line in status["stdout"].splitlines():
        # porcelain format: "XY path" — strip 3-char prefix
        if len(line) > 3:
            dirty_files.append(line[3:])
        if len(dirty_files) >= 20:
            break

head = git_head_sha(cwd)
head_sha = head["stdout"].strip() if head["ok"] else ""

br = git_branch(cwd)
branch = br["stdout"].strip() if br["ok"] else ""

# 7. Deterministic verdict
if errors:
    verdict = "fail"
    reason = "parsed_scope.json not readable"
elif clean_tree and (verify_verdict == "pass" or verify_check == "missing"):
    verdict = "pass"
    reason = f"clean tree; verify={verify_verdict if verify_verdict else verify_check}"
elif not clean_tree:
    verdict = "fail"
    reason = "fail (dirty tree): " + ", ".join(dirty_files[:5])
else:
    verdict = "fail"
    reason = f"fail (verify failed): verify_verdict={verify_verdict!r}, verify_check={verify_check!r}"

# 8. Write preflight.json
result = {
    "verdict": verdict,
    "reason": reason,
    "clean_tree": clean_tree,
    "dirty_files": dirty_files,
    "head_sha": head_sha,
    "branch": branch,
    "verify_verdict": verify_verdict,
    "verify_check": verify_check,
    "scope_summary": scope_summary,
    "errors": errors,
}
out = run_dir / "preflight.json"
out.write_text(
    json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False),
    encoding="utf-8",
)
print(f"WROTE: {out}")
```

## Verdict logic (canonical)

```python
verdict = (
    "pass"
    if (clean_tree and (verify_verdict == "pass" or verify_check == "missing"))
    else "fail"
)
```

Reason text contract:

- `pass` → `"clean tree; verify={pass | missing}"`
- `fail (dirty tree)` → `"fail (dirty tree): <first 5 dirty paths, comma-joined>"`
- `fail (verify failed)` → `"fail (verify failed): verify_verdict=<repr>, verify_check=<repr>"` (`verify_check` is `present` when verify_result.json was readable but verdict ≠ pass; `malformed` when JSON parse failed)
- parsed_scope unreadable → `"parsed_scope.json not readable"` (verdict=fail, errors populated)

## Output JSON shape

```json
{
  "branch": "main",
  "clean_tree": true,
  "dirty_files": [],
  "errors": [],
  "head_sha": "abc123...",
  "reason": "clean tree; verify=pass",
  "scope_summary": "Ship Spike IX shipper bundle ...",
  "verdict": "pass",
  "verify_check": "present",
  "verify_verdict": "pass"
}
```

`sort_keys=True` is mandatory — downstream golden-file tests rely on stable ordering.

## Error handling

If `parsed_scope.json` is missing or unparseable, set:

- `errors = ["parsed-scope-missing"]` or `["parsed-scope-malformed"]`
- `verdict = "fail"`
- `reason = "parsed_scope.json not readable"`

Still write `preflight.json` and emit the `WROTE:` line — orchestrator needs the file to render the abort report (Step 4 abort-path template). Exit 0 either way; orchestrator detects via `errors` field, not via exit code.

If git probes fail (e.g. not a git repo), `clean_tree` stays `False`, `head_sha`/`branch` stay empty strings, and the verdict falls through to `fail (dirty tree)` with empty dirty list — orchestrator reads stderr from the run log if a deeper diagnosis is needed.

## Output discipline

Single trailing line:

```
WROTE: <abs path to preflight.json>
```

Orchestrator parses with regex `^WROTE: (.+)$` and takes the last match (Spike VII F7 inheritance). Do NOT print prose, banners, progress dots, or warning text on stdout. Errors/diagnostics belong in the JSON `errors` field.
