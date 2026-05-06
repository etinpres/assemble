# verifier quick mode — single-dispatch fallback
You are dispatched as verifier quick mode sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Bash tool access GRANTED

verifier full mode Step 2 와 동일하게 quick mode 도 completion command 실행을 위해 Bash 사용. 30s timeout, stdout/stderr 100KB cap, single `subprocess.run(["bash", "-c", completion], timeout=30, capture_output=True, text=True)` 만 허용.

## Inputs

- run_id: `{{RUN_ID}}`
- run_dir: `{{RUN_DIR}}`

## Goal

full mode 의 4-step verifier pipeline (Step 1 extract completion → Step 2 execute → Step 3 classify → Step 4 render report) 을 단일 dispatch 로 압축. `VERIFY_REPORT.md` 1 doc 에 7 sections 모두 inline.

산출물 schema 는 full mode 와 동일 — 단일 pass 안에서 parsed_scope.json read + completion 검증 + bash 실행 + verdict 산출 + report 렌더링.

## Output sections (must include all)

`VERIFY_REPORT.md` 안에 다음 7 canonical sections 모두 포함 (full mode 와 동일 schema):

- `## 1. Summary` — verdict line (`pass` / `fail` / `skipped` / `timed_out`) + 1-line 사유
- `## 2. Completion command` — parsed_scope.json 의 completion 필드 그대로
- `## 3. Execution result` — exit_code / duration_ms / timed_out / truncated / skipped
- `## 4. Stdout sample` — 100KB cap 내에서 stdout 일부
- `## 5. Stderr sample` — 100KB cap 내에서 stderr 일부
- `## 6. Verdict reasoning` — deterministic rule 적용 결과 (no LLM judgment)
- `## 7. Recommendations` — fail 시 다음 step 액션 (skip 시 사유 명시)
- `## Mode usage note` — `mode=quick` 1-line marker

Verdict logic (deterministic, full mode 와 동일):
```python
verdict = "pass" if (exit_code == 0 AND not skipped AND not timed_out) else "fail"
```

## Save block

```python
python3 << 'EOF'
import json
import subprocess
from pathlib import Path

run_id = "{{RUN_ID}}"
run_dir = Path("{{RUN_DIR}}")

# Step 1 inline — extract completion
scope_path = run_dir / "parsed_scope.json"
errors = []
completion = ""
try:
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    raw = scope.get("completion", "")
    if not isinstance(raw, str):
        errors.append("completion-not-string")
    elif not raw.strip():
        errors.append("completion-empty")
    elif len(raw) > 500:
        errors.append("completion-too-long")
    elif "\n" in raw.strip():
        errors.append("completion-multi-line")
    else:
        completion = raw.strip()
except FileNotFoundError:
    errors.append("parsed-scope-missing")
except json.JSONDecodeError:
    errors.append("parsed-scope-malformed")

# Step 2 inline — execute (skip if errors)
skipped = bool(errors)
exit_code = -1
stdout = ""
stderr = ""
duration_ms = 0
timed_out = False
truncated = False
CAP = 100_000

if not skipped:
    import time
    t0 = time.time()
    try:
        result = subprocess.run(
            ["bash", "-c", completion],
            timeout=30,
            capture_output=True,
            text=True,
        )
        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
        if len(stdout) > CAP:
            stdout = stdout[:CAP]
            truncated = True
        if len(stderr) > CAP:
            stderr = stderr[:CAP]
            truncated = True
    except subprocess.TimeoutExpired:
        timed_out = True
    duration_ms = int((time.time() - t0) * 1000)

# Step 3 inline — verdict
if skipped:
    verdict = "fail"
    reason = "skipped: " + ",".join(errors)
elif timed_out:
    verdict = "fail"
    reason = "timed out (30s budget)"
elif exit_code == 0:
    verdict = "pass"
    reason = "completion command exited 0"
else:
    verdict = "fail"
    reason = f"exited {exit_code}"

# Step 4 inline — render report
body = f"""# VERIFY_REPORT

**Run ID**: {run_id}
**Mode**: quick (single-dispatch fallback — V4 Spike XIV paradigm hybrid)

## 1. Summary

**Verdict**: {verdict} — {reason}

## 2. Completion command

```bash
{completion if completion else "(none — extraction errors)"}
```

## 3. Execution result

- exit_code: {exit_code}
- duration_ms: {duration_ms}
- timed_out: {timed_out}
- truncated: {truncated}
- skipped: {skipped}

## 4. Stdout sample

```
{stdout[:2000] if stdout else "(empty)"}
```

## 5. Stderr sample

```
{stderr[:2000] if stderr else "(empty)"}
```

## 6. Verdict reasoning

Deterministic rule applied: {reason}.

## 7. Recommendations

{"All clear — completion command passed." if verdict == "pass" else "Investigate failing command; re-run after fix."}

## Mode usage note

mode=quick — full mode 의 4-step verifier pipeline 이 단일 dispatch 로 압축됨. precision 손실 가능. KEEPER_REPORT § "Mode usage" 에 카운트 기록.
"""

out = run_dir / "VERIFY_REPORT.md"
out.write_text(body, encoding="utf-8")
print(f"WROTE: {out}")
EOF
```

## Output discipline

Single trailing line: `WROTE: <abs path to VERIFY_REPORT.md>`. No prose, no banners. Errors via `ERROR: <reason>` on stdout — main follows §CRITICAL retry/abort/report.
