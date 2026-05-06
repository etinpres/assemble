# Spike XIV B-20b — Lived Dogfood 캡쳐 가이드

> 별도 세션에서 형이 직접 운전하면서 따라가는 가이드. 비동기. 시간 날 때 진행.
>
> 목적은 V4 paradigm 약속 + 본 spike Phase A~E fix 5 항목이 *빈손 환경 + 사용자
> perspective* 에서 실제로 작동하는지 확인하는 것. 자동 probe (B-20a) 가 못 잡는
> UX / 판단 / 4원칙 위반 + paradigm hybrid 단축 모드 분기는 인간 눈으로 잡는다.

---

## 목적 (재시도 — Spike XIII NEEDS-FIX 후속)

V4 결정 #6 release gate 재시도. Spike XIII B-19 lived dogfood 90분 23초 완주 후
verdict 는 NEEDS-FIX (2 Critical + 4 Important). 본 spike Phase A~E 가 그 5 결함을
모두 닫았는지 lived 환경에서 재검증하는 단계가 B-20b.

기본 흐름은 Spike XIII B-19 와 동일하지만, 6 신규 capture point (C20~C25) 가
추가됐다. paradigm hybrid (default = full / opt-in = quick) 분기 + ASSEMBLE_HOME
자동 전파 + plan-pack iter1 default = yes + orthogonal stage 마킹을 명시적으로
관찰한다.

Verdict 분류 (SHIP-READY / SHIP-WITH-MINOR-CARRYFORWARDS / NEEDS-FIX /
NEEDS-MAJOR-REWORK) 는 캡쳐 가져온 후 메인 세션에서.

---

## Setup

별도 터미널 / 세션에서 (B-19 setup script 재사용 OK — 빈손 ASSEMBLE_HOME 만 만들면
충분):

```bash
bash ~/.claude/skills/assemble/scripts/spike_xiii_b19_setup.sh
```

스크립트가 출력하는 `ASSEMBLE_HOME=...` 경로 받아서 같은 터미널에서:

```bash
ASSEMBLE_HOME=<path-from-script> claude
```

들어가면 *빈손* Claude Code 세션. assemble 만 보이고 다른 스킬은 0개.

> Phase A fix 검증 포인트: 이 별도 세션 안에서 메인 Claude 가 sub-agent 디스패치
> 할 때, ASSEMBLE_HOME env 가 자동으로 [TASK] body 에 주입되어 서브에이전트가
> 같은 home 을 보는지 — **수동 prepend 없이**. C23 캡쳐.

---

## Project 선택 (3 옵션)

| 옵션 | 설명 | 시간 | 추천 |
|---|---|---|---|
| 1 | **작은 CLI 도구 신규** (예: 마크다운 → plain text 변환기, 50~80줄 bash/python) | 30~45분 | ★ 권장 |
| 2 | 가상 PRD ("X 기능 추가" 시나리오, 실제 코드 X — 산출물만 검증) | 20~40분 | 시간 부족 시 |
| 3 | (메타) Spike XIII 자체 재현 — recursive | 큼 | 비추 |

권장 = 옵션 1. 모든 stage 가 자연스럽게 통과되고 산출물 품질도 평가 가능. 옵션 2
는 산출물 템플릿 / wording 검증에는 충분하나 빌드 / 테스트 / 디버그 stage 가
비어 있다.

---

## ★ paradigm hybrid 모드 시연 — 중요

본 spike Phase B 가 ★ 번들에 mode-gate AskUserQuestion 을 도입했다 (full /
quick). C20~C22 캡쳐 정확도를 위해 **의도적으로 두 모드를 모두 골라봐야** 한다.

권장 패턴:

- **1번 ★ stage (예: plan)** → quick 골라보기 (단일 디스패치 흐름 관찰)
- **2번 ★ stage (예: builder)** → full 골라보기 (spec 명시 N-step pipeline 관찰)
- 나머지 ★ stage 는 본인 판단 (가급적 full 우선)

> 이유: R-F2 (spec § "Risk register") — 단축 모드 검증을 사용자가 적극적으로
> 안 골라주면 quick path 가 dead code 화 됐는지 lived 검증이 빈다.

---

## 시작 명령 예시

```
/assemble 마크다운 파일을 plain text 로 변환하는 작은 CLI 도구 만들고 싶어
```

또는

```
/assemble <task description in 한국어 또는 English>
```

메인 Claude 가 V3 concierge 흐름으로 응답하면서 stage 단위로 번들 추천 + 진행을
시작한다.

---

## 10 Stage 게이트 + 캡쳐 4항목 (총 40 캡쳐)

각 stage 끝낼 때마다 4항목 캡쳐. 양식 통일.

| # | Stage | Bundle | Grade | 핵심 게이트 | Spike XIV fix 관련 |
|---|---|---|---|---|---|
| 1 | discover | idea-shaper | 표준 | IDEA.md 5 sections, 사용자 / 문제 / wedge / non-goals 명확 | I4 (SKILL.md drift) |
| 2 | plan | plan-pack | ★ | PRD/ARCH/ADR/UI_GUIDE 4종 일관성, AC bash 실행 가능 | C2 (mode-gate) + I1 (iter1 default=yes) |
| 3 | design | design-pack | 표준 | DESIGN.md + ANTI_PATTERNS.md, AI 슬롭 회피 | I4 (SKILL.md drift) |
| 4 | execute | builder | ★ | TDD 흐름, surgical change boundary | C2 (mode-gate) |
| 5 | debug | debugger | ★ | 가설→재현→이등분→근본원인, Iron Law | C2 (mode-gate) |
| 6 | review | reviewer | ★ | diff vs SCOPE 비교, 객관 위험 0건 | C2 (mode-gate) |
| 7 | verify | verifier | ★ | AC bash 실제 실행, exit code 기반 | C2 (mode-gate) |
| 8 | ship | shipper | ★ | preflight pass, version bump, build, tag (local-only) | C2 (mode-gate) |
| 9 | safety | guardian | 표준 | GUARDIAN.md 4 placeholder + 5 checkbox | I3 (orthogonal stage 마킹) |
| 10 | meta | keeper | ★ | KEEPER_REPORT 7-section, audit-clean OR audit-flagged | C2 (mode-gate) + I3 (orthogonal stage 마킹) |

---

## C1 — Stage 1: discover — idea-shaper (표준)

**검증 게이트**: IDEA.md 5 sections (사용자 / 문제 / wedge / non-goals / 성공 신호)
모두 채워지고, 메인 Claude 가 각 항목에 대해 질문 또는 추론 근거를 명확히 보여
준다.

**Spike XIV 회귀 체크**: Phase E (I4 fix) 가 idea-shaper SKILL.md 의 stale
dispatch_prompt 시그니처를 정정했다 — 메인이 디스패치할 때 잘못된 인자
패턴 호출 흔적이 0 인지 확인 *(Spike XIV fixed — verify regression)*.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄):
   - 입력한 명령 그대로
   - main Claude 의 응답 첫 5줄
2. **산출물 파일 경로**:
   - `~/.assemble/runs/<rid>/IDEA.md` 위치
   - `ls -lh` 크기
3. **막힘 / 어색한 UX**:
   - 자유 노트. 막힘 없으면 `smooth` 한 단어 OK.
4. **4원칙 위반 의심**:
   - 메인이 직접 작성? 서브에이전트 우회? AC 자기선언?
   - 위반 없으면 `none`.

---

## C2 — Stage 2: plan — plan-pack (★) ⚡ Phase B + Phase C 검증

**검증 게이트**: PRD / ARCH / ADR / UI_GUIDE 4종 산출물 일관성. AC 가 bash 로 실제
실행 가능한 형태 (echo / test / pytest 등). MVP 제외 명확.

**Spike XIV 회귀 체크**:
- Phase B (C2/I2 fix) → 진입 시 mode-gate AskUserQuestion (full / quick) 발사
  되는지 *(C20 에서 별도 캡쳐)*.
- Phase C (I1 fix) → iter1 추천 default = "yes" 인지 (iter≤3 + new>0 or
  unresolved>0 시) *(C24 에서 별도 캡쳐)*.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄)
2. **산출물 파일 경로**:
   - `~/.assemble/runs/<rid>/PRD.md`, `ARCH.md`, `ADR-*.md`, `UI_GUIDE.md`
   - 각 파일 크기
3. **막힘 / 어색한 UX**: 자유 노트 또는 `smooth`.
4. **4원칙 위반 의심**: 메인 직접 작성 / 추측 / etc. 또는 `none`.

---

## C3 — Stage 3: design — design-pack (표준)

**검증 게이트**: DESIGN.md + ANTI_PATTERNS.md. AI 슬롭 (gradient / glassmorphism /
generic placeholder) 회피 가이드 명확.

**Spike XIV 회귀 체크**: Phase E (I4 fix) — design-pack SKILL.md 의 stale
`dispatch_prompt('design_draft_step1.md', run_id)` 시그니처가 정정됐는지
*(Spike XIV fixed — verify regression)*.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄)
2. **산출물 파일 경로**: `DESIGN.md`, `ANTI_PATTERNS.md` + 크기.
3. **막힘 / 어색한 UX**: 자유 노트 또는 `smooth`.
4. **4원칙 위반 의심**: 또는 `none`.

---

## C4 — Stage 4: execute — builder (★) ⚡ Phase B 검증

**검증 게이트**: TDD 흐름이 실제로 강제되는지 (test-first → red → green →
refactor). Surgical change boundary 준수 — diff 가 SCOPE 안에 있는지.

**Spike XIV 회귀 체크**: Phase B mode-gate — full 선택 시 8-step TDD 파이프라인
모두 디스패치되는지 (dispatches.jsonl row ≥ 8).

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄)
2. **산출물 파일 경로**:
   - `~/.assemble/runs/<rid>/BUILDER_LOG.md`
   - 실제 생성된 코드 파일 경로 + 크기
3. **막힘 / 어색한 UX**: 자유 노트 또는 `smooth`.
4. **4원칙 위반 의심**:
   - 메인이 코드를 직접 썼나? 서브에이전트 통해 builder 호출됐나?
   - 추측 코딩 사례 있나?

---

## C5 — Stage 5: debug — debugger (★) ⚡ Phase B 검증

**검증 게이트**: 가설 → 재현 → 이등분 → 근본원인 흐름. Iron Law (근본원인 없이
fix 금지) 준수.

> 옵션 1 (CLI 도구) 진행 시 자연스러운 버그가 안 생기면, 의도적으로 작은 버그를
> 심어두고 debugger 호출 가능. 또는 builder 단계에서 발생한 실제 빨강을 들고
> 와도 됨.

**Spike XIV 회귀 체크**: Phase B mode-gate — full / quick 선택지가 진입 시
실제로 보이는지.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄)
2. **산출물 파일 경로**: `DEBUGGER_LOG.md` + 크기.
3. **막힘 / 어색한 UX**: 자유 노트 또는 `smooth`.
4. **4원칙 위반 의심**: 메인 직접 fix / 추측 fix / 곁가지 수정 등. 또는 `none`.

---

## C6 — Stage 6: review — reviewer (★) ⚡ Phase B 검증

**검증 게이트**: diff vs SCOPE 비교. 객관 위험 항목 (보안 / 스레드 / 무한루프 등)
0건 보고 또는 명확히 항목 list-up.

**Spike XIV 회귀 체크**: Phase B mode-gate — 모드 선택 분기 발사.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄)
2. **산출물 파일 경로**: `REVIEW_REPORT.md` + 크기.
3. **막힘 / 어색한 UX**: 자유 노트 또는 `smooth`.
4. **4원칙 위반 의심**: 또는 `none`.

---

## C7 — Stage 7: verify — verifier (★) ⚡ Phase B 검증

**검증 게이트**: PRD AC 를 bash 로 실제 실행. exit code 기반 verdict (PASS /
FAIL). verifier 가 AC 를 자기 선언으로 PASS 처리하면 안 됨.

**Spike XIV 회귀 체크**: Phase B mode-gate — full 선택 시 4-step 파이프라인
완주, quick 선택 시 단일 디스패치만.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄)
2. **산출물 파일 경로**: `VERIFY_REPORT.md` + 크기.
3. **막힘 / 어색한 UX**: 자유 노트 또는 `smooth`.
4. **4원칙 위반 의심**:
   - AC 를 실제 bash 실행했나? 자기선언으로 PASS 했나?
   - exit code 기반 명시됐나?

---

## C8 — Stage 8: ship — shipper (★) ⚡ Phase B 검증

**검증 게이트**: preflight (테스트 / lint / diff clean) → version bump → build
→ tag. Local-only scope (push / publish 없음). 4-step 파이프라인 w/ Bash.

**Spike XIV 회귀 체크**: Phase B mode-gate.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄)
2. **산출물 파일 경로**: `SHIPPER_LOG.md` + 크기. tag 이름 / version.
3. **막힘 / 어색한 UX**: 자유 노트 또는 `smooth`.
4. **4원칙 위반 의심**: push 자동 호출? remote 건드림? 또는 `none`.

---

## C9 — Stage 9: safety — guardian (표준) ⚡ Phase D 검증

**검증 게이트**: GUARDIAN.md 에 4 placeholder + 5 checkbox 채워짐. 위험 시나리오
명확.

**Spike XIV 회귀 체크**: Phase D (I3 fix) — guardian 종료 후 메인이
`mark_stage('safety', ...)` 호출 시 ValueError 없이 progress.json 의
`orthogonal_stages.safety` 에 기록되는지 *(C25 에서 별도 캡쳐)*.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄)
2. **산출물 파일 경로**: `GUARDIAN.md` + 크기.
3. **막힘 / 어색한 UX**: 자유 노트 또는 `smooth`.
4. **4원칙 위반 의심**: 또는 `none`.

---

## C10 — Stage 10: meta — keeper (★) ⚡ Phase B + Phase D 검증

**검증 게이트**: KEEPER_REPORT 7-section 모두 채워짐. 트레이스 자가 점검 결과
audit-clean OR audit-flagged 명확. 학습 회수 (다음 run 에 반영될 항목) 있으면
명시.

**Spike XIV 회귀 체크**:
- Phase B mode-gate.
- Phase B (T3) → KEEPER_REPORT.md 에 Mode usage section 추가됐는지 (full / quick
  카운트, C22 캡쳐와 연계).
- Phase D (I3 fix) → keeper stage 종료 마킹 → `orthogonal_stages.meta` 기록.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄)
2. **산출물 파일 경로**: `KEEPER_REPORT.md` + 크기.
3. **막힘 / 어색한 UX**: 자유 노트 또는 `smooth`.
4. **4원칙 위반 의심**: 또는 `none`.

---

## C11~C19 — 일반 protocol cross-cutting capture

10 stage 캡쳐 외에 dogfood 전체에 걸쳐 한 번씩 점검하는 항목. 전체 run 끝나고
한꺼번에 노트.

- **C11** — 전체 stage 진행 도중 메인 Claude 가 `Bash` 도구를 직접 써서 산출물을
  생성한 흔적이 있는지 (빌드 / lint / 테스트 등 인프라 코드는 OK, 산출물 본문
  생성은 4원칙 #7 위반).
- **C12** — `~/.assemble/runs/<rid>/dispatches.jsonl` 의 row 갯수가 stage 수
  대비 적절한지 (full mode 기준 대략 ★ stage 7 × 4-7 = 28~49 + 표준 stage 3 × 1
  = 31~52 row).
- **C13** — `~/.assemble/runs/<rid>/progress.json` 의 stage 순서가 V3 concierge
  §1-§7 default flow 와 일치하는지.
- **C14** — 메뉴 옵션 (각 stage 시작 시 보이는 ToolPicker) 이 6개 이내인지 (M2
  = V5 후보, 본 spike 비범위지만 회귀 모니터링).
- **C15** — Spike XIII 누적 V5 backlog (M-XII4 / F-XII1~5 / F4 perf / roles.json
  등) 가 V4 출시 차단 수준 아닌지 — 출시 차단이면 verdict 영향.
- **C16** — 한국어 wording 어색함 (외래어 표기, "디스패치" / "서브에이전트" 등)
  자연스러운지 — preamble v3 rule 5 위반 의심 사례 모음.
- **C17** — 빈손 ASSEMBLE_HOME 외부 file system 침범 사례 0건인지 (`/tmp` 외
  쓰기 / `~` 직접 수정 등).
- **C18** — 전체 run 시간 (start → keeper 종료) 측정. Spike XIII B-19 = 90분
  23초 baseline.
- **C19** — verdict 자체평가 (사용자 직관) — `SHIP-READY` / `SHIP-WITH-MINOR-
  CARRYFORWARDS` / `NEEDS-FIX` / `NEEDS-MAJOR-REWORK` 한 단어 + 1줄 사유.

---

## C20~C25 — Spike XIV fix 검증 신규 캡쳐 (필수)

본 spike Phase A~E 가 Spike XIII 5 결함을 닫았는지 lived 환경에서 직접 관찰.
6 항목 모두 매 run 한 번씩 noted 되어야 함.

### C20 — ★ stage 진입 시 mode-gate AskUserQuestion 발사 여부

**검증 대상**: Phase B (C2/I2 fix). ★ stage (plan / builder / debugger /
reviewer / verifier / shipper / keeper) 진입할 때마다 메인 Claude 가
AskUserQuestion 으로 full / quick 메뉴를 보여주는지.

**노트 형식**:
- 7 ★ stage 중 mode-gate 가 발사된 stage 수: `<n>/7`
- 미발사 stage 가 있으면 stage 이름 + 메인 Claude 가 단축 결정한 흔적 (4원칙 #1
  위반 가능성).

### C21 — full mode 선택 시 spec 명시 N-step 파이프라인 모두 실행

**검증 대상**: Phase B 의 full mode 약속 — 각 ★ 번들 SKILL.md 에 명시된 N-step
파이프라인이 dispatches.jsonl row N+ 개로 실제 실행되는지.

**참조 N**:
- plan-pack: 4-7 (iteration 포함)
- builder: 8 step
- debugger: 5-7 step
- reviewer: 4-step
- verifier: 4-step
- shipper: 4-step
- keeper: 7-section

**노트 형식**:
- full mode 로 고른 ★ stage: 어떤 stage 인지 + spec N step 대비 dispatches.jsonl
  row 수 (`expected ≥N, actual <m>`).

### C22 — quick mode 선택 시 단일 디스패치 + KEEPER_REPORT mode=quick 카운트

**검증 대상**: Phase B 의 quick mode 약속 — quick 선택 시 통합 1 디스패치 + 후속
keeper 가 KEEPER_REPORT.md 의 Mode usage section 에서 mode=quick 카운트 정확한지.

**노트 형식**:
- quick mode 로 고른 ★ stage: 어떤 stage + dispatches.jsonl 해당 stage row 수
  (`expected = 1, actual = <m>`).
- KEEPER_REPORT.md Mode usage section grep: `mode=quick: <count>` 가 실제 quick
  선택 횟수와 일치하는지.

### C23 — ASSEMBLE_HOME 별도 세션 자동 전파

**검증 대상**: Phase A (C1 fix). 별도 세션 (`ASSEMBLE_HOME=<path> claude`) 안에서
메인 Claude 가 sub-agent 디스패치 시 [TASK] body 에 ASSEMBLE_HOME 이 자동
prepend 되어 서브에이전트가 같은 home 을 보는지 — **수동 명시 X**.

**노트 형식**:
- run 도중 메인이 사용자에게 "ASSEMBLE_HOME 명시해주세요" 요청한 횟수: `<n>`
  (기대값 0).
- `~/.assemble/runs/<rid>/` 가 *별도 세션 ASSEMBLE_HOME path* 안에 생성됐는지
  (default `~/.assemble` 침범 X 확인).

### C24 — plan-pack iter1 default = "yes"

**검증 대상**: Phase C (I1 fix). plan-pack Step 6 (recommendation policy) — iter1
종료 후 추가 iteration 추천 시 iter≤3 AND (new>0 OR unresolved>0) 조건이면 default
= "yes" 인지.

**노트 형식**:
- plan-pack iter1 종료 후 메인 Claude 가 보여준 AskUserQuestion default 값:
  `yes` / `no` / 그 외.
- iter≤3 + new>0 or unresolved>0 조건 충족 했는지 (PRD/ARCH 확인) — 충족했는데
  default 가 "no" 면 Spike XIV C24 회귀.

### C25 — orthogonal stage (safety / meta) 마킹 시 ValueError 없이 기록

**검증 대상**: Phase D (I3 fix). guardian / keeper stage 종료 후 `mark_stage(
'safety', ...)` 또는 `mark_stage('meta', ...)` 호출이 ValueError 없이 progress
.json 의 `orthogonal_stages.safety` / `orthogonal_stages.meta` 에 기록되는지.

**노트 형식**:
- guardian 종료 후 `cat ~/.assemble/runs/<rid>/progress.json | jq
  '.orthogonal_stages.safety'` 결과 (기대: 객체, status / tool_used / notes
  필드 보유).
- keeper 종료 후 동일하게 `.orthogonal_stages.meta` 확인.
- ValueError stack trace 흔적 0건인지 (transcript grep `ValueError`).

---

## 종료 후 정리

10 stages + C11~C19 cross-cutting + C20~C25 신규 캡쳐 완주 (또는 막힌 시점까지)
후:

```bash
rm -rf $ASSEMBLE_HOME
```

캡쳐 노트는 별도 파일에 저장하거나 클립보드에 보관. 메인 세션으로 복귀.

---

## 캡쳐 가져오기 (메인 세션 복귀)

이 세션 (메인) 으로 돌아와서 두 옵션 중 하나:

- **옵션 A — 텍스트 paste**: 25 capture point (C1~C25) 를 한 번에 paste. 또는
  stage 별로 나눠서 paste.
- **옵션 B — 단일 파일**: 텍스트 파일에 모은 후 path 알려주기. 메인 Claude 가
  읽음.

권장: 옵션 B (파일). 캡쳐 양이 많고 stage 별 + cross-cutting + Spike XIV 신규
구조가 정확히 보존됨. 파일 경로 예시:

```
~/spike-xiv-b20b-captures.md
```

---

## 시간 부족 시 priority

90분 다 못 빼면 우선순위:

1. **C20~C25 (Spike XIV 신규)** — 본 spike 검증 핵심. 무조건 캡쳐.
2. plan ★ (C2)
3. builder ★ (C4)
4. debugger ★ (C5)
5. reviewer ★ (C6)
6. verifier ★ (C7)

위 5 ★ stage + C20~C25 가 V4 paradigm hybrid 핵심 (자급자족 + 4원칙 + mode-gate
+ ASSEMBLE_HOME 전파 + iter1 default + orthogonal stage). 표준 등급 (idea-shaper
/ design-pack / guardian) + shipper / keeper / C11~C19 cross-cutting 은 추후
보완 OK.

---

## 결함 발견 시

캡쳐 가이드 따라가다가 막히거나 어색한 점 보이면:

- 그냥 캡쳐만 한다 (4항목 노트 + 신규 C20~C25 노트 형식대로).
- *자기진단 / 원인 분석 X.*
- 분석은 메인 세션에서 형이 캡쳐 가져온 후 같이 한다.

별도 세션에서 디버깅 시도하면 시간만 날아가고 dogfood 검증 흐름이 깨진다.

특히 본 spike fix 5 항목 (C1, C2/I2, I1, I3, I4) 의 *재발* 발견 시 — 별도 세션
에서 wrap-around 시도 금지. 메인 세션에서 fix design 자체 재검토 트리거.

---

## V4 release gate 통과 조건 (재시도)

본 가이드 verdict 가 release gate 통과 / 실패 결정. 조건:

| 결과 | verdict | 후속 |
|---|---|---|
| ✅ 통과 | B-20a 18/18 PASS (T8 done) **AND** B-20b verdict ∈ {SHIP-READY, SHIP-WITH-MINOR-CARRYFORWARDS} **AND** Spike XIV fix 5 항목 (C1, C2/I2, I1, I3, I4) 재발 0 | V4 출시 |
| ❌ 실패 | B-20b verdict ∈ {NEEDS-FIX, NEEDS-MAJOR-REWORK} **OR** fix 5 항목 중 어느 하나 재발 | Spike XV+ cleanup spike(s) 후 재시도. 재발 시 fix design 자체 재검토. |

> Spike XIII NEEDS-FIX 학습 — 본 spike 가 Phase A~E 로 5 결함을 닫았다고 *주장*
> 하지만 lived 환경 행동까지 안 통과하면 SHIP-READY X. C20~C25 가 그 검증의
> 사실상 전부.

---

## Refs

- Spec: `docs/specs/2026-05-06-v4-spike-xiv-design.md` § Phase F + § B-20b lived
  dogfood 가이드
- Plan: `docs/plans/2026-05-06-v4-spike-xiv.md` § T9 + § T10
- Setup script (재사용): `scripts/spike_xiii_b19_setup.sh`
- Phase A 결과 (B-20a 자동 probe, T8): tests/dogfood/spike_xiv_b20a.py
- Spike XIII B-19 가이드 (base 템플릿): `docs/dogfood/spike-xiii-b19-capture-guide.md`
- Spike XIII B-19 verdict (NEEDS-FIX): `project_assemble_v4_spike_xiii.md`
