# reviewer quick mode — single-dispatch fallback
You are dispatched as reviewer quick mode sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Inputs

- run_id: `{{RUN_ID}}`
- run_dir: `{{RUN_DIR}}`
- diff_range: `{{DIFF_RANGE}}` (default `HEAD`)
- repo_path: `{{REPO_PATH}}`

## Goal

full mode 의 5-step reviewer pipeline (Step 1 parse_scope → Step 2 diff_collect → Step 3 classify_files → Step 4 rule3_check → Step 5 severity_assess → Step 6 reviewer_report) 을 단일 dispatch 로 압축. `REVIEW_REPORT.md` 1 doc 에 7 sections 모두 inline.

산출물 schema 는 full mode 와 동일 — 단일 pass 안에서 SCOPE.md parsing + git diff capture + allow/deny classification + Rule 3 surgical audit + severity grid + report rendering.

## Output sections (must include all)

`REVIEW_REPORT.md` 안에 다음 7 canonical sections 모두 포함 (full mode 와 동일 schema):

- `## 1. Summary` — verdict line (`merge-ready` / `needs-fix`) + 1-line 사유
- `## 2. Scope baseline` — SCOPE.md 의 allow-list / deny-list / completion criterion 요약
- `## 3. Diff inventory` — 변경된 파일 list + LOC 합계
- `## 4. Allow/Deny classification` — 각 파일 allow / deny / unknown 분류 + summary counts (allow_hit / allow_miss / deny_violation)
- `## 5. Surgical Changes audit` — Rule 3 위반 (요청 범위 밖 코드 임의 수정) — critical / major / minor counts + 증거
- `## 6. Severity assessment` — severity grid (critical/major/minor x allow/deny/rule3)
- `## 7. Recommendations` — verdict 사유 + 수정 액션 우선순위
- `## Mode usage note` — `mode=quick` 1-line marker

Verdict logic (deterministic, full mode 와 동일):
```python
verdict = "merge-ready" if (deny_violation == 0 AND allow_miss == 0 AND rule3_critical == 0) else "needs-fix"
```

## Save block

```python
python3 << 'EOF'
from pathlib import Path

run_id = "{{RUN_ID}}"
run_dir = Path("{{RUN_DIR}}")

# Sub-agent: 동일 dispatch 안에서 SCOPE.md 읽기 + git diff (cwd=repo_path)
# capture + 분류 + Rule 3 audit + severity grid 모두 1-pass 처리.
# 모든 <TBD: ...> 는 concrete 으로 채워야 함. Verdict 는 deterministic logic 으로.

body = f"""# REVIEW_REPORT

**Run ID**: {run_id}
**Mode**: quick (single-dispatch fallback — V4 Spike XIV paradigm hybrid)

## 1. Summary

**Verdict**: <TBD: merge-ready | needs-fix>

<TBD: 1-line reason>

## 2. Scope baseline

- allow-list: <TBD>
- deny-list: <TBD>
- completion criterion: <TBD>

## 3. Diff inventory

- files changed: <TBD count>
- LOC delta: +<TBD> / -<TBD>

<TBD: file list>

## 4. Allow/Deny classification

| File | Class | Reason |
|---|---|---|
| <TBD> | <allow/deny/unknown> | <TBD> |

- allow_hit: <TBD>
- allow_miss: <TBD>
- deny_violation: <TBD>

## 5. Surgical Changes audit

| Severity | Count | Notes |
|---|---|---|
| critical | <TBD> | <TBD> |
| major | <TBD> | <TBD> |
| minor | <TBD> | <TBD> |

## 6. Severity assessment

<TBD: grid summary — critical/major/minor x allow/deny/rule3>

## 7. Recommendations

<TBD: priority-ordered actions; deny-violations → critical Rule 3 → allow-misses → major Rule 3>

## Mode usage note

mode=quick — full mode 의 5-step reviewer pipeline 이 단일 dispatch 로 압축됨. precision 손실 가능. KEEPER_REPORT § "Mode usage" 에 카운트 기록.
"""

out = run_dir / "REVIEW_REPORT.md"
out.write_text(body, encoding="utf-8")
print(f"WROTE: {out}")
EOF
```

## Output discipline

Single trailing line: `WROTE: <abs path to REVIEW_REPORT.md>`. No prose, no banners. Errors via `ERROR: <reason>` on stdout — main follows §CRITICAL retry/abort/report.
