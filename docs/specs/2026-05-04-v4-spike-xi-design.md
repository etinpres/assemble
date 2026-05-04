# V4 Spike XI Design — 3 standard bundles (idea-shaper / design-pack / guardian)

**Date**: 2026-05-04
**Status**: draft (pre-review)
**Parent**: `project_assemble_v4_spec.md`, `project_assemble_v4_spike_x.md`

---

## Scope

Single-track spike landing **3 standard-grade bundles** that complete the V4
spec § 결정 #1 lineup ("번들은 *전 stage·orthogonal cover*. 자급자족 보증").
Spike X closed the 6 self-sufficient ★ bundles (plan / execute / debug / review
/ verify / ship / meta). Spike XI fills the remaining 3 stages:

| stage | bundle | grade | 한 줄 역할 |
|---|---|---|---|
| discover | `idea-shaper` | 표준 | 아이디어 → 사용자/문제/wedge 1페이지 |
| design | `design-pack` | 표준 | 디자인 시스템 + 안티패턴 + UI 가이드 |
| safety | `guardian` | 표준 | 위험 명령 차단 + 디렉토리 freeze 가이드 |

After Spike XI, V4 결정 #1 라인업 10/10 채워짐. V4 출시 게이트 (Phase G 빈손 컴
dogfood — Spike XIII)에서 사용자가 모든 stage에 fallback 가능.

Ship gate: **B-16 dogfood** — 3 sub-runs (one per bundle), each self-execute.
Verifies (a) bundle is dispatchable (allowlist gate passes), (b) inventory
emits `bundled=true` + `★` prefix, (c) `_BUNDLED_DIR_TO_STAGE` map covers the
new stage. 12 AC PASS target.

### 표준 vs ★ 등급 차이 (V4 결정 #7 명시)

| 측면 | ★ 등급 (Spike IV-X) | 표준 등급 (Spike XI) |
|---|---|---|
| 파이프라인 | 4-step (extract → execute → classify → report) | 1-step single-dispatch (또는 메인 직접 IO) |
| Bash 권한 | sub-agent에 narrow scope grant (read-only git / canned subprocess) | **없음** (Read/Write만, 가능하면 dispatch도 단일) |
| 결정론적 verdict | 명시 (audit-clean / pass / ship-ready / etc.) | 산출물 자체만 (verdict 없음, 사용자 판단) |
| 산출물 | REPORT.md (7-section happy + 4-section abort) + 4+ JSON audit | 단일 .md (1-2 templates) |
| Codex retro | mandatory (Phase E2) | **선택** — 필요 시점 판단 (사용자 명시) |
| Overall code review | mandatory | mandatory (E1 superpowers:code-reviewer) |
| contracts.json | 3 entries (allowlist + verdict + artifact invariants) | 1 entry (allowlist + artifact 통합) |
| dogfood depth | 4 sub-runs (verdict 매트릭스) | 1 sub-run per bundle (happy만, 12 AC) |
| SECURITY.md | 별도 파일 (T1-T7 + mitigations + non-goals) | 보안 surface 있는 번들만 (guardian) |

표준 = 가벼움. ★ = 무겁고 검증 가능한 산출물 자가 강제.

### Out of scope

- ❌ Multi-language version bumping (Cargo / Gem) — V5 shipper 트랙
- ❌ `roles.json` 파일 도입 — Spike XII+ 후보
- ❌ /assemble eject 명령 — Spike XII
- ❌ Phase G 빈손 컴 dogfood — Spike XIII (외부 검증)
- ❌ ledger schema versioning — V5 (Codex retro F2 carryforward)
- ❌ multi-run concurrency safety — V5
- ❌ guardian이 hook 차단 시스템 (PreToolUse hook으로 위험 명령 자동 거부) — V5/V6
  - V4 guardian = **참조 가이드 문서**만. 실제 차단은 사용자/유저 hook 책임.
- ❌ design-pack이 Stitch / Figma MCP 연동 — V5
  - V4 design-pack = **AI 슬롭 안티패턴 표 + 디자인 시스템 1 페이지 가이드**만
- ❌ idea-shaper가 외부 검색 (web_search 호출) — V5
  - V4 idea-shaper = **AskUserQuestion 인터뷰 → IDEA.md 1페이지** 만
- ❌ Codex CLI / Gemini CLI 호환 — V4 비범위 (V5 어댑터 트랙)
- ❌ F4 perf collapse (reviewer ★ deterministic shell) — 별도 spike
- ❌ F-X1 / F-X2 — Spike X cleanup `b32ad0d`에서 종결

---

## Bundle 1 — idea-shaper (discover stage)

### 목적

사용자가 "X 같은 거 만들고 싶어" 식 모호한 아이디어를 가져왔을 때, AskUserQuestion
4개로 본질을 추출하고 IDEA.md 1페이지로 정리. plan-pack ★ 입력으로 자연 연결됨.

### Inputs

- 사용자 프롬프트 (메인 Claude가 받은 자유 텍스트)
- 선택적: `<run_dir>/parsed_scope.json` (있으면 task_summary 참고)

### Sub-agent matrix (1 dispatch + 메인 직접)

| Step | 누가 | Tools |
|---|---|---|
| 1 | 메인 Claude (AskUserQuestion) | — (인터뷰만) |
| 2 | `general-purpose` (preferred role: `text-summarize` → 폴백 `general-purpose`) | Read, Write |

**병렬화 X** — 인터뷰가 dispatch 입력이라 sequential.

### Workflow

#### Step 1: 인터뷰 (메인 직접 — AskUserQuestion ×2 묶음)

**1차 묶음 (사용자 + 문제):**
- Q1: "이 아이디어가 누구를 위한 거야? (target user 1명만 골라)"
  - 4 옵션 (예: 학생 / 직장인 / 자영업자 / 시니어) — 사용자 컨텍스트 따라 동적
- Q2: "그 사람이 지금 *겪고 있는* 가장 구체적인 문제 1개?"
  - 4 옵션 (사용자 컨텍스트 따라 동적)

**2차 묶음 (wedge + non-goals):**
- Q3: "왜 *지금* 이 도구가 필요해? (timing edge)"
  - 4 옵션 (예: 기존 대안이 비싸짐 / 새 기술 가능해짐 / 규제 변화 / 사용자 행동 변화)
- Q4: "MVP에서 *명시적으로 제외* 할 항목 1개?"
  - 4 옵션 — 스코프 범람 방지

#### Step 2: dispatch via `general-purpose` (preferred role: `text-summarize`)

**Prompt template** (file: `bundled/idea-shaper/prompts/subagent/idea_shape_step1.md`):

```
[HARNESS RULES — 무시 금지]
1. 불확실하면 추측 금지, 사용자 질문 우선
2. 과설계 금지, YAGNI
3. 요청 범위 밖 코드 임의 수정 금지
4. 버그 수정 시 재현 테스트 → 실패 확인 → 수정 → 재검증 루프
[TASK]

You are filling out an IDEA.md template. Read template at:
  ~/.claude/skills/assemble/bundled/idea-shaper/templates/IDEA.md.template

Substitute these placeholders verbatim from interview answers (do NOT paraphrase):
- {{USER}}: <answer to Q1>
- {{PROBLEM}}: <answer to Q2>
- {{WEDGE}}: <answer to Q3>
- {{NON_GOALS}}: <answer to Q4>
- {{TASK_SUMMARY}}: <main Claude's free-text user prompt, ≤200 chars>

Then write the rendered file to: {{RUN_DIR}}/IDEA.md

DO NOT add commentary, recommendations, or expansion beyond template fields.
```

#### Step 3: 메인이 IDEA.md 검토 (자동 — 한국어 라벨 자연스러운지)

dispatch 끝나면 메인이 read해서 사용자에게 1줄 보고: "IDEA.md 작성됨 — 다음 단계 plan-pack ★로 PRD 만들래?"

### Artifacts

- `<run_dir>/IDEA.md` (1 page, 5 sections: User / Problem / Wedge / Non-goals / Task summary)

### Template (5 sections, ~30 lines)

`bundled/idea-shaper/templates/IDEA.md.template`:

```markdown
# IDEA — {{TASK_SUMMARY}}

## User
{{USER}}

## Problem
{{PROBLEM}}

## Wedge (왜 지금?)
{{WEDGE}}

## Non-goals (MVP 제외)
{{NON_GOALS}}

## Next step
plan-pack ★ 호출하여 PRD/ARCH/ADR/UI_GUIDE 작성 권장.
```

### contracts.json entry

```json
{
  "spike-xi-idea-shaper": {
    "phrase": "spike XI: idea-shaper standard bundle",
    "checks": [
      "ALLOWED_PROMPT_FILES contains 'bundled/idea-shaper/prompts/subagent/idea_shape_step1.md'",
      "_BUNDLED_DIR_TO_STAGE['idea-shaper'] == 'discover' (BOTH harness.py + inventory.py)",
      "templates/IDEA.md.template exists and contains all 5 placeholders {{USER}}/{{PROBLEM}}/{{WEDGE}}/{{NON_GOALS}}/{{TASK_SUMMARY}}",
      "SKILL.md ≤120 lines (standard-grade budget)"
    ]
  }
}
```

---

## Bundle 2 — design-pack (design stage)

### 목적

PRD/IDEA에서 정해진 스코프 위에 **AI 슬롭 안티패턴 표** + 디자인 시스템 1페이지
가이드를 박아둠. plan-pack ★의 UI_GUIDE.md 보다 가벼운 1차 스케치 단계 또는
독립 사용 가능.

### Inputs

- 선택적: `<run_dir>/PRD.md` (plan-pack ★ 산출물 — 있으면 read)
- 선택적: `<run_dir>/IDEA.md` (idea-shaper 산출물 — 있으면 read)
- 둘 다 없으면 메인이 사용자에게 "어떤 프로젝트야?" 인터뷰

### Sub-agent matrix (1 dispatch + 메인 직접)

| Step | 누가 | Tools |
|---|---|---|
| 1 | 메인 Claude (AskUserQuestion) | — (인터뷰만) |
| 2 | `general-purpose` (preferred role: none, fallback only) | Read, Write |

### Workflow

#### Step 1: 인터뷰 (AskUserQuestion ×2 묶음)

**1차 묶음 (톤 + 색상):**
- Q1: "디자인 톤 1개 골라"
  - 옵션: 미니멀 모노 / 따뜻한 파스텔 / 굵은 컬러 블록 / 시니어 친화 큰 글자
- Q2: "주 색상 1개"
  - 옵션: 청색 (#2563eb) / 녹색 (#16a34a) / 회색 (#525252) / 따뜻한 오렌지 (#ea580c)

**2차 묶음 (컴포넌트 + 타이포):**
- Q3: "컴포넌트 라이브러리 선호"
  - 옵션: shadcn/ui / Tailwind 만 / iOS 네이티브 / Android Material
- Q4: "타이포 1개"
  - 옵션: Inter / Pretendard / SF Pro / 시스템 기본

#### Step 2: dispatch via `general-purpose`

**Prompt template** (`bundled/design-pack/prompts/subagent/design_draft_step1.md`):

```
[HARNESS RULES — 무시 금지]
1. 불확실하면 추측 금지, 사용자 질문 우선
2. 과설계 금지, YAGNI
3. 요청 범위 밖 코드 임의 수정 금지
4. 버그 수정 시 재현 테스트 → 실패 확인 → 수정 → 재검증 루프
[TASK]

You are filling DESIGN.md and ANTI_PATTERNS.md templates.

Read templates:
  ~/.claude/skills/assemble/bundled/design-pack/templates/DESIGN.md.template
  ~/.claude/skills/assemble/bundled/design-pack/templates/ANTI_PATTERNS.md.template

Substitute placeholders verbatim:
- {{TONE}}: <answer to Q1>
- {{COLOR_PRIMARY}}: <answer to Q2>
- {{COMPONENTS}}: <answer to Q3>
- {{TYPO}}: <answer to Q4>
- {{IDEA_OR_PRD_SUMMARY}}: 2-3 lines summary read from
  {{RUN_DIR}}/IDEA.md OR {{RUN_DIR}}/PRD.md (whichever exists; if both, prefer PRD).
  If neither exists, write "(no upstream design context)".

Write rendered files to:
- {{RUN_DIR}}/DESIGN.md
- {{RUN_DIR}}/ANTI_PATTERNS.md (template is content-fixed, only header substitutes
  TONE — body lists 8 anti-patterns verbatim from V4 spec § plan-pack 출하 default
  AI 슬롭 안티패턴 표).

DO NOT add gradient-text / glass morphism / backdrop-blur / "혁신적" / "차세대"
language. ANTI_PATTERNS.md is the deny list — do not violate it in DESIGN.md.
```

### Artifacts

- `<run_dir>/DESIGN.md` (디자인 시스템: 톤 / 색상 / 타이포 / 컴포넌트 / 레이아웃)
- `<run_dir>/ANTI_PATTERNS.md` (AI 슬롭 표 — 8 항목 고정)

### Templates

`bundled/design-pack/templates/DESIGN.md.template` (~40 lines):

```markdown
# DESIGN — {{IDEA_OR_PRD_SUMMARY}}

## Tone
{{TONE}}

## Color
- Primary: {{COLOR_PRIMARY}}
- Neutral: 회색 #525252 / #f5f5f5 (light) / #171717 (dark)

## Typography
{{TYPO}}, 본문 16px / 헤더 24-32px / 라벨 14px.

## Components
{{COMPONENTS}}

## Layout
- 모바일 우선, max-width 600px on desktop
- Spacing scale: 4 / 8 / 16 / 24 / 32 / 48
- Radius: 8 (carded), 4 (input)

## Reference
ANTI_PATTERNS.md를 항상 참조 — AI 슬롭 8 항목 deny list.
```

`bundled/design-pack/templates/ANTI_PATTERNS.md.template` (content-fixed):

```markdown
# AI 슬롭 안티패턴 — {{TONE}} 디자인 deny list

이 8개 패턴은 모든 화면에서 *사용 금지*:

1. **gradient-text** (`background-clip: text`) — 모든 헤더가 무지개색
2. **glass morphism / backdrop-blur** — 모든 카드가 투명 유리
3. **보라색 일색** — primary가 보라/네온이면 즉시 의심
4. **의미 없는 emoji 폭격** — 모든 라벨에 ✨/🚀/💎
5. **Lorem ipsum / placeholder 잔재** — "Lorem ipsum" / "Sample text" / "placeholder@example.com"
6. **TODO 미완성** — "TODO: 채워주세요" / "// add later"
7. **광고 카피체** — "혁신적인" / "차세대" / "AI 기반"
8. **회색 그라데이션 박스** — 콘텐츠 자리 채우기용 빈 회색 카드

reviewer ★ 번들이 review 단계에서 이 표를 자동 검증할 수 있음 (현재는 수동 점검).
```

### contracts.json entry

```json
{
  "spike-xi-design-pack": {
    "phrase": "spike XI: design-pack standard bundle",
    "checks": [
      "ALLOWED_PROMPT_FILES contains 'bundled/design-pack/prompts/subagent/design_draft_step1.md'",
      "_BUNDLED_DIR_TO_STAGE['design-pack'] == 'design' (BOTH harness.py + inventory.py)",
      "templates/DESIGN.md.template exists with placeholders {{TONE}}/{{COLOR_PRIMARY}}/{{TYPO}}/{{COMPONENTS}}/{{IDEA_OR_PRD_SUMMARY}}",
      "templates/ANTI_PATTERNS.md.template exists and contains all 8 anti-pattern entries verbatim",
      "SKILL.md ≤120 lines"
    ]
  }
}
```

---

## Bundle 3 — guardian (safety stage)

### 목적

사용자가 destructive 작업 (rm -rf / DROP TABLE / git reset --hard / etc.) 직전에
의식적으로 거치는 **참조 가이드 문서**. V4는 hook 차단 시스템이 아니므로 (사용자
gstack /careful 또는 /freeze가 그 역할), guardian은 GUARDIAN.md를 작성해서
"활성 freeze 디렉토리 + 위험 명령 목록 + 사용자가 의식적으로 거쳐야 하는 체크리스트"
를 박아둠. 다른 번들이 destructive 작업 시작 전 GUARDIAN.md read하여 경고 표시.

### Inputs

- 사용자가 직접 freeze하고 싶은 디렉토리 / 위험 명령 목록 / 계획된 destructive 작업

### Sub-agent matrix (메인 직접 — dispatch X)

| Step | 누가 | Tools |
|---|---|---|
| 1 | 메인 Claude (AskUserQuestion ×3) | — |
| 2 | 메인 Claude (Write — V4 #9 예외 적용: 단순 IO) | Write |

V4 결정 #9 ("번들 스킬은 *오케스트레이터-only*. 메인 Claude는 직접 작업 X.
단순 IO·AskUserQuestion만 예외") 의 *예외* 케이스. dispatch 비용보다 메인 직접
IO가 단순 — guardian은 인터뷰 답변을 템플릿에 주입하는 것뿐.

### Workflow

#### Step 1: 인터뷰 (AskUserQuestion ×2 묶음)

**1차 묶음 (freeze + 위험 명령):**
- Q1: "freeze 할 디렉토리 (이번 작업 동안 *수정 금지*)?"
  - 옵션: 없음 / `~/Documents` / `/etc` / 사용자 직접 입력
- Q2: "이번 작업에서 *명시적 deny* 명령?"
  - 옵션: 없음 / `git push --force` / `rm -rf` 류 / `kubectl delete` 류 / 사용자 직접 입력

**2차 묶음 (계획 + 백업):**
- Q3: "계획된 destructive 작업 (이번 세션 안 일어날 일)?"
  - 옵션: 없음 / DB 마이그레이션 / 프로덕션 배포 / 파일 대량 삭제 / 사용자 직접 입력

#### Step 2: 메인이 GUARDIAN.md 작성 (Write 직접)

메인 Claude가 템플릿 read하고 placeholder 채워서 `<run_dir>/GUARDIAN.md`로 write.

### Artifacts

- `<run_dir>/GUARDIAN.md` (활성 freeze + deny 명령 + 계획 작업 + 사용자 체크리스트)

### Template (~30 lines)

`bundled/guardian/templates/GUARDIAN.md.template`:

```markdown
# GUARDIAN — 안전 가이드 ({{TIMESTAMP}})

## Frozen directories (이 세션 *수정 금지*)
{{FROZEN_DIRS}}

## Deny commands (이 세션 *실행 금지*)
{{DENY_COMMANDS}}

## Planned destructive operations (사전 알림)
{{PLANNED_DESTRUCTIVE}}

## 사용자 체크리스트 (destructive 작업 직전 매번)

- [ ] 백업 (git commit / DB dump / file copy) 완료
- [ ] dry-run 실행 (`--dry-run` / `-n` 플래그)
- [ ] 영향 범위 확인 (touched files / affected rows count)
- [ ] 롤백 절차 1줄로 적을 수 있는가
- [ ] 사용자 (형) 본인 명시적 승인

## 다른 번들에 알림

builder / shipper / debugger 번들이 destructive 작업 직전 이 파일을 read하면
콘솔에 1줄 경고 표시 (V5에서 자동 차단 hook 추가 후보).
```

### contracts.json entry

```json
{
  "spike-xi-guardian": {
    "phrase": "spike XI: guardian standard bundle",
    "checks": [
      "_BUNDLED_DIR_TO_STAGE['guardian'] == 'safety' (BOTH harness.py + inventory.py)",
      "templates/GUARDIAN.md.template exists with placeholders {{FROZEN_DIRS}}/{{DENY_COMMANDS}}/{{PLANNED_DESTRUCTIVE}}/{{TIMESTAMP}}",
      "guardian has NO entries in ALLOWED_PROMPT_FILES (no sub-agent dispatch — main-direct IO per V4 #9 exception)",
      "SKILL.md ≤100 lines (no dispatch, simpler)"
    ]
  }
}
```

### V4 #9 예외 정당화

V4 #9 "메인 Claude는 직접 작업 X. 단순 IO·AskUserQuestion만 예외" — guardian의
유일한 작업이 (a) 인터뷰 + (b) 템플릿 substitution + Write. dispatch overhead가
실 작업보다 큼. dispatch 0번이라 ALLOWED_PROMPT_FILES에 entry 추가 안 함.

부작용: SKILL.md 자체에 4 placeholder substitution 인스트럭션 명시 (메인 Claude가
follow 가능하도록).

---

## Phase D — wiring (3 bundles 동시)

### server/harness.py 변경

```python
ALLOWED_PROMPT_FILES = {
    # ... existing 39 entries unchanged ...
    "bundled/idea-shaper/prompts/subagent/idea_shape_step1.md",   # +1 (Spike XI)
    "bundled/design-pack/prompts/subagent/design_draft_step1.md", # +1 (Spike XI)
    # guardian: NO entries (no dispatch)
}

_BUNDLES = (
    "plan-pack",
    "debugger",
    "builder",
    "reviewer",
    "verifier",
    "shipper",
    "keeper",
    "idea-shaper",   # +Spike XI
    "design-pack",   # +Spike XI
    "guardian",      # +Spike XI
)

_BUNDLED_DIR_TO_STAGE = {
    # ... existing 7 entries unchanged ...
    "idea-shaper": "discover",
    "design-pack": "design",
    "guardian": "safety",
}

_PROMPT_TO_STAGE = {
    # ... existing 39 unchanged ...
    "bundled/idea-shaper/prompts/subagent/idea_shape_step1.md": "discover",
    "bundled/design-pack/prompts/subagent/design_draft_step1.md": "design",
    # guardian has no prompts
}

# ORCHESTRATOR_ONLY_PROMPTS — no changes (no orchestrator helpers in standard bundles)
```

### server/inventory.py 변경

```python
_BUNDLED_DIR_TO_STAGE = {
    # ... existing entries unchanged (universal-defense convention sync) ...
    "idea-shaper": "discover",
    "design-pack": "design",
    "guardian": "safety",
}
```

### tests/contracts/contracts.json — +3 entries

위 각 번들 섹션에 정의됨 (3개 모두 phrase + checks 4-5개).

### Bidirectional integrity test (Spike X 패턴)

`set(_PROMPT_TO_STAGE.keys()) == set(ALLOWED_PROMPT_FILES)` 시간이 지나도 깨지지
않도록 CI 테스트로 enforce. Spike X에 이미 있음 — Phase D 후 자동 통과 (idea-shaper
+ design-pack 둘 다 양쪽 map에 들어감, guardian은 양쪽 모두 없음).

---

## B-16 dogfood

### 형태

Self-execute mode (Spike VIII/IX/X 패턴). 실제 Agent dispatch는 contracts test
+ Spike X 통합 테스트로 충분히 cover됨. B-16은 *번들 인프라*가 작동하는지만 검증.

### 3 sub-runs

#### Sub-run 1: idea-shaper happy

- 시나리오: 가상 사용자 입력 "택시 기사 가계부 같은 거 만들고 싶어"
- 검증:
  - inventory가 idea-shaper를 `bundled=true`로 emit
  - 메뉴에 `★ idea-shaper` prefix 표시
  - dispatch_prompt가 idea_shape_step1.md를 wrap하여 prompt 생성 — preamble v3
    sha 보존, [TASK] 본문에 4 placeholder 포함
  - allowlist gate 통과
  - 가상 dispatch 결과로 IDEA.md.template 5 placeholder 모두 substitute 가능
- 산출물: `<rid>/IDEA.md` (모킹 — 실제 dispatch 호출 안 함, 템플릿 substitution
  로컬 검증)

#### Sub-run 2: design-pack happy

- 시나리오: PRD.md 가상 셋업 + 4 인터뷰 답변 모킹
- 검증:
  - inventory bundled=true + ★ prefix
  - dispatch wrap 작동 — DESIGN + ANTI_PATTERNS 두 템플릿 read 가능
  - allowlist gate 통과 (design_draft_step1.md)
  - ANTI_PATTERNS.md 8 항목 verbatim 유지 (template content-fixed)
- 산출물: `<rid>/DESIGN.md` + `<rid>/ANTI_PATTERNS.md` (모킹)

#### Sub-run 3: guardian happy

- 시나리오: 사용자 freeze list 입력 (3 인터뷰 답변)
- 검증:
  - inventory bundled=true + ★ prefix
  - guardian은 ALLOWED_PROMPT_FILES에 entry 없음 (검증)
  - 메인 직접 Write 작동 — 4 placeholder substitution 후 GUARDIAN.md 생성
  - _BUNDLED_DIR_TO_STAGE['guardian'] == 'safety' (BOTH maps)
- 산출물: `<rid>/GUARDIAN.md`

### 12 AC

| # | 검증 항목 | 통과 기준 |
|---|---|---|
| 1 | 3 bundles inventory bundled=true | scan_skills() 결과에 모두 emit |
| 2 | 3 bundles 메뉴 ★ prefix | render_menu_block() 검증 |
| 3 | idea-shaper allowlist gate | _resolve_prompt_path('bundled/idea-shaper/...') 통과 |
| 4 | design-pack allowlist gate | 동상 |
| 5 | guardian no allowlist entry | ALLOWED_PROMPT_FILES에 'bundled/guardian/' 없음 |
| 6 | _BUNDLED_DIR_TO_STAGE harness.py 3 stages | discover/design/safety 모두 |
| 7 | _BUNDLED_DIR_TO_STAGE inventory.py 3 stages | 동상 (sync) |
| 8 | _PROMPT_TO_STAGE 2 entries | discover + design (guardian 제외) |
| 9 | preamble sha 변경 X | canonical preamble sha 8d22a29c... 보존 |
| 10 | bidirectional integrity | _PROMPT_TO_STAGE.keys() == ALLOWED_PROMPT_FILES |
| 11 | contracts.json 3 entries pass | tests/contracts/test_contracts.py 3 신규 ID 통과 |
| 12 | pytest baseline +N green | 759 baseline → ~770+ (신규 테스트 +10~15) |

### Wall-time budget

≤30s (3 sub-runs 모두 메모리 + JSON template 검증, 실 dispatch X). Spike X 0.26s
대비 자유.

### Out of B-16 scope

- 실 Agent dispatch (학습된 코드 신뢰 — contracts test 충분)
- 4-step pipeline correctness (표준 번들은 1-step)
- Codex retro adversarial (★ 번들 아니라 mandatory 안 함)

---

## Phase E — overall code review (E1)

### Scope

`superpowers:code-reviewer` 1회 invoke. 입력:
- spec + plan 인용
- 모든 commit (Phase A-D)
- 3 SKILL.md + 3 templates + 2 prompts
- harness.py / inventory.py wiring diff
- contracts.json 3 신규 entries

### 출력

`docs/dogfood/spike-xi-overall-review.md` — SHIP-READY 또는 carryforward 목록.

### Codex retro: 선택 (사용자 명시 — "★ 번들 아니라 Codex retro mandatory 안 함")

표준 번들은 보안 surface 없음 (Bash 0개, dispatch 단일 / 메인 IO):
- idea-shaper: 사용자 인터뷰 → IDEA.md substitution → 위험 0
- design-pack: 사용자 인터뷰 → DESIGN.md + ANTI_PATTERNS.md → 위험 0
- guardian: 사용자 인터뷰 → GUARDIAN.md → 가이드 문서, 차단 hook X → 위험 0

E1 review에서 critical issue 1+ 떠오르면 그 시점에 Codex retro 호출 결정. 기본
SKIP.

---

## Phase F — ship gate

1. CHANGELOG.md `[Unreleased] V4 Spike XI` 블록 + 모든 변경 enumerate
2. 메모리 `~/.claude/projects/-Users-yonghaekim-my-folder/memory/project_assemble_v4_spike_xi.md`
   작성 (Spike X 메모리 형식)
3. `MEMORY.md` index entry 추가
4. ship commit `docs(v4-spike-xi): ship — V4 Spike XI released, 3 standard bundles
   (idea-shaper / design-pack / guardian) — V4 결정 #1 라인업 10/10 완성`

---

## V4 정체성 보호 (변경 X)

- ✅ Spike I~X core contracts (verdict logic / 7-section / allowlist / RUN_DIR
   token / FIX-1 streaming + Codex F2/F3 process-group kill / extended tag
   validation / kill-on-EITHER-cap / Track B body-prefix fence)
- ✅ canonical preamble v3 sha unchanged: `8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9`
- ✅ ALLOW_LIST = {v1, v2, v3} unchanged (additive — only ALLOWED_PROMPT_FILES
   grows by 2 standard-bundle prompts; guardian adds 0)
- ✅ V3 concierge 메뉴 레이어 변경 X (★ prefix render 그대로, bundled-first sort
   그대로)
- ✅ 7개 self-sufficient ★ bundle prompts (plan-pack/debugger/builder/reviewer
   /verifier/shipper/keeper) 변경 X
- ✅ orchestrator-only V4 #9 — main never executes Bash; guardian이 메인 직접
   Write 하는 것은 V4 #9 명시 예외 ("단순 IO·AskUserQuestion만 예외")
- ✅ wrap_with_preamble + wrap_with_preamble_and_learnings (Track B) — 변경 X
   (idea-shaper + design-pack 두 prompt가 _PROMPT_TO_STAGE에 추가되면 자동으로
   Track B 학습 회수도 됨)
- ✅ scope_parser deterministic helper (B-13 strict grammar) 변경 X
- ✅ R4 net-delta logic (Spike X cleanup) — 변경 X
- ✅ STAGE_CATEGORY_PRIORITY tuple (Spike X cleanup F-X2) — 변경 X
- ✅ universal-defense convention: _BUNDLED_DIR_TO_STAGE 양쪽 동기 — 표준 번들
   3개도 동일 패턴
- ✅ ORCHESTRATOR_ONLY_PROMPTS 단일 source (server.harness)

## Spike XII candidates (deferred)

- `/assemble eject <bundle>` 명령 (번들 → 사용자 스킬 변환)
- `roles.json` 파일 도입 (메모리 spec 정의 → 실제 파일)
- F4 perf collapse (reviewer ★ deterministic shell)
- Spike XIII (Phase G 빈손 컴 dogfood — V4 출시 게이트)

## Source

- Parent: `project_assemble_v4_spec.md`
- Sibling: `project_assemble_v4_spike_x.md`
- 형식 참조: `docs/specs/2026-05-04-v4-spike-x-design.md`
