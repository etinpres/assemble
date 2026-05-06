# Spike XIV B-20b — Lived Dogfood 분석 + Verdict

**Date**: 2026-05-06
**Verdict**: **SHIP-WITH-MINOR-CARRYFORWARDS**
**Wall-time (lived)**: 41m 41s
**Run ID**: `20260506-151623-a69b`
**Transcript source**: iCloud `V4 dogfood-2.rtf` → `/tmp/spike-xiv-b20b-transcript.txt` (740 lines)

---

## TL;DR

본 dogfood 는 V4 paradigm hybrid (default=full + opt-in quick) 가 lived 환경에서
실제로 작동하는지 + Phase A~E fix 5 항목이 재발하지 않는지 검증. 결과:

- ✅ **paradigm enforcement 작동** — 3 ★ stage 모두 mode-gate AskUserQuestion 발사, quick/full 선택에 따라 dispatch 수 일관 (1 vs N)
- ✅ **5 fix 중 3 lived verified (C1, C2/I2, I4)** — 재발 0
- ⚠️ **2 fix lived uncovered (I1, I3)** — 시퀀스 축약 + quick mode 선택으로 lived 자극 미달, 단 자동 probe (B-20a) 에서 PASS
- ⚠️ **Critical re-occurrence: 0**
- ⚠️ **Important re-occurrence: 0**
- 5 minor carryforwards → V5 또는 Spike XV

V4 release gate (B-20a 18/18 PASS + B-20b SHIP-with-minor) 통과. T11 ship 진행 가능.

---

## Operational summary

### Setup

- 별도 Claude Code 세션, ASSEMBLE_HOME 빈손 tempdir (Spike XIII B-19 setup script 재사용)
- task: `Python CLI 도구 — 디렉토리 안 모든 .md 파일을 단일 PDF 로 묶는 스크립트` (T9 가이드 #1 추천)

### Sequence

| 단계 | 도구 | 모드 | dispatch 수 | 시간 |
|---|---|---|---|---|
| plan | ★ plan-pack | **quick** (의도 — R-F2) | 1 | 1m 24s |
| execute | ★ builder | **full** (의도 — R-F2) | 7 (steps 2~7 + Step 5 retry x2) | ~25m |
| verify | ★ verifier | **full** (추천) | 4 (extract/execute/classify/report) | ~2m |

총 3 stages (시퀀스 축약 — 메인이 task 단순도 보고 plan/execute/verify 만 추천 → 형 approve. V4 #1 8-stage 라인업 vs 사용자 명시 approve. 4원칙 #1 위반 X.)

### 산출물

- `~/my-folder/md2pdf/` — Python CLI 패키지 (collect/render/cli 모듈, pytest tests, README, pyproject.toml)
- run dir 산출물 (PRD.md / SCOPE.md / IMPL_REPORT.md / VERIFY_REPORT.md / parsed_scope.json + 4 verifier intermediates / dispatches.jsonl)
- 최종 AC: `python -m md2pdf tests/sample_docs -o /tmp/out.pdf && pdfinfo` → 2-page · 29KB PDF ✅

---

## Capture point 검증 (C20~C25)

| C# | 검증 대상 | 결과 | 근거 (transcript line) |
|---|---|---|---|
| C20 | ★ stage 진입 mode-gate 발사 | ✅ **PASS** | line 121 (plan-mode), line 219 (exec-mode), line 595 (verify-mode) — 3/3 |
| C21 | full mode → N-step pipeline 모두 실행 | ✅ **PASS** | execute: line 325/340/353/366/393/455/475/479 (7 dispatch). verify: line 659/665/681/687 (4 dispatch) |
| C22 | quick mode → 단일 dispatch + KEEPER_REPORT mode=quick | ✅ **PASS (단일 dispatch)** ⚠️ KEEPER_REPORT 미생성 (keeper stage 시퀀스 X) | line 167 — Agent(plan-pack quick mode dispatch). KEEPER_REPORT 는 keeper 번들 산출물이므로 시퀀스 축약으로 미생성 (no signal, not failure) |
| C23 | ASSEMBLE_HOME 자동 전파 | ✅ **PASS** | sub-agent dispatch 모두 정상 작동, 메인 수동 prepend 흔적 0 (transcript 전체 grep 통과) |
| C24 | plan-pack iter1 default = "yes" | ⚠️ **lived uncovered** | quick mode 라 plan-pack Step 6 iter 비활성. **자동 probe (B-20a AC15) 에서 § Recommendation policy + iter≤3 알고리즘 PASS** |
| C25 | orthogonal stage 마킹 | ⚠️ **lived uncovered** | 시퀀스 축약 (3 stages) — safety/meta 활성화 X. **자동 probe (B-20a AC16) 에서 mark_orthogonal_stage 직접 호출 PASS** |

---

## Phase A~E fix 5 항목 재발 검증

| Fix | 결과 | 근거 |
|---|---|---|
| **C1** ASSEMBLE_HOME 비전파 | ✅ **재발 X (lived)** | 별도 세션 진입 후 sub-agent dispatch 가 모두 home 경로 자동 사용. line 154 (run_dir creation), line 156 (run_dir ready) 모두 ASSEMBLE_HOME 기반 정상. 메인이 ASSEMBLE_HOME 명시 prepend 한 흔적 0 |
| **C2/I2** paradigm violation | ✅ **재발 X (lived)** | 3 ★ stage 진입 모두 mode-gate 발사 (line 121/219/595). quick 1 dispatch / full N dispatch 일관. 메인 자가 단축 결정 X. dispatches.jsonl audit row 모두 기록 |
| **I1** plan-pack iter1 default | ⚠️ **lived uncovered**, 자동 PASS | quick mode 선택으로 plan-pack iteration Step 6 자체를 거치지 않음 — 본 dogfood 가 fix 자체를 자극 못함. B-20a AC15 에서 § Recommendation policy + iter≤3 algorithm + forbidding wording 모두 PASS — fix 무결 |
| **I3** mark_orthogonal_stage | ⚠️ **lived uncovered**, 자동 PASS | 시퀀스가 plan/execute/verify 만 → safety (guardian) / meta (keeper) 미활성. lived 자극 0. B-20a AC16 에서 import + safety/meta 마킹 + auto-route 모두 PASS — fix 무결 |
| **I4** SKILL.md doc drift | ✅ **재발 X (lived)** | dispatch_prompt 호출 모두 정상 작동 — 메인 또는 sub-agent 가 stale 시그니처 시도한 흔적 0 |

**Critical re-occurrence: 0** | **Important re-occurrence: 0**

---

## V4 paradigm 검증 (Spike XIII NEEDS-FIX gap 재현)

| 약속 | 본 dogfood lived |
|---|---|
| ★ 등급 = 4-7 sub-agent dispatch | ✅ execute: 7 dispatch (full), verify: 4 dispatch (full). plan-pack: 1 dispatch (quick — 사용자 의도) |
| harness 4원칙 #1 (사용자 질문 우선) | ✅ mode-gate 3회 + verify-fail / weasy-fix / iter / next-task / already-done 추가 5회 — 메인 자가 결정 시도 시 차단 (Bash hook v3 작동) |
| iteration 3~7 round | (해당 없음 — quick mode 라 자극 X) |
| 빈손 환경 격리 | ✅ ASSEMBLE_HOME tempdir 격리 작동, host 오염 0 |
| 자급자족 (10/10 라인업) | ✅ ★ plan-pack / builder / verifier 3개 정상. 시퀀스 축약으로 나머지 7개 미사용 |

V4 약속 fundamental 한계 (Spike XIII 진단) **해소 확인**: 메인 컨텍스트 budget
한계로 paradigm 강제 작동 불가했던 문제가 mode-gate AskUserQuestion 으로 해결.

---

## 운영 incidents (verdict 무관, 기록용)

### Incident 1 — ESC 실수 (line 630-632)

verify 진입 시 형이 ESC 실수로 메인 차단. "잘못 눌렀어 계속 진행해" 로 즉시 복구.
paradigm 무관, 가벼운 운영 문제.

### Incident 2 — Bash GUARD hook 차단 (line 618-630)

verify 진입 시 메인이 `python3 -c "from server import parse_scope_md, write_run_artifact"` 호출 → V4 GUARD hook (Spike I+ Item B-prime) 가 plan-pack artifact 직접 write 차단. 메인이 즉시 sub-agent 로 우회 (line 638 — Agent(Generate parsed_scope.json)).

**paradigm enforcement 작동의 추가 신호** ✅ — 메인이 무거운 작업을 직접 시도해도 hook layer 가 잡아내고 sub-agent dispatch 로 강제 라우팅.

### Incident 3 — WeasyPrint native deps (line 370-459)

builder Step 5 verify 첫 실패 (`python` 명령어 부재 + venv 권한) → venv fix retry → 두 번째 실패 (WeasyPrint native libs 부재) → AskUserQuestion 으로 brew install 결정 → 세 번째 실패 (DYLD path) → DYLD env fix retry → PASS.

retry 흐름 모두 AskUserQuestion 으로 사용자 결정 위임. 4원칙 #1 모범 사례.
운영 이슈, fix 무관.

---

## Carryforwards (V5 또는 Spike XV)

### CF1 — Lived dogfood coverage gap (medium)

본 dogfood 가 시퀀스 축약 (3 stages) + plan-pack quick mode 선택으로 plan-pack
iteration (I1) + orthogonal stage 마킹 (I3) lived 자극 X. 자동 probe 에서 PASS
이지만 lived 환경 신호 0.

권장: V5 외부 베타 시 *시퀀스 8 stages 풀번들 + full mode 만 운영* 시나리오로 별도 dogfood 1회 추가.

### CF2 — 시퀀스 추천 알고리즘 검토 (low)

메인이 task "Python CLI" 단순도 보고 3 stages 만 추천 (line 47-58). V4 #1
라인업 8 sequence 정신과 *부분 충돌*. 사용자 명시 approve 였으니 4원칙 #1 위반 X
(R-B1 Spike XIV 거부 옵션 1 정신과 일관).

권장: 시퀀스 추천 default 알고리즘이 *task 복잡도 추정* 을 어떻게 하는지 명시
필요. 현재 메인 휴리스틱 + 사용자 approve 패턴은 작동 — 단, 메인 자의적 단축
가능성 있음.

### CF3 — T3 spec deviation 노출 X (very low)

T3 KEEPER_REPORT placeholder syntax deviation 은 본 dogfood 에서 keeper 번들
미사용으로 노출 X. V5 시 lived 검증 권장.

### CF4 — Builder Step 5 retry pattern 모범 사례 (positive — 기록용)

verify.sh 두 번 retry (venv → DYLD) 모두 AskUserQuestion 으로 사용자 결정 위임.
4원칙 #1 모범 사례. ★ paradigm 의 운영 강점 신호.

### CF5 — pyproject.toml 의 [project.optional-dependencies] dev 추가 권장 (very low, off-spec)

산출물 (md2pdf) 자체의 사소한 마무리 — pytest 가 venv 에 설치 안 됨. assemble
spec 무관, 형이 직접 정리 가능.

---

## V4 출시 게이트 판정

| 조건 | 결과 |
|---|---|
| B-20a 자동 sanity probe 18/18 PASS | ✅ T8 commit `d543502` |
| B-20b lived dogfood verdict ∈ {SHIP-READY, SHIP-WITH-MINOR-CARRYFORWARDS} | ✅ 본 verdict |
| 본 spike fix 5 항목 (C1, C2/I2, I1, I3, I4) 재발 0 | ✅ 모두 재발 0 (3 lived + 2 auto) |
| V4 정체성 invariants 모두 보존 | ✅ canonical preamble v3 sha 8d22a29c…089a9, ALLOW_LIST {v1,v2,v3} unchanged |

**판정**: **SHIP-WITH-MINOR-CARRYFORWARDS** — V4 release gate 통과. T11 ship 진행
가능. carryforward 5건 모두 V5 또는 Spike XV 후보, 본 spike scope 외.

---

## V5 backlog 추가 (본 spike 발생)

- CF1: 시퀀스 8 stages 풀번들 + full mode 시나리오 lived dogfood (Spike XIV 누락 coverage)
- CF2: 시퀀스 추천 default 알고리즘 *task 복잡도 추정* 명시
- CF3: T3 KEEPER_REPORT placeholder syntax lived 검증

기존 누적 V5 (Spike XIII M1/M2/M3 + Spike XII M-XII4/F-XII1~5 + F4 perf + roles.json + multi-language version bumping + multi-run concurrency + PII redaction + build sandboxing + Codex CLI / Gemini CLI 호환) 그대로 유지.

---

## Source

- Transcript: iCloud `V4 dogfood-2.rtf` (103KB, 1286+ lines RTF)
- Transcript 변환: `/tmp/spike-xiv-b20b-transcript.txt` (740 lines plain text)
- B-20a (자동) 결과: `docs/dogfood/spike-xiv-b20a.md` — 18/18 PASS
- 가이드: `docs/dogfood/spike-xiv-b20b-capture-guide.md` (T9)
- Run dir (별도 세션 host pollution X — tempdir 격리): `~/.claude/channels/assemble/runs/20260506-151623-a69b/` (별도 세션의 ASSEMBLE_HOME 안)
- Spec: `docs/specs/2026-05-06-v4-spike-xiv-design.md`
- Plan: `docs/plans/2026-05-06-v4-spike-xiv.md`
- Parent: `project_assemble_v4_spec.md`
- Sibling: `project_assemble_v4_spike_xiii.md`
