---
name: "design-pack"
description: "디자인 시스템 + AI 슬롭 안티패턴 + UI 가이드를 1페이지에 정리하는 표준 번들 (V4 design stage)"
stages: ["design"]
grade: "standard"
---

# design-pack — design stage 표준 번들

V4 결정 #1 라인업의 design stage. PRD/IDEA에서 정해진 스코프 위에 디자인 시스템 1페이지 가이드 + AI 슬롭 안티패턴 표를 박아둠. plan-pack ★의 UI_GUIDE.md보다 가벼운 1차 스케치 단계 또는 독립 사용 가능.

## 사용 시점

- PRD 또는 IDEA.md 작성 후, builder ★ 호출 *전*
- 또는 독립 사용 — 디자인 시스템만 빠르게 박아두고 싶을 때
- 사용자 컴에 design-consultation 같은 사용자 스킬 있으면 그쪽 우선 — 번들은 폴백

## 워크플로

### Step 1: 인터뷰 (메인 Claude 직접 — AskUserQuestion 묶음 ×2)

**1차 묶음 — 톤 + 색상:**
- Q1: "디자인 톤 1개 골라"
- Q2: "주 색상 1개 (hex 또는 자유 입력)"

**2차 묶음 — 컴포넌트 + 타이포:**
- Q3: "컴포넌트 라이브러리 선호"
- Q4: "타이포 1개"

옵션은 사용자 컨텍스트(웹/iOS/Android/CLI 등)에 맞춰 동적 생성.

### Step 2: dispatch via `general-purpose`

dispatch_prompt('design_draft_step1.md', run_id) 호출.

번들 prompt가 자동으로 harness preamble v3 + Track B 학습 회수 fence를 prepend. 메인 Claude는 dispatch 결과만 받음.

sub-agent는 DESIGN.md.template + ANTI_PATTERNS.md.template 두 개를 read하여 5 placeholder({{TONE}}/{{COLOR_PRIMARY}}/{{COMPONENTS}}/{{TYPO}}/{{IDEA_OR_PRD_SUMMARY}})를 substitute한 후 `{{RUN_DIR}}/DESIGN.md` + `{{RUN_DIR}}/ANTI_PATTERNS.md` 두 파일로 write.

ANTI_PATTERNS.md 본문은 content-fixed (8 항목 verbatim) — `{{TONE}}` 헤더만 substitute.

### Step 3: 후속 알림

dispatch 완료 후 메인이 사용자에게 1줄: "DESIGN.md + ANTI_PATTERNS.md 작성됨. 다음 단계 builder ★ 호출하여 구현 시작 권장."

## 서브에이전트 매핑 표

| 단계 | role | 폴백 보장 |
|---|---|---|
| 1. 인터뷰 | (메인 직접) | — |
| 2. DESIGN/ANTI_PATTERNS 작성 | general-purpose | 표준 컨텍스트 — "디자인 시스템 1페이지 + 8 안티패턴 표 templates 그대로 substitute" |

## 산출물

- `<run_dir>/DESIGN.md` (디자인 시스템: 톤/색상/타이포/컴포넌트/레이아웃)
- `<run_dir>/ANTI_PATTERNS.md` (AI 슬롭 8 항목 deny list, content-fixed)

## V4 정체성 합치

- V4 #9 orchestrator-only — 인터뷰 + dispatch만, 메인 무거운 작업 X
- V4 #13 역할 명시만 — general-purpose 표준
- harness 4원칙 prepend — preamble v3 통해 자동 (Track B 학습도 자동)
- ANTI_PATTERNS deny list가 reviewer ★의 review 단계에서 검증 가능 (현재 수동, V5 자동화 후보)

## 비범위 (V4)

- Stitch / Figma MCP 연동 — V5
- 자동 색상 팔레트 생성 — V5
- 디자인 토큰 변환 (Tailwind config 등) — V5
