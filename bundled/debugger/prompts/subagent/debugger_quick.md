# debugger quick mode — single-dispatch fallback
You are dispatched as debugger quick mode sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Inputs

- run_id: `{{RUN_ID}}`
- run_dir: `{{RUN_DIR}}`
- symptom_summary: `{{SYMPTOM_SUMMARY}}`
- env: `{{ENV}}`
- last_known_good: `{{LAST_KNOWN_GOOD}}`
- tried_fixes: `{{TRIED_FIXES}}`

## Goal

full mode 의 6-step debugger pipeline (Step 2 reproducer → Step 3 hypotheses → Step 4 root cause + second-opinion → Step 5 fix patch + verifier → Step 6 BUG_REPORT integration + status flip) 을 단일 dispatch 로 압축. `DEBUGGER_LOG.md` (= full mode 의 `BUG_REPORT.md` 동치) 1 doc 에 5 sections 모두 inline.

산출물 schema 는 full mode 와 동일 — 단일 pass 안에서 repro.sh + verify.sh + BUG_REPORT.md 모두 작성하되 hypothesis iteration 은 1회로 제한.

## Output sections (must include all)

`DEBUGGER_LOG.md` (= `BUG_REPORT.md`) 안에 다음 sections 모두 포함 (full mode 5-section schema 보존):

- 프론트매터: `status: complete`
- `## TL;DR` — 1-line 진단 + fix 요약
- `## Symptom` — 한 줄 증상 + 재현 환경 (OS / runtime / deps / 마지막 정상 시점)
- `## Reproducer` — repro.sh 명령 + 실패 출력 증거
- `## Hypotheses` — 3~5개 falsifiable 가설, 우선순위 ranking
- `## Root cause` — 선택된 hypothesis + ≥2-alternative challenge 결과
- `## Fix & verification` — 패치 요약 + verify.sh 명령 + 통과 증거
- `## Mode usage note` — `mode=quick` 1-line marker

Sub-agent 는 동일 dispatch 안에서 repro.sh 와 verify.sh shell 도 함께 작성하고 마지막에 BUG_REPORT.md (== DEBUGGER_LOG.md) path 만 `WROTE:` 로 출력.

## Save block

```python
python3 << 'EOF'
from pathlib import Path

run_id = "{{RUN_ID}}"
run_dir = Path("{{RUN_DIR}}")
symptom_summary = "{{SYMPTOM_SUMMARY}}"
env = "{{ENV}}"
last_known_good = "{{LAST_KNOWN_GOOD}}"
tried_fixes = "{{TRIED_FIXES}}"

# Sub-agent: 본 dispatch 안에서 다음 3 파일 모두 작성
# 1. run_dir / "repro.sh"       (exits non-zero — symptom reproduces)
# 2. run_dir / "verify.sh"      (exits 0 — fix verified)
# 3. run_dir / "BUG_REPORT.md"  (final report — 5 sections + status: complete)
# Source-file 편집은 root-cause-driven minimal patch 만.
# 모든 <TBD: ...> 는 concrete 으로 채워야 함.

body = f"""---
status: complete
mode: quick
---

# BUG_REPORT — {symptom_summary}

**Run ID**: {run_id}

## TL;DR

<TBD: 1-line root cause + fix>

## Symptom

- summary: {symptom_summary}
- environment: {env}
- last known good: {last_known_good}
- tried fixes: {tried_fixes}

## Reproducer

```bash
bash repro.sh
```

<TBD: failing output excerpt>

## Hypotheses

1. <TBD: hypothesis 1 — falsifiable>
2. <TBD: hypothesis 2 — falsifiable>
3. <TBD: hypothesis 3 — falsifiable>

## Root cause

- selected hypothesis: <TBD>
- evidence: <TBD>
- alternatives ruled out: <TBD ≥2>

## Fix & verification

- patch summary: <TBD>
- verify.sh: passes (exit 0)

```bash
bash verify.sh
```

<TBD: passing output excerpt>

## Mode usage note

mode=quick — full mode 의 6-step debugger pipeline 이 단일 dispatch 로 압축됨. precision 손실 가능. KEEPER_REPORT § "Mode usage" 에 카운트 기록.
"""

out = run_dir / "BUG_REPORT.md"
out.write_text(body, encoding="utf-8")
print(f"WROTE: {out}")
EOF
```

## Output discipline

Single trailing line: `WROTE: <abs path to BUG_REPORT.md>`. No prose, no banners. Errors via `ERROR: <reason>` on stdout — main follows §CRITICAL retry/abort/report.
