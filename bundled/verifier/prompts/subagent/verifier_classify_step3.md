# verifier Step 3 — classify execution result

You are dispatched as verifier Step 3 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`. Multi-write steps may emit multiple `WROTE:` lines; orchestrator takes the last match as canonical (helper `server.harness.extract_wrote_paths`).

## Inputs

- run_id: `{{RUN_ID}}`
- exec_path: `{{RUN_DIR}}/execution_result.json`

## Goal

Read `{{RUN_DIR}}/execution_result.json`, apply deterministic verdict logic, write `{{RUN_DIR}}/verify_result.json`.

Run with `python3 -c "..."` (or write to a temp file then `python3 <file>`) from the assemble repo root — the harness sets that as CWD. python3 + stdlib only. NO Bash.

## Verdict logic (deterministic)

```python
import json
from pathlib import Path

exec_result = json.loads(
    Path("{{RUN_DIR}}/execution_result.json").read_text(encoding="utf-8")
)

if exec_result["skipped"]:
    verdict = "fail"
    skip_reasons = exec_result.get("skip_reasons") or [exec_result.get("skip_reason", "")]
    reason = f"skipped: {', '.join(s for s in skip_reasons if s)}"
elif exec_result["timed_out"]:
    verdict = "fail"
    reason = "timed out (30s budget)"
elif exec_result["exit_code"] == 0:
    verdict = "pass"
    reason = "completion command exited 0"
else:
    verdict = "fail"
    reason = f"exited {exec_result['exit_code']}"

result = {
    "verdict": verdict,
    "reason": reason,
    "exit_code": exec_result.get("exit_code"),
    "duration_ms": exec_result.get("duration_ms", 0),
    "truncated": exec_result.get("truncated", False),
    "timed_out": exec_result.get("timed_out", False),
    "skipped": exec_result.get("skipped", False),
}
out = Path("{{RUN_DIR}}/verify_result.json")
out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"WROTE: {out}")
```

## Verdict invariant

```
verdict == "pass"  iff  exit_code == 0  AND  not skipped  AND  not timed_out
verdict == "fail"  otherwise
```

This is the canonical rule for `spike-viii-verifier-verdict-invariant` contract (lands A8). NO LLM judgment. Truncated stdout/stderr does NOT auto-fail — verdict logic ignores `truncated`; it surfaces in VERIFY_REPORT for human review (A6).

## Output JSON shape

```json
{
  "verdict": "pass",
  "reason": "completion command exited 0",
  "exit_code": 0,
  "duration_ms": 142,
  "truncated": false,
  "timed_out": false,
  "skipped": false
}
```

Fail variants:
- `verdict: "fail"`, `reason: "exited 1"`, `exit_code: 1`
- `verdict: "fail"`, `reason: "timed out (30s budget)"`, `exit_code: 124`, `timed_out: true`
- `verdict: "fail"`, `reason: "skipped: completion-too-long, completion-multiline"`, `exit_code: null`, `skipped: true`

## Constraints

- python3 + stdlib only. NO Bash.
- NO subjective judgment — verdict is `pass` iff `exit_code == 0` AND not skipped AND not timed-out.
- Truncated output does NOT auto-fail — `truncated: true` is metadata for the report, not a verdict input.
- ensure_ascii=False — Korean characters in `reason` (if execution_result has Korean error text) must round-trip.
- Preserve exec_result fields verbatim — do not normalize or transform.

## Save

Write JSON via Python `json.dumps(..., indent=2, ensure_ascii=False)`. Print `WROTE: <absolute path>` and exit.
