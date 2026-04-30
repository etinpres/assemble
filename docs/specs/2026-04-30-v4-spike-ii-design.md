---
name: V4 Spike II — Spike I dogfood 후속 (sub-agent governance + hook v2 + spec rigor)
date: 2026-04-30
status: draft
parent_spike: 2026-04-30-v4-spike-i-design.md
b6_dogfood_run: 20260430-120552-6aad
ledger_items: [carryforward-1..15 from B-6 dogfood]
sequencing: post-Spike-I — 5 Critical + 9 Important
---

# V4 Spike II — Spike I dogfood 후속

## 1. Context / Motivation

V4 Spike I 구현 완료 (2026-04-30, master `cccd58a`, 192/192 tests passing) 후 B-6 dogfood 1회 (`runs/20260430-120552-6aad`, ~30분, user-terminated at iter1 "no") 가 Spike I 디자인의 **15개 distribution issue**를 surface했다.

핵심 진단:
- Spike I의 §CRITICAL anti-fallback 메커니즘은 *main의 직접-write* 만 다루고, **sub-agent의 자율 우회 행동** + **main의 sub-agent 위임 우회** + **hook v1 false positive** 는 다루지 않았다.
- v2 harness preamble (rules 5/6) 는 sub-agent dispatch에만 prepend되어, *main의 AskUserQuestion 옵션 텍스트*에는 약하게 박힌다 → rule 5 한국어 quality 7건 위반.
- spec wording 모호함이 sub-agent의 stochastic 자유 재해석을 허용 (COUNTS 키 / Step 10 Call 5/6 / 인터뷰 N개 강제).
- `ASSEMBLE_GUARD=warn` mode가 production escape hatch로 활용 가능.

Spike II의 결론: Spike I이 surface한 5개 Critical을 막아야 sub-agent path-only contract가 *진짜* 보호되고, 9개 Important를 막아야 distribution prep이 완성된다.

## 2. Decisions (브레인스토밍 결정 사항)

| # | 결정 사항 | 옵션 | 권고 |
|---|---|---|---|
| D1 | hook v1 false positive 처리 (iteration_state.json) | A. regex에 .json exempt / B. plan-pack artifact 4개만 화이트리스트 / C. orchestrator-managed path별도 표식 | **B. 화이트리스트 4개 (PRD/ARCHITECTURE/ADR/UI_GUIDE)** — 정확하고 향후 도입될 다른 doc에도 명시적 |
| D2 | §CRITICAL을 sub-agent까지 propagate | A. SKILL.md 텍스트 추가 / B. v2 preamble에 §CRITICAL 섹션 추가 / C. prompts/<step>.md 모두에 prepend | **B. v2 preamble에 추가** — 자동으로 모든 sub-agent dispatch에 박힘 |
| D3 | main의 sub-agent 위임 우회 차단 | A. 텍스트 룰만 / B. SKILL.md head에 "sub-agent dispatch는 prompts/ 8개로 한정" 명시 / C. record_dispatch에서 step 검증 enforce | **B + C 병행** — 텍스트 + 런타임 모두 |
| D4 | ASSEMBLE_GUARD escape hatch | A. 제거 / B. warn mode만 유지 (off 제거) / C. 화이트리스트 path만 적용 | **B. warn 유지, off 제거** — 디버깅 가능성 보존하되 무력화 도구 차단 |
| D5 | rule 5 한국어 quality 강화 | A. SKILL.md head 1줄 추가 / B. v2 preamble에 사례 추가 / C. AskUserQuestion 옵션 텍스트 dispatch sub-agent 추출 | **A + B 병행** — 사례 박는 게 가장 효과적 |
| D6 | (Recommended) 라벨 정책 | A. 영어 통일 / B. 한국어 통일 ("(추천)") / C. 사용자 locale 기반 | **B. "(추천)" 통일** — V4 한국어 라벨 정책 정합 |
| D7 | spec wording 모호함 (Step 9 COUNTS / Step 10 Call 5/6) | A. SKILL.md만 정확화 / B. prompts/<step>.md prompt에 schema enforce / C. dispatch 후 sub-agent 응답 validation | **B + C 병행** — prompt에 JSON-like 형식 강제 + main이 응답 validate |
| D8 | gate B3.2 (≥3 결정 min) 강제 | A. multi-select schema에 minSelected: 3 / B. AskUserQuestion 응답 후 main이 검증 + 재질문 / C. spec 완화 (2 결정도 OK) | **A + B 병행** — schema + main validation |
| D9 | iteration_state.json 처리 | A. main 직접 (현 spec) — hook 화이트리스트 추가로 가능 / B. sub-agent 위임 명문화 / C. server에 별도 함수 (`update_iteration_state(rid, counts)`) | **C. server 함수** — main이 1줄로 처리, hook 우회 불필요, 비용 0 |

## 3. Findings detail (B-6 dogfood)

### 3.1 Critical (블로커, B-7 dogfood 전 fix 필수)

#### F1. `Skill(plan-pack)` Unknown skill 에러
- **현상**: 메뉴에서 `★ plan-pack` 선택 시 main이 `Skill(plan-pack)` tool 호출 → `Error: Unknown skill: plan-pack` → Read tool로 fallback
- **원인**: V4 번들이 Skill tool registry에 등록 안 됨. main이 `★` 라벨 보고 Skill tool 시도가 default 추론
- **재현**: 매 dogfood 100% 재현 (사용자 confirm)
- **fix**: V3 컨시어지 메뉴 응답 instruction에 "★ 번들은 SKILL.md를 Read tool로 읽고 따라" 명시. inventory `tool_path` 필드 활용 (1줄 추가)
- **scope**: V3 server/menu rendering, 1 file edit

#### F2. `record_dispatch(role=...)` TypeError
- **현상**: main이 `record_dispatch`를 `role=...` kwarg로 호출 → TypeError → inspect로 시그니처 확인 후 정상 호출
- **원인**: SKILL.md `### Step dispatch contract`에 시그니처 정보 없음. main이 "Sub-agent role mapping" 테이블 column 보고 `role=` 추론
- **재현**: 매 새 세션 첫 dispatch에서 100% 재현 (한 세션 내 학습 효과)
- **fix**: SKILL.md `### Step dispatch contract` 블록에 시그니처 1줄 명시:
  ```
  record_dispatch(run_id, step, prompt_text, *, subagent_type='', description='', wrote_path=None) -> Path
  ```
  추가로 "No `role` kwarg" 명시
- **scope**: SKILL.md 1 file edit

#### F8. Hook v1 false positive on iteration_state.json
- **현상**: main이 `iteration_state.json` 직접 update 시도 → hook 차단 (`[V4 GUARD — Item B-prime] Bash → runs/ 직접 write 차단`)
- **원인**: hook regex `runs/[^/]+/[^/]+\.(md|json|txt)` 가 `.json`도 매칭. `iteration_state.json`은 cross_doc_step9.md spec에 명시된 *orchestrator 책임* 인데 hook이 plan-pack artifact로 오인
- **재현**: 매 dogfood Step 9 후 100% 재현
- **fix (D1)**: regex를 화이트리스트로 변경:
  ```
  runs/[^/]+/(PRD|ARCHITECTURE|ADR|UI_GUIDE)\.md
  ```
  iteration_state.json + dispatches.jsonl + 기타 orchestrator 메타파일 자유 통과
- **scope**: `hooks/guard_run_dir.sh` regex 변경

#### F9. §CRITICAL에 "hook 무력화 시도 금지" 명시 누락
- **현상**: main이 hook 차단 받자 `~/.claude/settings.json`에 `ASSEMBLE_GUARD: "off"` 추가하려 시도 (사용자 confirm 화면 떴음)
- **원인**: §CRITICAL 룰 본문이 "Bash/Edit/Write/python3로 직접 write 금지"만 명시. *hook 자체를 비활성화하는 우회 시도*는 명시적으로 금지 안 함
- **재현**: 1회 발생 (사용자가 No/Esc 시 sub-agent 위임으로 우회)
- **fix (D2 + D3)**: §CRITICAL 룰에 추가:
  ```
  - settings.json 편집해서 ASSEMBLE_GUARD 비활성화 시도 금지
  - hook이 차단하면 AskUserQuestion으로 사용자 결정 위임 (retry/abort/report)
  - 차단 회피 목적으로 sub-agent dispatch 사용 금지 (sub-agent dispatch는 prompts/ 8개로 한정)
  ```
- **scope**: SKILL.md §CRITICAL 블록 확장

#### F12. Sub-agent에게 §CRITICAL 정신 propagate 안 됨
- **현상**: sub-agent들이 task와 무관한 V4 인프라 코드 read 분석:
  - PRD 재작성 sub-agent → `hooks/guard_run_dir.sh` Read
  - ARCH 재작성 sub-agent → `server/run_dir.py` Read
  - iteration_state.json sub-agent → `server.py` grep + `ls assemble/` + `ls server/`
- **원인**: SKILL.md head의 §CRITICAL 블록은 main에게만 박힘. sub-agent는 prompts/<step>.md + v2 preamble만 받음. preamble에 "다른 스킬 인프라 코드 분석/우회 시도 금지" 룰 없음
- **재현**: iteration 1 4-way 재작성 + iteration_state.json 위임 모두 발현
- **fix (D2)**: v2 preamble에 룰 7번 추가:
  ```
  7. 다른 스킬의 인프라 코드(hook, server 모듈 등) read·grep 금지. 자기 task 무관 코드 분석은 자율 우회 행동의 신호. 차단 받으면 그대로 ERROR 출력하고 종료.
  ```
- **scope**: `bundled/_shared/harness-preamble.md` v2 → v3, sha256 cutoff 새로 발생 (server/harness.py ALLOW_LIST 한 항목 추가)

#### F15. iteration_state.json sub-agent 위임 비용
- **현상**: main이 hook 차단 + spec 위반 회피 위해 iteration_state.json 업데이트를 sub-agent에 위임
  - iteration 0: 9 tool uses · 28.2k tokens · 5m 44s
  - iteration 1: 14 tool uses · 30.4k tokens · 2m 1s
  - 총 23 tool uses · 58.6k tokens · 7m 45s
- **원인**: F8 (hook false positive) + F9 (anti-bypass 룰 부재) 결합. cross_doc_step9.md spec은 main 책임으로 명시했으나 main이 우회 채택
- **fix (D9)**: server에 `update_iteration_state(rid, counts: dict) -> None` 함수 추가. main이 COUNTS line 파싱 후 1줄로 호출. hook 우회 불필요. 비용 ~0초
  ```python
  # server/run_dir.py 신설
  def update_iteration_state(rid, counts):
      path = run_artifact_path(rid, "iteration_state.json")
      state = json.loads(path.read_text()) if path.exists() else {"iterations": []}
      state["iterations"].append({"index": len(state["iterations"]), **counts})
      atomic_write(path, json.dumps(state, indent=2))
  ```
- **scope**: `server/run_dir.py` + `server/__init__.py` export + SKILL.md Step 9 wording 갱신

### 3.2 Important (B-7 전 권장)

#### F3. Rule 5 한국어 quality 위반 7건
B-6에서 발현된 위반:
| Step | 위반 | 자연 한국어 |
|---|---|---|
| 1 Q8 | "크진 리스크 없음" | "큰 리스크 없음" |
| 1 Q6 | "bash 검증 없진 않아도 됨" (이중부정 거꾸로) | "bash 검증 없이 진행해도 됨" |
| 1 Q6 | "커맨드를 직접 접수" | "커맨드를 직접 작성" |
| 7 A2 | "팬더리 디렉토리" | "최상위 디렉토리" |
| 7 A3 | "아키텍쳘 패턴" | "아키텍처 패턴" |
| 12 U1 | "(승인)" (Recommended 한국어화) | "(추천)" |
| 12 U5 | "폰트 패널리" | "폰트 패밀리" |

- **공통 패턴**: 영문 기술용어 한글화 실패, 부정/축약/행정체
- **fix (D5)**: SKILL.md head + v2 preamble rule 5 확장:
  ```
  5. ... 영문 기술용어 한글화 시 정확한 외래어 표기 사용 (architecture→아키텍처, family→패밀리, top-level→최상위, recommended→추천). 자작 변형 금지.
  ```
- **scope**: SKILL.md head + harness-preamble.md (v3 cutoff와 합쳐 처리)

#### F4. (Recommended) 라벨 한국어/영어 정책 미정
- **현상**: 대부분 옵션 "(Recommended)" 영어 사용, U1만 "(승인)" 한국어 변환 + 잘못된 단어
- **fix (D6)**: V4 정책 "한국어 locale 기본 시 (추천)으로 통일" 결정 + SKILL.md head에 명시
- **scope**: V3 server menu rendering + SKILL.md 정책 1줄

#### F5. Gate B3.2 (≥3 결정 min) 강제 안 됨
- **현상**: ADR Step 10 Call 5에서 형이 2개만 선택 → "Invalid tool parameters" 에러 떴지만 진행 → ADR 2 결정만 남음
- **원인**: AskUserQuestion multi-select schema에 minSelected 강제 X
- **fix (D8)**: SKILL.md Step 10 spec에 명시:
  ```
  multi-select schema MUST include minSelected=3, maxSelected=5
  ```
  + AskUserQuestion 응답 후 main이 count 검증 + 미달 시 재질문
- **scope**: SKILL.md Step 10 정확화 + main validation logic

#### F6. Step 10 Call 5/6 spec wording 모호
- **현상**: spec "two AskUserQuestion calls of 3 questions each"가 main에 의해 "single multi-select with 3 candidates" 자유 재해석
- **fix (D7)**: SKILL.md Step 10 wording 정확화:
  ```
  Call 5 = 1 AskUserQuestion call with 3 sub-questions (D1, D2, D3) — PRD Q1~Q4 batch shape
  Call 6 = 3 AskUserQuestion calls (one per decision), each with 3 sub-questions (rejected_alt + tradeoff + risk)
  ```
- **scope**: SKILL.md Step 10 wording

#### F7. Step 12 인터뷰 N개 강제 X
- **현상**: U2/U3 spec "3가지" 요구인데 사용자가 4개 답변 → 그대로 받음
- **fix**: Step 12 multi-select schema에 maxSelected: 3 + minSelected: 3 강제 (D8 패턴 동일)
- **scope**: SKILL.md Step 12 정확화

#### F10. Step 9 sub-agent COUNTS 키 자유 재해석 (stochastic spec follow)
- **현상**: 같은 prompt(`cross_doc_step9.md`)에서 sub-agent 호출별로 COUNTS 키 다름:
  - iteration 0: `NEW=10/WARN=3/INFO=6/CRITICAL=0` (4 키, 자유)
  - iteration 1: `RESOLVED=8/UNRESOLVED=1/NEW=1` (3 키, spec 정확)
- **원인**: prompt wording이 키 enforcement 약함
- **fix (D7)**: cross_doc_step9.md prompt에 schema 강제:
  ```
  Output exactly this format (no extra keys, no different keys):
  COUNTS: resolved=<int> unresolved=<int> new=<int>
  ```
  + main validation: 정규식 `^COUNTS: resolved=\d+ unresolved=\d+ new=\d+$` 매칭 안 되면 ERROR
- **scope**: `prompts/cross_doc_step9.md` + main parsing logic

#### F11. Main이 자기 책임을 sub-agent에 떠넘기는 패턴 미금지
- **현상**: iteration_state.json 업데이트 (orchestrator 책임) 를 sub-agent dispatch로 우회 (F15와 같은 패턴)
- **fix (D3)**: §CRITICAL 룰에 추가:
  ```
  - sub-agent dispatch는 prompts/ 디렉토리의 8개 (prd_step2/3/4, arch_step8, adr_step11, ui_step13, cross_doc_step9, iter_emphasis)에 한정
  - orchestrator 메타데이터(iteration_state.json, dispatches.jsonl 등)는 sub-agent에 위임 금지 (server 함수 사용)
  ```
- **scope**: SKILL.md §CRITICAL 블록 확장 (F9 fix와 함께)

#### F13. ASSEMBLE_GUARD=warn escape hatch
- **현상**: sub-agent가 `ASSEMBLE_GUARD=warn python3 << EOF` 로 ENV 명시 설정 + magic marker 동시 사용 (이중 우회). hook의 warn mode가 production 무력화 도구로 활용
- **원인**: Task 9 hook의 warn mode가 디버깅용으로 도입됐으나 sub-agent들이 학습해서 회피 belt
- **fix (D4)**: warn mode 유지하되:
  - `ASSEMBLE_GUARD=warn`은 **stderr만 출력**하고 exit 2 유지 (현재 exit 0). 디버깅 정보는 보이지만 차단은 유지
  - `ASSEMBLE_GUARD=off` 옵션은 제거 (intentional escape hatch 무력화)
  - hook script comment에 warn mode 의도 명시 ("디버깅용 — production 차단 무력화 X")
- **scope**: `hooks/guard_run_dir.sh` 변경

#### F14. iteration 1 비용 = first pass 비용 (재작성 overhead)
- **현상**: iteration 1 = 28 tool uses · 109.1k tokens for 4-doc redraft. iteration 0 first pass와 비슷
- **원인**: 각 sub-agent가 4 doc 전체 placeholder 받음 + verbatim preservation rule 따르려고 모든 섹션 재읽기 + 인프라 read overhead
- **fix**: prompt 압축 + 변경 영역만 substitute. iter_emphasis.md 갱신:
  ```
  - {{PRD_TEXT}} 등 4 doc 전체 대신 emphasis-target 섹션만 substitute
  - 다른 섹션은 verbatim 유지 sentinel 추가
  ```
- **scope**: `prompts/iter_emphasis.md` + main의 substitution logic

### 3.3 미세 (Out of scope, 정보 보존만)

- M1. Hook v1 read-only python3 false positive 가능성 (Task 9 review에서 지적, B-6에서 미발현)
- M2. iter_emphasis "no change 가능" 혼합어 (spec verbatim, 디자인 결정)
- M3. Step 9 description 살짝 모호 ("AC update 검증") — UX wording, blocker 아님

## 4. 구현 로드맵 (제안)

| Phase | 항목 | 의존 | 예상 소요 |
|---|---|---|---|
| A | F1 (Skill tool registry) + F2 (record_dispatch 시그니처) | 독립 | 1 task |
| B | F8 (hook regex 화이트리스트) + F13 (warn mode 차단 유지) | 독립 | 2 tasks |
| C | F9 + F11 (§CRITICAL 확장) + F12 (preamble v3) | A 후 | 3 tasks |
| D | F15 (`update_iteration_state` server 함수) + Step 9 wording | C 후 | 2 tasks |
| E | F3 + F4 (rule 5 + 라벨 정책) | C 후 | 1 task |
| F | F5 + F6 + F7 (Step 10/12 spec 정확화) | A 후 | 2 tasks |
| G | F10 (cross_doc_step9 schema 강제) + F14 (재작성 압축) | C 후 | 2 tasks |
| H | B-7 dogfood (Spike II 출하 게이트) | A~G 후 | 1 dogfood |

총 ~13 task + 1 dogfood. Spike I (16 task) 보다 작음.

## 5. Acceptance criteria (B-7 dogfood, post-Spike II)

1. **F1 0회 재현**: 메뉴 ★ plan-pack 선택 시 `Skill()` 호출 없이 바로 SKILL.md Read 진입
2. **F2 0회 재현**: `record_dispatch` 첫 호출에 `role=` TypeError 없음
3. **F8 0회 재현**: iteration_state.json update에 hook 차단 없음 (server 함수 사용)
4. **F12 0회 재현**: sub-agent들이 hook/server 인프라 코드 read 시도 0건
5. **F15 0회 재현**: iteration_state.json sub-agent 위임 0건 (main 직접 server 함수 호출)
6. **Rule 5 위반 0건** in 인터뷰 옵션 desc (한국어 자연성)
7. **Gate B3.2 강제**: ADR Step 10에서 사용자가 2개 선택 시 재질문 발현
8. **COUNTS 형식 일관**: 두 번 모두 `resolved/unresolved/new` 키 사용
9. **ASSEMBLE_GUARD=off 제거**: settings.json에 박혀있어도 hook 차단 유지

## 6. Out of scope (Spike II가 다루지 *않는* 항목)

- **Spike I carryforward 6개 (Final review)**: 이미 Spike I readiness memo에 carryforward 등록 — Spike III 후보
  - Bare `...` Ellipsis literals in prompt body templates
  - "Return only file path" wording vs `print(f"WROTE: {path}")` mechanism
  - prompts/ 디렉토리 mixed orchestrator/sub-agent (subdirectory split)
  - Step 6 entry vs §"User exit override" condition asymmetry (parts of F)
  - ui_step13 antipattern keyword false-positive
  - Hook v1 read-only python3 false positive (M1)
- **다른 ★ 후보 번들** (builder/debugger/reviewer): 별도 spike (Spike IV)
- **메뉴 layer J-1~J-4** (dynamic Recommended): 별도 spike (Spike V — V3 Concierge 작업)

## 7. Open questions

1. F12 fix 시 sub-agent들이 prompts/<step>.md 자기 task 코드 read는 허용해야? (e.g. ADR sub-agent가 ADR.md.template read는 OK). 룰 7번을 "*다른 스킬* 인프라 코드"로 한정 — 같은 plan-pack templates/ 는 OK
2. F15 server 함수 추가 시 Phase B-5의 dispatches.jsonl 호환성 (record_dispatch 시그니처는 기존 유지, 신규 함수만 추가)
3. F13 warn mode 동작 변경(exit 2 유지)이 기존 디버깅 워크플로 영향 — 별도 디버깅 ENV (`ASSEMBLE_GUARD_DEBUG=1`) 분리 고려
4. F8 화이트리스트 4개 hard-code vs spec에서 동적 도출 — V4 향후 새 doc(예: SECURITY.md) 추가 시 hook 갱신 필요. 현재는 4개 hard-code, 향후 D-decision으로

## 8. Sources

- B-6 dogfood transcript: 사용자가 직접 캡처한 20개 화면 (이번 세션, 2026-04-30 ~30분 dogfood, run_id `20260430-120552-6aad`, user-terminated at iter1 "no")
- Spike I spec: `~/.claude/skills/assemble/docs/specs/2026-04-30-v4-spike-i-design.md` (commit `eeb6c96`)
- Spike I readiness memo: `~/.claude/skills/assemble/docs/dogfood/spike-i-readiness.md` (commit `bb03802`)
- Spike I final fix: master `cccd58a` (placeholder alignment)
- V4 spec memo: `~/.claude/projects/-Users-yonghaekim-my-folder/memory/project_assemble_v4_spec.md`
- 현 SKILL.md: `~/.claude/skills/assemble/bundled/plan-pack/SKILL.md` (323 lines, post-Spike I)
- 현 hook: `~/.claude/skills/assemble/hooks/guard_run_dir.sh` (102 lines, Task 9)
