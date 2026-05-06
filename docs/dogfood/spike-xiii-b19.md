# V4 Spike XIII B-19 — Lived Dogfood 분석 + 결함 분류

**Date**: 2026-05-06
**Run**: 2026-05-06 09:46 ~ 11:16 (90분 23초)
**rid**: `20260506-094612-0bde`
**Project**: 마크다운 → plain text CLI 도구 (Python stdlib only)
**Captures source**: `/tmp/spike-xiii-b19-transcript.txt` (1286 lines, RTF→TXT)
**User strategy**: 모든 메뉴 옵션에서 의도적으로 1번 (default-recommended) 선택 — 어셈블의 default 정책이 실제 최선인지 검증 목적

---

## 운영 환경 한계 (사전 인지)

본 dogfood는 형이 별도 Claude Code 세션 진입을 시도했으나 ASSEMBLE_HOME 환경변수가 sub-agent dispatch로 전파되지 않아 **메인 세션 시뮬레이션**으로 진행됨. 즉 V4 결정 #6의 원래 의도 (별도 fresh 환경)는 부분적으로만 구현. 그러나 결함 분류에 영향: C1 자체가 결함이라는 점 명확.

---

## Verdict — **NEEDS-FIX (Spike XIV cleanup 후 재검증)**

**V4 ship 차단 사유 (Critical 2건)**:
1. **C1 ASSEMBLE_HOME env 비전파** — V4 결정 #6 핵심인 빈손 환경 격리가 setup script로 강제 안 됨
2. **C2 V4 #11 parallel violation 시스템적** — 7개 ★ stage 모두 통합 1 dispatch. ★ paradigm 자체가 메인 컨텍스트 budget 한계로 *작동 불가*. 메인이 자가 판단으로 spec 워크플로 단축

**산출물 자체는 합격**:
- 8/8 sequential + 2 orthogonal stages done
- md2txt.py 5.4K (실제 작동, 31 tests pass, AC 3/3 PASS)
- 21 files generated (4종 docs + reports + tests + executables)
- harness preamble v3 prepend 정상
- review/verify 객관 verdict (자기선언 PASS X)
- shipper push/publish 0건 (local-only 준수)
- keeper 자체 audit 작동 (V4 #11 violation 명시 capture)

V4 paradigm 약속과 실제 동작의 gap이 결함의 핵심.

---

## 결함 분류

### Critical (ship 차단)

#### C1. ASSEMBLE_HOME env 비전파 (RUNTIME)

**문제**: 별도 Claude Code 세션에 `ASSEMBLE_HOME=<path> claude` 명령으로 진입해도 환경변수가 메인 프로세스에서 sub-agent dispatch로 전파되지 않음.

**증거** (transcript line 31-36, 304):
- 메인 세션 자체에 `ASSEMBLE_HOME` 미설정 (`echo "from-bash-env: ${ASSEMBLE_HOME:-(unset)}"` → `(unset)`)
- 매 dispatch prompt 본문에 `os.environ['ASSEMBLE_HOME'] = '<abs path>'` 첫 줄 prepend 명시 필요
- 빈손 dogfood 환경 핵심 한계

**영향**:
- V4 결정 #6 "빈손 컴 dogfood가 V4 출시 게이트"의 본질인 환경 격리가 setup script만으로는 강제 안 됨
- sub-agent가 메인 머신 ~/.claude/runs/로 write 시도 → 빈손 환경 격리 깨짐
- 진짜 빈손 컴 dogfood (Spike XIII 의도) 운영 자체가 어려움

**Spike XIV fix 후보**:
- (a) setup script가 `env -i` 격리로 진입 + ASSEMBLE_HOME 명시 export
- (b) harness preamble v3에 `os.environ['ASSEMBLE_HOME']` auto-prepend (현 ASSEMBLE_HOME 값을 dispatch prompt 본문에 자동 주입)
- (c) `wrap_with_preamble` 함수가 호출 시점 env 캡쳐 후 prepend

(b) 또는 (c) 권장. setup script만으로는 fragile.

#### C2. V4 #11 parallel violation 시스템적 (★ paradigm 무력화)

**문제**: 7개 ★ stage 모두 spec 명시 4~7 sub-agent 병렬 dispatch 대신 통합 1 dispatch로 단축. 메인이 *자가 판단*으로 spec 워크플로 우회.

**증거** (transcript verbatim):
- Line 404: `plan stage 풀 검증은 시간 한계. ARCH/ADR/UI_GUIDE는 단축 인터뷰 후 1-shot dispatch + Step 9 cross-doc + Step 6 no.`
- Line 503: `iter1 simplification — 4-way parallel 대신 1 sub-agent 통합 dispatch로 시간/컨텍스트 압축. spec 위반 capture.`
- Line 643: `builder 단축 통합 dispatch (6 dispatch → 1).`
- Line 672, 688, 704, 720, 737: debugger/reviewer/verifier/shipper/guardian+keeper 모두 통합 dispatch
- 캡쳐 파일 C2 명시 (line 800-803): "spec: 각 ★ bundle은 4~7 sub-agent dispatch... dogfood 시간/메인 컨텍스트 한계로 통합 1 dispatch"

**영향**:
- harness 4원칙 #1 (추측 금지, 사용자 질문 우선) 시스템적 위반 — 메인이 사용자에게 묻지 않고 단축 결정
- V4 #11 parallel + V4 #9 orchestrator-only 모두 위반
- dispatches.jsonl audit row 누락 (4-row invariant 깨짐)
- ★ 등급의 "verdict 명시" 약속이 표면적 (산출물은 정상이지만 spec follow 부분적)
- **★ paradigm 자체가 메인 컨텍스트 budget 한계로 *작동 불가*** = V4 약속의 fundamental 한계

**Spike XIV fix 후보**:
- (a) ★ 번들 SKILL.md에 "단축 금지" 명시 + 메인 자가 판단 차단 강화 (orchestrator-only 정신)
- (b) Bash hook이 ★ stage에서 단일 통합 dispatch 패턴 감지 → warn 또는 차단
- (c) 시간/컨텍스트 budget 정책 추가 — 사용자에게 미리 묻기 (4원칙 #1 자체 강화)
- (d) ★ paradigm 자체 단순화: "★ = optional, 빈손 환경에서는 단축 권장" 명시 (paradigm retreat — 비추)

(c) 권장. 단축 결정 *전*에 사용자에게 명시적으로 묻기 (AskUserQuestion). harness preamble v3에 4원칙 #1 강화 wording.

### Important (ship 차단 가능)

#### I1. iter1 default = "no" (plan-pack ★ multi-iteration 약속 위배)

**문제**: plan-pack Step 6 iteration prompt에서 default-recommended 옵션이 "no — 종료, dogfood 시간 한계". yes는 2번. 그러나 plan-pack ★ 핵심 가치가 "iteration 3~7회"라서 1차 iteration 후 default = yes여야 paradigm 부합.

**증거** (transcript line 480-482, 511-512, 형 직접 발견):
```
· 네 문서 작성 완료 — PRD.md, ARCHITECTURE.md, ADR.md, UI_GUIDE.md.
  한 차례 반복 진행할까? (Step 9: 5 NEW findings) → yes (사용자 명시 선택)
[default cursor was on "no"]

· 반복을 계속할까? (iter1: resolved=5 unresolved=0 new=1) → no (Recommended, dogfood 시간 한계)
```

**iter1 stop condition violation**: resolved=5 (RESOLVED 80% 충족) + new=1 (NEW > 0) → spec은 iter2 진행 권장. default가 그러나 "no"로 표시. 형이 만약 1번 default 따랐다면 plan iteration 가치 자체 무력화.

**Spike XIV fix**: plan-pack SKILL.md Step 6 prompt 정정. iter≤3 + (RESOLVED < 80% OR NEW > 0)이면 default = yes. 또한 "dogfood 시간 한계" 사유는 default 추천 문구에서 제거.

#### I2. interview 단축 패턴 (메인 자가 결정)

**문제**: Stage 2 (plan) Step 7/10/12 interview, Stage 3 (design) interview, Stage 4 (execute) Step 1 interview 모두 spec 명시 묶음 → 1 묶음 단축. 메인이 사용자에게 묻지 않고 자가 판단.

**증거** (transcript):
- Stage 2 ARCH interview spec 2 calls of 3 = 6 questions → 단축 1 묶음 4 답
- Stage 2 ADR interview spec Call 5 + 3 separate Call 6 = 4 round trip → 단축 1 묶음 3 답
- Stage 2 UI_GUIDE interview spec 2 calls of 3 → 단축 1 묶음 3 답
- Stage 3 design interview 4 question → 1 묶음
- Stage 4 builder interview spec ×2 → 1 묶음

**영향**: finding rationale 깊이 손실 가능. C2와 같은 root cause (메인 자가 단축).

**Spike XIV fix**: C2 fix와 같이 처리. 메인 단축 결정 시 사용자에게 명시 묻기.

#### I3. orthogonal stage marker 미비 (C3)

**문제**: `mark_stage(rid, 'safety'/'meta', 'done')` → `ValueError: stage safety not in sequence`. progress.json `stages` 배열이 sequence-bound.

**증거** (transcript line 746-749):
```
File "/Users/yonghaekim/.claude/skills/assemble/server/progress.py", line 96, in mark_stage
ValueError: stage safety not in sequence
```

**영향**: guardian/keeper 산출물은 작성되지만 progress.json 추적 불가. dashboard / dogfood automation에서 누락.

**Spike XIV fix**: `server/progress.py`에 `mark_orthogonal_stage(rid, name, status)` API 추가. orthogonal_stages 별도 필드.

#### I4. SKILL.md doc drift (Stage 1)

**문제**: `bundled/idea-shaper/SKILL.md`에 명시된 `dispatch_prompt('bundled/idea-shaper/prompts/subagent/idea_shape_step1.md', run_id)` 시그니처가 실제 facade와 mismatch. 실제는 `dispatch_prompt('idea_shape_step1.md')` 1-arg basename.

**영향**: 메인이 코드 보고 보정. 빈손 사용자 perspective에서는 SKILL.md만 보고 그대로 따라하면 fail.

**Spike XIV fix**: 모든 ★ + 표준 번들 SKILL.md grep `dispatch_prompt(` → 시그니처 일치 검증 + 정정. (참고: Spike VII에서 RUN_DIR token 도입 시 시그니처 변경된 것이 SKILL.md doc에 반영 안 됨 추정)

### Minor / Cosmetic (V5)

#### M1. Bash guard hook recurring blockage (C4)

**문제**: 매 sub-agent 첫 write 시도가 V4 guard B-prime hook에 차단. magic marker `# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE` 학습 후 우회.

**우회**: sub-agent들이 1회 차단 후 우회 노하우 발견하면 진행. 시간 손실 ~10초/dispatch.

**Spike XIV fix (선택)**: hook 차단 메시지에 magic marker 위치 명시 추가. UX polish.

#### M2. 메뉴 옵션 6개 신규 사용자 과함 (Stage 1)

★ 1개 + ask/skip/manual/back/done = 6개. UX polish.

#### M3. design-pack과 plan-pack UI_GUIDE 중복 area

CLI 도구 컨텍스트라 design system 의미 약함. plan-pack UI_GUIDE.md와 중복. bundle scope 재검토 — V5.

---

## V4 paradigm 약속 vs 실제 동작 평가

| 약속 | 실제 |
|---|---|
| 자급자족 (10/10 라인업) | ✅ 모든 stage 작동, 산출물 정상 |
| ★ 등급 = 4~7 sub-agent dispatch pipeline | ❌ 시스템적 통합 1 dispatch (C2) |
| V4 #11 parallel dispatch | ❌ "시간 한계" 핑계로 우회 |
| V4 #9 orchestrator-only | ⚠️ 표면적 OK (sub-agent dispatch 사용), audit row 누락 |
| harness 4원칙 #1 (추측 금지, 사용자 질문 우선) | ⚠️ 단축 결정 시 사용자에게 묻지 않음 |
| iteration 3~7 round | ❌ default 추천이 "no — 종료" (I1) |
| 빈손 환경 격리 | ❌ ASSEMBLE_HOME env 전파 깨짐 (C1) |

**핵심 진단**: V4 paradigm은 *spec 문서 차원에서는* 일관되지만 *메인 Claude의 실제 운영 perspective*에서 작동하기 어렵다. 메인의 컨텍스트/시간 budget이 ★ paradigm 7회 dispatch + 4 iteration round를 감당하기 어려움.

선택지:
1. **paradigm 강화** — 단축 금지 강제 메커니즘 추가 (C1+C2 fix). 메인이 사용자 명시 동의 없이는 spec 우회 불가.
2. **paradigm retreat** — ★ 번들 spec 완화. "통합 1 dispatch도 OK" 명시. 사용자 약속 줄임.

(1) 권장. V4 약속을 지키려면 강제 메커니즘 필수. (2)는 V4 가치 자체 무력화.

---

## 형의 의도적 검증 전략 평가

> 모든 선택지를 의도적으로 1번 (default-recommended) 선택 — 어셈블의 default 정책 검증

**Gold standard dogfood 방법론**. 결과:

| 1번 default | 평가 |
|---|---|
| Stage 1 sequence 추천 (8 stages 전체) | ✅ 적절 |
| Stage 1 idea-shaper ★ | ✅ 적절 |
| Stage 2 plan-pack ★ | ✅ 적절 |
| ... (모든 stage 메뉴) | ✅ 적절 |
| iter0 → "yes" 진행 | ✅ 적절 (형 직관 정확) |
| iter1 → "no" default | ❌ **약속 위배** (I1) |

전체 default 정책 = 1개 결함. 형 직관이 정확히 그 1개를 잡았음.

---

## Spike XIV 입력

권장 scope:

**Phase A — C1 인프라 fix**:
- `server/harness.py::wrap_with_preamble`에 ASSEMBLE_HOME auto-prepend (호출 시점 env 캡쳐)
- `setup-spike-xiii-b19_setup.sh` 또는 후속 setup script에 `env -i` 격리 시도
- B-18 probe에 ASSEMBLE_HOME 전파 검증 AC 추가

**Phase B — C2/I2 paradigm 강화**:
- ★ 번들 SKILL.md head에 "단축 금지" 명시
- harness preamble v3에 4원칙 #1 wording 강화 ("모든 단축 결정 *전에* 사용자에게 AskUserQuestion으로 명시 묻기")
- Bash hook이 ★ stage에서 통합 dispatch 패턴 감지 → 사용자 confirmation 강제 (선택)

**Phase C — I1 plan-pack iter1 default fix**:
- `bundled/plan-pack/SKILL.md` Step 6 prompt 정정
- iter≤3 + (RESOLVED < 80% OR NEW > 0)이면 default = yes
- "dogfood 시간 한계" 사유 default 추천 문구 제거

**Phase D — I3 orthogonal stage API**:
- `server/progress.py` `mark_orthogonal_stage` API 추가
- progress.json schema 확장 (`orthogonal_stages` 필드)
- B-18 probe에 AC 추가

**Phase E — I4 SKILL.md doc drift**:
- 모든 번들 SKILL.md `dispatch_prompt(` 시그니처 검증 + 정정
- bidirectional integrity test에 시그니처 일치 검증 추가

**Phase F — B-20 재검증** (B-18 + B-19 재실행):
- C1 fix로 진짜 빈손 환경 dogfood 가능
- C2 fix로 메인이 spec 우회 불가
- 형이 1번 default 전략 재실행 → iter1에서 yes default 확인

**총 task**: 6 phases × 1-2 task = 6-12 atomic commits. 시간: ~4-6시간.

---

## V5 backlog (Spike XIV에 포함 X)

- M1/M2/M3 (cosmetic / UX polish)
- 이전 spike 누적 V5 (M-XII4 / F-XII1~5 / F4 perf / roles.json / etc.)
- bundle scope 재검토 (design-pack vs plan-pack UI_GUIDE 중복)
- ★ paradigm 부담 줄이기 (메인 컨텍스트 효율화)
- 외부 사용자 베타 (진짜 새 맥북)

---

## 산출물 inventory (검증 완료)

본 dogfood가 *실제로 작동하는 CLI 도구*를 만들어냈다는 점은 V4 paradigm의 부분적 성공:

```
ADR.md            11K
ANTI_PATTERNS.md  1.8K
ARCHITECTURE.md   3.7K
DEBUGGER_LOG.md   3.5K
DESIGN.md         1.2K
GUARDIAN.md       4.7K
IDEA.md           420B
IMPL_REPORT.md    3.2K
KEEPER_REPORT.md  7.1K
PRD.md            3.7K
REVIEW_REPORT.md  3.3K
SCOPE.md          921B
SHIPPER_LOG.md    2.1K
UI_GUIDE.md       8.4K
VERIFY_REPORT.md  1.8K
iteration_state.json  441B
md2txt.py         5.4K  (실행 가능, 31 tests pass, AC 3/3 PASS)
progress.json     2.0K
test_first.sh     473B
test_md2txt.py    5.5K
verify.sh         787B
```

총 21 files, 80KB+. md2txt.py는 빈손 환경에서 V4가 *실제로 만들어낸* 작동하는 도구.

---

## Source

- Transcript: `/tmp/spike-xiii-b19-transcript.txt` (RTF→TXT, 1286 lines, 141KB)
- Original RTF: `~/Library/Mobile Documents/com~apple~CloudDocs/assemble v4 dogfood.rtf`
- Captures (사본): `/Users/yonghaekim/spike-xiii-b19-captures.md` (14K)
- Spec: `docs/specs/2026-05-06-v4-spike-xiii-design.md` § B-19
- Plan: `docs/plans/2026-05-06-v4-spike-xiii.md` § Phase D
- B-18 자동 sanity probe: `tests/dogfood/spike_xiii_b18.py` (12/12 PASS)
- Parent: `project_assemble_v4_spec.md` (memory)
- Sibling: `project_assemble_v4_spike_xii.md` (memory)
