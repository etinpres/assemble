# Spike XIII B-19 — Lived Dogfood 캡쳐 가이드

> 별도 세션에서 형이 직접 운전하면서 따라가는 가이드. 비동기. 시간 날 때 진행.
>
> 목적은 V4 paradigm 약속이 *빈손 환경 + 사용자 perspective*에서 실제로 작동하는지
> 확인하는 것. 자동 probe(B-18)가 못 잡는 UX/판단/4원칙 위반은 인간 눈으로 잡는다.

---

## 목적

V4 결정 #6 release gate. Spike I~XII는 모두 자체 dogfood (assemble이 자기 자신을 사용)
였으니 외부 사용자 시야가 빠져 있었다. B-19는 빈손 ASSEMBLE_HOME + 작은 실제
프로젝트 한 건을 끝까지 끌고 가면서 매 stage 4항목씩 캡쳐 → 40 캡쳐 모음.
Verdict 분류 (SHIP / SHIP-WITH-CARRYFORWARDS / NEEDS-FIX / NEEDS-MAJOR-REWORK)는
캡쳐 가져온 후 메인 세션에서.

---

## Setup

별도 터미널 / 세션에서:

```bash
bash ~/.claude/skills/assemble/scripts/spike_xiii_b19_setup.sh
```

스크립트가 출력하는 `ASSEMBLE_HOME=...` 경로 받아서 같은 터미널에서:

```bash
ASSEMBLE_HOME=<path-from-script> claude
```

들어가면 *빈손* Claude Code 세션. assemble만 보이고 다른 스킬은 0개.

---

## Project 선택 (3 옵션)

| 옵션 | 설명 | 시간 | 추천 |
|---|---|---|---|
| 1 | **작은 CLI 도구 신규** (예: 마크다운 → plain text 변환기) | 30~60분 | ★ 권장 |
| 2 | 가상 PRD ("X 기능 추가" 시나리오, 실제 코드 X — 산출물만 검증) | 20~40분 | 시간 부족 시 |
| 3 | (메타) Spike XII 자체 재현 — recursive | 큼 | 비추 |

권장 = 옵션 1. 모든 stage가 자연스럽게 통과되고 산출물 품질도 평가 가능. 옵션 2는
산출물 템플릿 / wording 검증에는 충분하나 빌드/테스트/디버그 stage가 비어 있음.

---

## 시작 명령 예시

```
/assemble 마크다운 파일을 plain text로 변환하는 작은 CLI 도구 만들고 싶어
```

또는

```
/assemble <task description in 한국어 또는 English>
```

메인 Claude가 V3 concierge 흐름으로 응답하면서 stage 단위로 번들 추천 + 진행을
시작한다.

---

## 10 Stage 게이트 + 캡쳐 4항목 (총 40 캡쳐)

각 stage 끝낼 때마다 4항목 캡쳐. 양식 통일.

| # | Stage | Bundle | Grade | 핵심 게이트 |
|---|---|---|---|---|
| 1 | discover | idea-shaper | 표준 | IDEA.md 5 sections, 사용자 / 문제 / wedge / non-goals 명확 |
| 2 | plan | plan-pack | ★ | PRD/ARCH/ADR/UI_GUIDE 4종 일관성, AC bash 실행 가능 |
| 3 | design | design-pack | 표준 | DESIGN.md + ANTI_PATTERNS.md, AI 슬롭 회피 |
| 4 | execute | builder | ★ | TDD 흐름, surgical change boundary |
| 5 | debug | debugger | ★ | 가설→재현→이등분→근본원인, Iron Law |
| 6 | review | reviewer | ★ | diff vs SCOPE 비교, 객관 위험 0건 |
| 7 | verify | verifier | ★ | AC bash 실제 실행, exit code 기반 |
| 8 | ship | shipper | ★ | preflight pass, version bump, build, tag (local-only) |
| 9 | safety | guardian | 표준 | GUARDIAN.md 4 placeholder + 5 checkbox |
| 10 | meta | keeper | ★ | KEEPER_REPORT 7-section, audit-clean OR audit-flagged |

---

### Stage 1: discover — idea-shaper (표준)

**검증 게이트**: IDEA.md 5 sections (사용자 / 문제 / wedge / non-goals / 성공 신호)
모두 채워지고, 메인 Claude가 각 항목에 대해 질문 또는 추론 근거를 명확히 보여준다.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄):
   - 입력한 명령 그대로
   - main Claude의 응답 첫 5줄
2. **산출물 파일 경로**:
   - `~/.assemble/runs/<rid>/IDEA.md` 위치
   - `ls -lh` 크기
3. **막힘 / 어색한 UX**:
   - 자유 노트. 막힘 없으면 `smooth` 한 단어 OK.
4. **4원칙 위반 의심**:
   - 메인이 직접 작성? subagent 우회? AC 자기선언?
   - 위반 없으면 `none`.

---

### Stage 2: plan — plan-pack (★)

**검증 게이트**: PRD / ARCH / ADR / UI_GUIDE 4종 산출물 일관성. AC가 bash로 실제
실행 가능한 형태 (echo / test / pytest 등). MVP 제외 명확.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄)
2. **산출물 파일 경로**:
   - `~/.assemble/runs/<rid>/PRD.md`, `ARCH.md`, `ADR-*.md`, `UI_GUIDE.md`
   - 각 파일 크기
3. **막힘 / 어색한 UX**: 자유 노트 또는 `smooth`.
4. **4원칙 위반 의심**: 메인 직접 작성 / 추측 / etc. 또는 `none`.

---

### Stage 3: design — design-pack (표준)

**검증 게이트**: DESIGN.md + ANTI_PATTERNS.md. AI 슬롭 (gradient/glassmorphism/
generic placeholder) 회피 가이드 명확.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄)
2. **산출물 파일 경로**: `DESIGN.md`, `ANTI_PATTERNS.md` + 크기.
3. **막힘 / 어색한 UX**: 자유 노트 또는 `smooth`.
4. **4원칙 위반 의심**: 또는 `none`.

---

### Stage 4: execute — builder (★)

**검증 게이트**: TDD 흐름이 실제로 강제되는지 (test-first → red → green → refactor).
Surgical change boundary 준수 — diff가 SCOPE 안에 있는지.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄)
2. **산출물 파일 경로**:
   - `~/.assemble/runs/<rid>/BUILDER_LOG.md`
   - 실제 생성된 코드 파일 경로 + 크기
3. **막힘 / 어색한 UX**: 자유 노트 또는 `smooth`.
4. **4원칙 위반 의심**:
   - 메인이 코드를 직접 썼나? subagent 통해 builder 호출됐나?
   - 추측 코딩 사례 있나?

---

### Stage 5: debug — debugger (★)

**검증 게이트**: 가설 → 재현 → 이등분 → 근본원인 흐름. Iron Law (근본원인 없이
fix 금지) 준수.

> 옵션 1 (CLI 도구) 진행 시 자연스러운 버그가 안 생기면, 의도적으로 작은 버그를
> 심어두고 debugger 호출 가능. 또는 builder 단계에서 발생한 실제 빨강을 들고 와도 됨.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄)
2. **산출물 파일 경로**: `DEBUGGER_LOG.md` + 크기.
3. **막힘 / 어색한 UX**: 자유 노트 또는 `smooth`.
4. **4원칙 위반 의심**: 메인 직접 fix / 추측 fix / 곁가지 수정 등. 또는 `none`.

---

### Stage 6: review — reviewer (★)

**검증 게이트**: diff vs SCOPE 비교. 객관 위험 항목 (보안/스레드/무한루프 등)
0건 보고 또는 명확히 항목 list-up.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄)
2. **산출물 파일 경로**: `REVIEW_REPORT.md` + 크기.
3. **막힘 / 어색한 UX**: 자유 노트 또는 `smooth`.
4. **4원칙 위반 의심**: 또는 `none`.

---

### Stage 7: verify — verifier (★)

**검증 게이트**: PRD AC를 bash로 실제 실행. exit code 기반 verdict (PASS/FAIL).
verifier가 AC를 자기 선언으로 PASS 처리하면 안 됨.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄)
2. **산출물 파일 경로**: `VERIFY_REPORT.md` + 크기.
3. **막힘 / 어색한 UX**: 자유 노트 또는 `smooth`.
4. **4원칙 위반 의심**:
   - AC를 실제 bash 실행했나? 자기선언으로 PASS 했나?
   - exit code 기반 명시됐나?

---

### Stage 8: ship — shipper (★)

**검증 게이트**: preflight (테스트/lint/diff clean) → version bump → build → tag.
Local-only scope (push/publish 없음). 4-step pipeline w/ Bash.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄)
2. **산출물 파일 경로**: `SHIPPER_LOG.md` + 크기. tag 이름 / version.
3. **막힘 / 어색한 UX**: 자유 노트 또는 `smooth`.
4. **4원칙 위반 의심**: push 자동 호출? remote 건드림? 또는 `none`.

---

### Stage 9: safety — guardian (표준)

**검증 게이트**: GUARDIAN.md에 4 placeholder + 5 checkbox 채워짐. 위험 시나리오
명확.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄)
2. **산출물 파일 경로**: `GUARDIAN.md` + 크기.
3. **막힘 / 어색한 UX**: 자유 노트 또는 `smooth`.
4. **4원칙 위반 의심**: 또는 `none`.

---

### Stage 10: meta — keeper (★)

**검증 게이트**: KEEPER_REPORT 7-section 모두 채워짐. 트레이스 자가 점검 결과
audit-clean OR audit-flagged 명확. 학습 회수 (다음 run에 반영될 항목) 있으면 명시.

**캡쳐 4항목**:

1. **명령 입력 + 응답 헤더** (~5줄)
2. **산출물 파일 경로**: `KEEPER_REPORT.md` + 크기.
3. **막힘 / 어색한 UX**: 자유 노트 또는 `smooth`.
4. **4원칙 위반 의심**: 또는 `none`.

---

## 종료 후 정리

10 stages 완주 (또는 막힌 시점까지) 후:

```bash
rm -rf $ASSEMBLE_HOME
```

캡쳐 노트는 별도 파일에 저장하거나 클립보드에 보관. 메인 세션으로 복귀.

---

## 캡쳐 가져오기 (메인 세션 복귀)

이 세션 (메인) 으로 돌아와서 두 옵션 중 하나:

- **옵션 A — 텍스트 paste**: 40 캡쳐를 한 번에 paste. 또는 stage별로 나눠서 paste.
- **옵션 B — 단일 파일**: 텍스트 파일에 모은 후 path 알려주기. 메인 Claude가 읽음.

권장: 옵션 B (파일). 캡쳐 양이 많고 stage별 구조가 정확히 보존됨. 파일 경로
예시:

```
~/spike-xiii-b19-captures.md
```

---

## 시간 부족 시 priority

50분 다 못 빼면 우선 ★ stage들만:

1. plan ★ (Stage 2)
2. builder ★ (Stage 4)
3. debugger ★ (Stage 5)
4. reviewer ★ (Stage 6)
5. verifier ★ (Stage 7)

위 5개가 V4 paradigm 핵심 (자급자족 + 4원칙). 표준 등급 (idea-shaper / design-pack /
guardian) + shipper / keeper는 추후 보완 OK.

---

## 결함 발견 시

캡쳐 가이드 따라가다가 막히거나 어색한 점 보이면:

- 그냥 캡쳐만 한다 (4항목 노트로).
- *자기진단 / 원인 분석 X.*
- 분석은 메인 세션에서 형이 캡쳐 가져온 후 같이 한다.

별도 세션에서 디버깅 시도하면 시간만 날아가고 dogfood 검증 흐름이 깨진다.

---

## Refs

- Spec: `docs/specs/2026-05-06-v4-spike-xiii-design.md` § B-19
- Plan: `docs/plans/2026-05-06-v4-spike-xiii.md` § Phase B + § Phase C
- Setup script: `scripts/spike_xiii_b19_setup.sh`
- Phase A 결과 (B-18): `docs/dogfood/spike-xiii-b18.md`
