# keeper Step 1 — audit inventory

You are dispatched as keeper Step 1 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$` last-match (Spike VII F7 inheritance — multi-write steps may emit multiple `WROTE:` lines; orchestrator takes the last).

## Inputs

- run_id: `{{RUN_ID}}`
- run_dir: `{{RUN_DIR}}` (auto-derived per Spike VII Track A)
- parsed_scope_path: `{{RUN_DIR}}/parsed_scope.json`

## Bash tool access GRANTED

Read-only git probes only, invoked through `server.git_helpers`:

- `git_status_porcelain(cwd)` — `git status --porcelain`
- `git_head_sha(cwd)` — `git rev-parse HEAD`
- `git_branch(cwd)` — `git rev-parse --abbrev-ref HEAD`
- `git_diff_name_only(cwd, range_spec)` — `git diff --name-only <range>` (range_spec validated; default `HEAD~..HEAD`)

These wrappers use argv-list `subprocess.run`/`Popen` (no shell, no string interpolation — T8 mitigation inherited from Spike IX). Do NOT call `git` directly via Bash — always go through the helpers.

**Forbidden** in this step (defense in depth):

- write-side git ops (`git tag`, `git commit`, `git add`, `git checkout`, `git reset`, etc.)
- any form of `git push`
- `shell=True`, `os.system`, backtick interpolation, or any path that lets caller-controlled strings reach a shell

If `parsed_scope.json` is unreadable the sub-agent still writes `audit_inventory.json` with `verdict = "audit-skipped"` and `skip_reason = "parsed_scope.json not readable"` so the orchestrator has a deterministic file to read. Do not raise; do not exit non-zero.

## Goal

Read `parsed_scope.json` (sanity, capture `scope_summary`), enumerate run_dir artifacts, parse any `*REPORT*.md` verdicts found, run four read-only git probes, compute deterministic verdict, write `{{RUN_DIR}}/audit_inventory.json`, emit a single `WROTE:` line.

Run from the assemble repo root (the harness sets that as CWD). Use `python3` + stdlib + `server.git_helpers` only. Do NOT import `server.scope_parser`, `server.harness`, or any LLM/HTTP helper — Step 1 is pure deterministic file IO + git probes.

## Save block

```python
python3 << 'EOF'
import json
import re
from pathlib import Path

from server.git_helpers import (
    git_branch,
    git_diff_name_only,
    git_head_sha,
    git_status_porcelain,
)

run_id = "{{RUN_ID}}"
run_dir = Path("{{RUN_DIR}}")
errors = []

# 1. parsed_scope.json — sanity + scope_summary capture
scope_path = run_dir / "parsed_scope.json"
scope_summary = ""
scope_readable = True
skip_reason = None
try:
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    raw_summary = scope.get("task_summary", "")
    if isinstance(raw_summary, str):
        scope_summary = raw_summary[:200]
except FileNotFoundError:
    errors.append("parsed-scope-missing")
    scope_readable = False
    skip_reason = "parsed_scope.json not readable"
except (json.JSONDecodeError, OSError):
    errors.append("parsed-scope-malformed")
    scope_readable = False
    skip_reason = "parsed_scope.json not readable"

# 2. Enumerate known artifact filenames
known_artifacts = [
    "parsed_scope.json",
    "dispatches.jsonl",
    "preflight.json",
    "version_bump.json",
    "build_result.json",
    "tag_result.json",
    "verify_result.json",
    "execution_result.json",
    "extracted_completion.json",
    "REVIEW_REPORT.md",
    "VERIFY_REPORT.md",
    "SHIP_REPORT.md",
]
artifacts_present = {name: (run_dir / name).exists() for name in known_artifacts}

# 3. Count dispatches.jsonl rows if present
dispatch_row_count = 0
if artifacts_present.get("dispatches.jsonl"):
    try:
        with (run_dir / "dispatches.jsonl").open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    dispatch_row_count += 1
    except OSError:
        pass

# 4. Parse verdicts from any *REPORT*.md files present (best-effort, never raise)
verdicts_collected = {}
report_to_bundle = {
    "REVIEW_REPORT.md": "reviewer",
    "VERIFY_REPORT.md": "verifier",
    "SHIP_REPORT.md": "shipper",
}
verdict_line_re = re.compile(r"^\s*(?:[-*]\s*)?\**verdict\**\s*[:=]\s*([^\n*]+)", re.IGNORECASE | re.MULTILINE)
for fname, bundle in report_to_bundle.items():
    if not artifacts_present.get(fname):
        continue
    try:
        text = (run_dir / fname).read_text(encoding="utf-8")
    except OSError:
        continue
    m = verdict_line_re.search(text)
    if m:
        verdicts_collected[bundle] = m.group(1).strip().strip("`").strip()

# 5. Derive bundles_observed from artifact presence
bundles_observed = []
if artifacts_present.get("dispatches.jsonl"):
    bundles_observed.append("dispatch-traces")
if artifacts_present.get("REVIEW_REPORT.md"):
    bundles_observed.append("reviewer")
if artifacts_present.get("VERIFY_REPORT.md"):
    bundles_observed.append("verifier")
if artifacts_present.get("SHIP_REPORT.md"):
    bundles_observed.append("shipper")

# 6. Git probes — argv-list, read-only (T8 mitigation)
cwd = Path.cwd()

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

diff = git_diff_name_only(cwd, "HEAD~..HEAD")
git_diff_files = []
if diff["ok"]:
    git_diff_files = [line for line in diff["stdout"].splitlines() if line]

# 7. Deterministic verdict
# audit-ready iff parsed_scope readable AND >=1 bundle artifact (anything other
# than parsed_scope.json itself).
non_scope_artifacts_present = any(
    present
    for name, present in artifacts_present.items()
    if name != "parsed_scope.json" and present
)
if not scope_readable:
    verdict = "audit-skipped"
    if skip_reason is None:
        skip_reason = "parsed_scope.json not readable"
elif not non_scope_artifacts_present:
    verdict = "audit-skipped"
    skip_reason = "no bundle artifacts present in run_dir"
else:
    verdict = "audit-ready"

# 8. Assemble audit_inventory.json
result = {
    "run_id": run_id,
    "verdict": verdict,
    "bundles_observed": bundles_observed,
    "artifacts_present": artifacts_present,
    "dispatch_row_count": dispatch_row_count,
    "verdicts_collected": verdicts_collected,
    "git_probes": {
        "clean_tree": clean_tree,
        "dirty_files": dirty_files,
        "head_sha": head_sha,
        "branch": branch,
        "git_diff_files": git_diff_files,
    },
    "scope_summary": scope_summary,
    "errors": errors,
}
if skip_reason is not None:
    result["skip_reason"] = skip_reason

out = run_dir / "audit_inventory.json"
out.write_text(
    json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False),
    encoding="utf-8",
)
print(f"WROTE: {out}")
EOF
```

## Verdict logic (canonical)

```python
verdict = (
    "audit-ready"
    if scope_readable and non_scope_artifacts_present
    else "audit-skipped"
)
```

Skip reasons (deterministic):

- `parsed_scope.json not readable` — scope file missing or malformed JSON
- `no bundle artifacts present in run_dir` — scope present but no other bundle output to audit

## Output JSON shape

```json
{
  "run_id": "<string>",
  "verdict": "audit-ready",
  "bundles_observed": ["dispatch-traces", "reviewer", "verifier", "shipper"],
  "artifacts_present": {
    "parsed_scope.json": true,
    "dispatches.jsonl": true,
    "preflight.json": true,
    "version_bump.json": true,
    "build_result.json": true,
    "tag_result.json": true,
    "verify_result.json": true,
    "execution_result.json": false,
    "extracted_completion.json": false,
    "REVIEW_REPORT.md": true,
    "VERIFY_REPORT.md": true,
    "SHIP_REPORT.md": true
  },
  "dispatch_row_count": 7,
  "verdicts_collected": {
    "reviewer": "merge-ready",
    "verifier": "pass",
    "shipper": "ship-ready"
  },
  "git_probes": {
    "clean_tree": true,
    "dirty_files": [],
    "head_sha": "abc123...",
    "branch": "master",
    "git_diff_files": ["src/auth.py", "tests/unit/test_auth.py"]
  },
  "scope_summary": "Audit V4 Spike X keeper bundle ...",
  "errors": []
}
```

`sort_keys=True` is mandatory — downstream golden-file tests rely on stable ordering. `skip_reason` is only present when `verdict == "audit-skipped"`.

## Error handling

If `parsed_scope.json` is missing or unparseable:

- `errors = ["parsed-scope-missing"]` or `["parsed-scope-malformed"]`
- `verdict = "audit-skipped"`
- `skip_reason = "parsed_scope.json not readable"`

Still write `audit_inventory.json` and emit the `WROTE:` line — orchestrator needs the file to render the audit-skipped report. Exit 0 either way; orchestrator detects via `errors` field, not via exit code.

If git probes fail (e.g. not a git repo), `clean_tree` stays `False`, `head_sha`/`branch` stay empty strings, `git_diff_files` stays `[]`. The audit verdict still computes deterministically — git probe failure does NOT downgrade `audit-ready` to `audit-skipped` (the audit is about run_dir contents, not the working tree).

Report-parse failures (malformed `*REPORT*.md`, missing `verdict:` line) are silently dropped from `verdicts_collected`. Step 1 never raises on report-format issues — that's the report author's bug, not the auditor's.

## Output discipline

Single trailing line:

```
WROTE: <abs path to audit_inventory.json>
```

Orchestrator parses with regex `^WROTE: (.+)$` and takes the last match (Spike VII F7 inheritance). Do NOT print prose, banners, progress dots, or warning text on stdout. Errors/diagnostics belong in the JSON `errors` field.
