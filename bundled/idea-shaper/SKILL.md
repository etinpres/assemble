---
name: "idea-shaper"
description: "모호한 아이디어를 사용자/문제/wedge 1페이지로 정리하는 표준 번들 (V4 discover stage)"
stages: ["discover"]
grade: "standard"
---

# idea-shaper — discover stage 표준 번들

V4 결정 #1 라인업의 discover stage. 사용자가 "X 같은 거 만들고 싶어" 식 모호 아이디어를 가져오면 AskUserQuestion 4개로 본질을 추출하고 IDEA.md 1페이지로 정리.

## 사용 시점

- 새 프로젝트 brainstorm 직후, plan-pack ★ 호출 *전*
- 또는 plan-pack 단독 사용 가능 (사용자가 IDEA.md 직접 손으로 작성)

## 워크플로

### Step 1: 인터뷰 (메인 Claude 직접 — AskUserQuestion 묶음 ×2)

**1차 묶음 — 사용자 + 문제:**
- Q1: "이 아이디어가 누구를 위한 거야? (target user 1명만 골라)"
- Q2: "그 사람이 지금 *겪고 있는* 가장 구체적인 문제 1개?"

**2차 묶음 — wedge + non-goals:**
- Q3: "왜 *지금* 이 도구가 필요해? (timing edge)"
- Q4: "MVP에서 *명시적으로 제외* 할 항목 1개?"

옵션은 사용자 컨텍스트 기반으로 동적 생성. 4-옵션 강제 X — 의미 모호하면 더 길어도 풀어서 표기.

### Step 2: dispatch via `general-purpose` (preferred role: `text-summarize`)

dispatch_prompt('bundled/idea-shaper/prompts/subagent/idea_shape_step1.md', run_id) 호출.

번들 prompt가 자동으로 harness preamble v3 + Track B 학습 회수 fence를 prepend. 메인 Claude는 dispatch 결과만 받음.

sub-agent는 IDEA.md.template를 read하여 4 placeholder + {{TASK_SUMMARY}}를 substitute한 후 `{{RUN_DIR}}/IDEA.md`로 write.

### Step 3: 후속 알림

dispatch 완료 후 메인이 사용자에게 1줄: "IDEA.md 작성됨. 다음 단계 plan-pack ★로 PRD/ARCH/ADR/UI_GUIDE 만들래?"

## 서브에이전트 매핑 표

| 단계 | role | 폴백 보장 |
|---|---|---|
| 1. 인터뷰 | (메인 직접) | — |
| 2. IDEA.md 작성 | text-summarize | general-purpose + 컨텍스트 "한국어 1페이지 IDEA 문서 작성, 템플릿 placeholder 그대로 substitute" |

## 산출물

- `<run_dir>/IDEA.md` (5 sections: User / Problem / Wedge / Non-goals / Task summary)

## V4 정체성 합치

- ✅ V4 #9 orchestrator-only — 인터뷰 + dispatch만, 메인 무거운 작업 X
- ✅ V4 #13 역할 명시만 — text-summarize 사전 정의 / fallback general-purpose
- ✅ harness 4원칙 prepend — preamble v3 통해 자동 (Track B 학습도 자동)

## 비범위 (V4)

- ❌ 외부 검색 (web_search) — V5
- ❌ 시장 조사 / 경쟁자 분석 — V5
- ❌ wedge 자동 생성 — 사용자 인터뷰 필수
