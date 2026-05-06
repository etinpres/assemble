# plan-pack quick mode — single-dispatch fallback
You are dispatched as plan-pack quick mode sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Inputs

- run_id: `{{RUN_ID}}`
- run_dir: `{{RUN_DIR}}`
- task_summary: `{{TASK_SUMMARY}}`
- interview_answers: `{{INTERVIEW_ANSWERS}}` (PRD + ARCH + ADR + UI_GUIDE 인터뷰 압축본)

## Goal

full mode 의 13-step pipeline (Step 1~13: PRD interview → PRD draft → AC bash → PRD second-opinion → ARCH interview → ARCH dispatch → ADR interview → ADR dispatch → UI_GUIDE interview → UI_GUIDE dispatch → cross-doc review) 을 단일 dispatch 로 압축. 단일 `PRD.md` 산출물 안에 4 sections (Goals/Users/Architecture/UI guide) inline 으로 모두 포함.

산출물 schema 는 full mode 와 동일 — 단지 정밀도 (sections 본문 깊이, second-opinion verification, iteration loop) 가 1-pass 로 줄어들 뿐.

## Output sections (must include all)

`PRD.md` 안에 다음 sections 모두 포함 (full mode 4-doc 통합 form):

- `## Goals` — 무엇을 만드나, 사용자/시장 컨텍스트, 성공 기준 1줄 + AC bash 1줄 (full mode PRD `## Goals` + `## AC` 결합)
- `## Users` — 누가 쓰나, 우선순위 사용자 그룹 (full mode PRD `## Users`)
- `## Core features` — 3~5개 핵심 기능 + 3개 MVP exclusion (full mode PRD `## Core features`)
- `## Architecture` — Stack, Top-level directory, Architectural patterns, Data flow ≤3 steps, External services, Module boundaries (full mode ARCHITECTURE.md 6 sections inline 압축)
- `## Decisions (ADR)` — 3~5개 결정. 각각 `### Decision N: <title>` + Context / Decision / Reasoning / Tradeoffs / Rejected alternatives sub-headings (full mode ADR.md 통합)
- `## UI guide` — Visual identity, ≤5 brand color tokens, Typography (primary + supporting font), Component patterns ≥3, Priority screens ≥3 (full mode UI_GUIDE.md 5 sections inline)
- `## Mode usage note` — `mode=quick` 1-line marker. KEEPER_REPORT 가 추후 집계 시 사용.

각 section 의 본문은 full mode 와 동일 schema 를 따르되 sub-agent 가 1-pass 로 채움.

## Save block

```python
python3 << 'EOF'
import json
from pathlib import Path

run_id = "{{RUN_ID}}"
run_dir = Path("{{RUN_DIR}}")
task_summary = "{{TASK_SUMMARY}}"
interview_answers = """{{INTERVIEW_ANSWERS}}"""

# Build PRD.md body. Sub-agent fills with concrete content from inputs.
body = f"""# PRD — {task_summary}

**Run ID**: {run_id}
**Mode**: quick (single-dispatch fallback — V4 Spike XIV paradigm hybrid)

## Goals

<TBD: success criterion 1-line + AC bash 1-line>

## Users

<TBD: primary user + priority groups>

## Core features

<TBD: 3-5 features + 3 MVP exclusions>

## Architecture

- Stack: <TBD>
- Top-level directory: <TBD>
- Architectural patterns: <TBD>
- Data flow: <TBD ≤3 steps>
- External services: <TBD or "none">
- Module boundaries: <TBD>

## Decisions (ADR)

### Decision 1: <title>

- Context: <TBD>
- Decision: <TBD>
- Reasoning: <TBD>
- Tradeoffs: <TBD>
- Rejected alternatives: <TBD>

(repeat for 3-5 decisions)

## UI guide

- Visual identity: <TBD>
- Color tokens: <TBD ≤5 hex/named>
- Typography: <TBD primary + supporting>
- Component patterns: <TBD ≥3>
- Priority screens: <TBD ≥3>

## Mode usage note

mode=quick — full mode 의 13-step pipeline 이 단일 dispatch 로 압축됨. precision 손실 가능. KEEPER_REPORT § "Mode usage" 에 카운트 기록.
"""

# Sub-agent MUST replace every <TBD: ...> sentinel with concrete content
# from interview_answers before the write below.

out = run_dir / "PRD.md"
out.write_text(body, encoding="utf-8")
print(f"WROTE: {out}")
EOF
```

## Output discipline

Single trailing line: `WROTE: <abs path to PRD.md>`. No prose, no banners. Errors via `ERROR: <reason>` on stdout — main follows §CRITICAL retry/abort/report.
