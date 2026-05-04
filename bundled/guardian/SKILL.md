---
name: "guardian"
description: "위험 명령 차단 + 디렉토리 freeze 가이드 문서를 작성하는 표준 번들 (V4 safety stage)"
stages: ["safety"]
grade: "standard"
---

# guardian — safety stage 표준 번들

V4 결정 #1 라인업의 safety stage. 사용자가 destructive 작업 직전에 의식적으로 거치는 *참조 가이드 문서* GUARDIAN.md 작성. V4는 hook 차단 시스템이 아님 — 자동 거부 X, 사용자 명시 체크리스트 작성 후 다른 번들에서 read해서 경고 표시.

## V4 #9 예외 적용 (메인 직접 IO)

V4 결정 #9 — "메인 Claude는 직접 작업 X. 단순 IO·AskUserQuestion만 예외".
guardian 워크플로 = (a) AskUserQuestion + (b) 템플릿 substitution + Write.
dispatch overhead가 실 작업보다 큼 → ALLOWED_PROMPT_FILES에 entry 추가 X. prompts/subagent/ 디렉토리 자체 없음.

**이 예외는 *분석적 추론 0*인 IO-only 번들에만 적용** — 다른 표준 번들에 dispatch 제거 시 정당화 사유로 차용 금지.

## 사용 시점

- 새 세션 시작 직후 (destructive 작업 *전*)
- 또는 builder / shipper / debugger 번들 작업 시작 직전 안전 가이드 셋업
- 사용자 컴에 gstack /careful 또는 /freeze 같은 보안 hook 시스템 있으면 그쪽 우선 — guardian은 가이드 문서만 제공

## 워크플로

### Step 1: 인터뷰 (메인 직접 — AskUserQuestion 묶음 ×2)

**1차 묶음 — freeze + 위험 명령:**
- Q1: "freeze 할 디렉토리 (이번 작업 동안 *수정 금지*)?"
- Q2: "이번 작업에서 *명시적 deny* 명령?"

**2차 묶음 — 계획:**
- Q3: "계획된 destructive 작업 (이번 세션 안 일어날 일)?"

옵션은 사용자 컨텍스트에 맞춰 동적 — "없음" 옵션 항상 포함.

### Step 2: 메인이 GUARDIAN.md 작성 (Write 직접)

메인 Claude가 `bundled/guardian/templates/GUARDIAN.md.template` read하고 4 placeholder ({{TIMESTAMP}}/{{FROZEN_DIRS}}/{{DENY_COMMANDS}}/{{PLANNED_DESTRUCTIVE}}) substitute 후 `{{RUN_DIR}}/GUARDIAN.md`로 Write.

- {{TIMESTAMP}}: 작성 시점 (ISO 8601, 예 `2026-05-04T15:00:00Z`)
- {{FROZEN_DIRS}}: 사용자 답변 (없으면 `없음`)
- {{DENY_COMMANDS}}: 사용자 답변 (없으면 `없음`)
- {{PLANNED_DESTRUCTIVE}}: 사용자 답변 (없으면 `없음`)

## 서브에이전트 매핑 표

| 단계 | role | 폴백 보장 |
|---|---|---|
| 1. 인터뷰 | (메인 직접) | — |
| 2. GUARDIAN.md 작성 | (메인 직접 — V4 #9 예외) | — |

## 산출물

- `<run_dir>/GUARDIAN.md` (활성 freeze + deny 명령 + 계획 작업 + 사용자 체크리스트 5 항목)

## 다른 번들과의 통합

builder / shipper / debugger 번들이 destructive 작업 직전 GUARDIAN.md read하면 콘솔에 1줄 경고 표시 (V5에서 자동 차단 hook 추가 후보). V4는 가이드 문서 + 사용자 의식만.

## V4 정체성 합치

- V4 #9 — 단순 IO·AskUserQuestion 예외 적용 (dispatch X)
- orchestrator-only 정신 유지 — 메인이 무거운 분석 안 함, IO만
- 다른 번들에 *읽기-전용* 알림 인프라 제공

## 비범위 (V4)

- 자동 차단 hook (PreToolUse) — V5
- 명령 패턴 자동 학습 — V5
- 백업 자동 실행 — V5
