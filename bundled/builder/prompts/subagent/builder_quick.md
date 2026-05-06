# builder quick mode — single-dispatch fallback
You are dispatched as builder quick mode sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Inputs

- run_id: `{{RUN_ID}}`
- run_dir: `{{RUN_DIR}}`
- task_summary: `{{TASK_SUMMARY}}`
- known_files: `{{KNOWN_FILES}}`
- test_cmd: `{{TEST_CMD}}`
- ac_cmd: `{{AC_CMD}}`

## Goal

full mode 의 7-step TDD pipeline (Step 2 SCOPE + skeleton → Step 3 test_first.sh red → Step 4 implementation → Step 5 verify.sh green → Step 6 self-review → Step 7 commit + status flip) 을 단일 dispatch 로 압축. `IMPL_REPORT.md` 1 doc 에 7 sections 모두 inline 으로 포함.

산출물 schema 는 full mode 와 동일 — 단일 pass 안에서 SCOPE.md + test_first.sh + verify.sh + IMPL_REPORT.md 를 모두 작성하되 verification iteration 은 1회로 제한.

## Output sections (must include all)

`IMPL_REPORT.md` 안에 다음 sections 모두 포함 (full mode 7-section schema 보존):

- 프론트매터: `status: complete`
- `## TL;DR` — 1-line 변경 요약
- `## Scope` — allow-list / deny-list / completion criterion (SCOPE.md 핵심 내용 inline)
- `## Test (red)` — test_first.sh 명령 + 실패 출력
- `## Implementation` — 변경된 파일 + 핵심 패치 요약
- `## Verify (green)` — verify.sh 명령 + 통과 증거 (exit 0)
- `## Self-review` — diff vs SCOPE deviation count + recommendation
- `## Commit message` — 1-line subject + body
- `## Mode usage note` — `mode=quick` 1-line marker

Sub-agent 는 동일 dispatch 안에서 SCOPE.md 와 test_first.sh / verify.sh shell 도 함께 작성하고 마지막에 IMPL_REPORT.md 의 path 만 `WROTE:` 로 출력.

## Save block

```python
python3 << 'EOF'
from pathlib import Path

run_id = "{{RUN_ID}}"
run_dir = Path("{{RUN_DIR}}")
task_summary = "{{TASK_SUMMARY}}"
known_files = "{{KNOWN_FILES}}"
test_cmd = "{{TEST_CMD}}"
ac_cmd = "{{AC_CMD}}"

# Sub-agent: 본 dispatch 안에서 다음 4 파일 모두 작성
# 1. run_dir / "SCOPE.md"        (allow/deny/completion)
# 2. run_dir / "test_first.sh"   (red — exits non-zero before fix)
# 3. run_dir / "verify.sh"       (green — exits 0 after fix)
# 4. run_dir / "IMPL_REPORT.md"  (final report — 7 sections + status: complete)
# Source-file 편집은 SCOPE.md allow-list 안에서만.
# 모든 <TBD: ...> 는 concrete 으로 채워야 함.

body = f"""---
status: complete
mode: quick
---

# IMPL_REPORT — {task_summary}

**Run ID**: {run_id}

## TL;DR

<TBD: 1-line summary of changes>

## Scope

- allow-list: <TBD>
- deny-list: <TBD>
- completion criterion: <TBD>

## Test (red)

```bash
{test_cmd}
```

<TBD: failing output excerpt>

## Implementation

<TBD: list of files changed + patch summary>

## Verify (green)

```bash
{ac_cmd}
```

<TBD: passing output excerpt — exit 0>

## Self-review

- scope deviations: <TBD count>
- recommendation: <TBD>

## Commit message

<TBD: 1-line subject + body>

## Mode usage note

mode=quick — full mode 의 7-step TDD pipeline 이 단일 dispatch 로 압축됨. precision 손실 가능. KEEPER_REPORT § "Mode usage" 에 카운트 기록.
"""

out = run_dir / "IMPL_REPORT.md"
out.write_text(body, encoding="utf-8")
print(f"WROTE: {out}")
EOF
```

## Output discipline

Single trailing line: `WROTE: <abs path to IMPL_REPORT.md>`. No prose, no banners. Errors via `ERROR: <reason>` on stdout — main follows §CRITICAL retry/abort/report.
