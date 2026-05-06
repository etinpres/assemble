# V4 Spike XIII Plan — Phase G blank-Mac dogfood (V4 release gate)

> **For agentic workers:** Spike XIII는 *검증* spike. Phase A/B는 자동 (이 세션).
> Phase C는 사용자가 별도 세션에서 운전 (비동기). Phase D/E는 캡쳐 분석 후 verdict.
> 일반적인 subagent-driven-development 패턴과 다름 — 사용자 운전이 핵심.

**Date**: 2026-05-06
**Spec**: `docs/specs/2026-05-06-v4-spike-xiii-design.md`
**Pattern**: Hybrid — automated B-18 probe (이 세션) + user-driven B-19 lived dogfood (별도 세션)
**Baseline**: master `ea15ea1`, pytest **813 passed** (Spike XII cleanup 후 안정 상태)

**Goal**: V4 결정 #6 release gate 통과 — 빈손 환경 + 사용자 perspective에서 V4
paradigm이 약속대로 작동하는지 검증. PASS 시 V4 ship.

**Architecture**: 검증 spike. 코드 변경 거의 없음. B-18 probe + setup script +
캡쳐 가이드 + 결과 리포트들 = 9 NEW files + 1 CHANGELOG edit. V4 정체성 invariant
모두 변경 X (변경 발견 = 결함, fix 필요).

**Tech Stack**: Python 3.10+ (B-18 probe), Bash (B-19 setup script), Markdown (가이드/리포트).

---

## Overview

6 phases. 운영 방식이 phase별로 다름.

| Phase | Scope | 운영 | 시간 |
|---|---|---|---|
| A | B-18 자동 sanity probe (`tests/dogfood/spike_xiii_b18.py`) | 이 세션, 자동 | ~30분 |
| B | B-19 setup 스크립트 + 캡쳐 가이드 doc | 이 세션, doc/script | ~30분 |
| C | B-19 lived dogfood 실행 (사용자 운전) | **별도 세션, 비동기** | ~50분 사용자 |
| D | 캡쳐 분석 + 결함 분류 | 이 세션, 형이 캡쳐 가져온 후 | ~30분 |
| E | overall review + ship verdict | 이 세션 | ~20분 |
| F | (조건부) CHANGELOG flip + ship commit | verdict가 SHIP이면 | ~10분 |

총 task 수: 7 (A1, B1, C1, D1, E1, F1 + 조건부 fix)

---

## Pre-scan checkpoint (sanity confirmed)

| # | 항목 | 결과 |
|---|---|---|
| 1 | pytest baseline | **813 passed** |
| 2 | frontmatter convention | enforced |
| 3 | bidirectional integrity | green |
| 4 | _PROMPT_TO_STAGE values ⊆ STAGE_CATEGORY_PRIORITY keys | 10 |
| 5 | STAGE_CATEGORY_PRIORITY count | 10 stages |
| 6 | WROTE: contract | line 1 |
| 7 | ALLOWED_PROMPT_FILES count | 42 BASENAMES |

V4 invariants:
- canonical preamble v3 sha = `8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9`
- ALLOW_LIST = {v1, v2, v3}
- _BUNDLES = 10, _BUNDLED_DIR_TO_STAGE = 10

Spike XIII는 검증 spike — 위 invariants 모두 변경 X. 변경 발견 시 결함, Spike XIV로.

---

## Phase A — B-18 자동 sanity probe (1 task)

**Task A1**: `tests/dogfood/spike_xiii_b18.py` 작성 + 실행 + 12 AC PASS 확인.

### 운영 방식

이 세션, 자동 실행. Spike XII B-17 패턴 따라.

### Acceptance

- 파일 `tests/dogfood/spike_xiii_b18.py` 존재, runnable as `python3 -m tests.dogfood.spike_xiii_b18`
- 12 AC 모두 PASS (spec § B-18 § 12 acceptance criteria 참조)
- Wall-time ≤ 30s
- `docs/dogfood/spike-xiii-b18.md` 생성 (verdict 리포트)

### B-18 12 AC (verbatim from spec)

| # | Check | PASS condition |
|---|---|---|
| AC1 | tempdir setup successful | assemble dir copied with all 10 bundles + _shared |
| AC2 | inventory.scan() returns ≥10 skills | bundled 번들 모두 인식 |
| AC3 | 모든 번들 entry has `bundled=True` | inventory `_is_bundled` 정상 |
| AC4 | 사용자 스킬 0개 | bundled-only 환경 검증 |
| AC5 | menu shows ★ prefix on bundled bundles | i18n keys 정상 |
| AC6 | menu fallback hint shown | `notices.bundled_only_hint` 정상 |
| AC7 | 모든 번들 SKILL.md frontmatter parses | yaml 무결성 |
| AC8 | 모든 dispatchable prompt 등재 in ALLOWED_PROMPT_FILES | bidirectional |
| AC9 | 모든 contract entries (contracts.json) loadable | 무결성 |
| AC10 | canonical preamble v3 sha = `8d22a29c97...089a9` | invariant |
| AC11 | /assemble eject sub-command resolves (text scan) | router 작동 |
| AC12 | dogfood doc generated | `docs/dogfood/spike-xiii-b18.md` |

### 구현 가이드

- Spike XII B-17 (`tests/dogfood/spike_xii_b17.py`) 패턴 그대로 재사용
- ASSEMBLE_HOME tempdir 격리, finally cleanup
- B-18은 inventory + frontmatter + contracts 무결성 위주 (B-17보다 가벼움 — eject 호출 없음)
- 결함 발견 시 즉시 abort + 결함 명시

### Commit

```
test(v4-spike-xiii-A): B-18 자동 sanity probe — blank ASSEMBLE_HOME 12/12 AC PASS

- tempdir-rooted ASSEMBLE_HOME, assemble만 복사 (빈손 환경 강제)
- inventory.scan() 폴백 / bundled-only menu hint 검증
- 모든 번들 frontmatter / contracts / prompt 무결성
- canonical preamble v3 sha invariant
- docs/dogfood/spike-xiii-b18.md 생성

Wall-time: <Xs>. pytest 813 passed (probe standalone, count 변경 X).

Refs: docs/specs/2026-05-06-v4-spike-xiii-design.md § B-18
```

---

## Phase B — B-19 setup 스크립트 + 캡쳐 가이드 (1 task)

**Task B1**: `scripts/spike_xiii_b19_setup.sh` + `docs/dogfood/spike-xiii-b19-capture-guide.md` 작성.

### 운영 방식

이 세션. doc/script 작성만. 코드 변경 X.

### Acceptance

- `scripts/spike_xiii_b19_setup.sh` 존재, executable
- `docs/dogfood/spike-xiii-b19-capture-guide.md` 존재
- 가이드에 40 캡쳐 항목 표준화 (10 stages × 4 항목)
- Project 선택 옵션 3개 명시 (CLI 도구 권장 / 가상 PRD / recursive)
- Stage 진행 게이트 10개 명확 (각 번들의 핵심 검증 포인트)

### Setup script 요건

```bash
#!/usr/bin/env bash
set -euo pipefail
TEMP_HOME=$(mktemp -d -t spike-xiii-b19-XXXXXX)
mkdir -p "$TEMP_HOME/.claude/skills"
cp -R "$HOME/.claude/skills/assemble" "$TEMP_HOME/.claude/skills/assemble"
# Verify 빈손 (only assemble)
SKILL_COUNT=$(ls -1 "$TEMP_HOME/.claude/skills/" | wc -l | tr -d ' ')
if [ "$SKILL_COUNT" != "1" ]; then
    echo "ERROR: 빈손 환경 검증 실패"; exit 1
fi
echo "ASSEMBLE_HOME=$TEMP_HOME"
echo "다음 명령으로 별도 세션 진입:"
echo "    ASSEMBLE_HOME=$TEMP_HOME claude"
```

### 캡쳐 가이드 요건

Markdown 문서, ~150줄. 구성:

1. **Setup 명령** — `scripts/spike_xiii_b19_setup.sh` 실행 후 별도 세션 진입
2. **Project 선택** — 3 옵션 (CLI 도구 / 가상 PRD / recursive). 권장 = CLI.
3. **시작 명령** — `/assemble <task>` 입력 예시
4. **10 Stage 게이트** — 각 stage 별 검증 포인트 (1줄~3줄)
5. **각 stage 캡쳐 4항목**:
   - 명령 입력 + 응답 헤더 (~5줄)
   - 산출물 파일 경로 + 크기
   - 막힘 / 어색함 노트
   - 4원칙 위반 의심 (있으면)
6. **종료 후 정리** — `rm -rf $ASSEMBLE_HOME`
7. **캡쳐 가져오기** — 형이 이 세션으로 돌아와서 캡쳐 보여주는 방법 (paste / file)

### Commit

```
docs(v4-spike-xiii-B): B-19 lived dogfood — setup 스크립트 + 40 캡쳐 가이드

- scripts/spike_xiii_b19_setup.sh: fresh ASSEMBLE_HOME tempdir + assemble만 복사
- docs/dogfood/spike-xiii-b19-capture-guide.md: 10 stages × 4 항목 = 40 캡쳐 표준
- Project 선택 3 옵션 (CLI 도구 권장)
- Stage 진행 게이트 + 캡쳐 항목 명확

별도 세션에서 사용자 운전 가능. 비동기 진행.

Refs: docs/specs/2026-05-06-v4-spike-xiii-design.md § B-19
```

---

## Phase C — B-19 lived dogfood 실행 (별도 세션)

**Task C1**: 사용자가 별도 세션에서 lived dogfood 실행. 비동기.

### 운영 방식

**별도 세션. 형이 운전. 이 세션은 대기.**

이 spike의 결정적 차이 — 이전 모든 spike의 dogfood (B-1~B-18)는 자동 self-execute
였으나 B-19는 사용자가 직접 진행해야 함. UX/판단/4원칙은 인간 시야 필요.

### 사용자 진행 흐름

1. 이 세션에서 "B-19 시작 준비됐다" 알림
2. **별도 터미널 / Claude Code 세션** 열기
3. `bash ~/.claude/skills/assemble/scripts/spike_xiii_b19_setup.sh` 실행
4. 출력된 `ASSEMBLE_HOME=...` 명령으로 별도 Claude Code 세션 진입
5. `cat ~/.claude/skills/assemble/docs/dogfood/spike-xiii-b19-capture-guide.md` 으로 가이드 확인
6. 가이드 따라 `/assemble <task>` 입력
7. 10 stages 진행하면서 4 항목씩 캡쳐 (총 40)
8. 종료 후 cleanup
9. 캡쳐 모음을 이 세션에 가져옴 (paste / file 첨부)

### Acceptance

- 한 프로젝트 완주 (10 stages 모두 통과 OR 일부 stage에서 막혔다는 캡쳐)
- 40 캡쳐 모음 (또는 막힌 시점까지 캡쳐 + 막힌 이유)
- 사용자 self-assessment (각 stage 어땠나 / 어색한 점 / 추천 점)

### 시간 예상

~50분 (5분 × 10 stages). 시간 부족하면 priority stage (plan ★ / debugger ★ /
reviewer ★ / verifier ★)만 먼저 진행 후 나머지 추후.

### B-19 산출물

이 phase 자체는 commit 없음 (사용자가 캡쳐 가져오는 시점에 Phase D 시작).

---

## Phase D — 캡쳐 분석 + 결함 분류 (1 task)

**Task D1**: 형이 캡쳐 가져온 후 분석 → 결함 Critical/Important/Minor 분류 →
`docs/dogfood/spike-xiii-b19.md` 작성.

### 운영 방식

이 세션, 형이 캡쳐 가져온 후. 자동 분석 + judgment.

### Acceptance

- `docs/dogfood/spike-xiii-b19.md` 생성
- 40 캡쳐 (또는 가져온 만큼) 모두 검토
- 발견 결함 분류 (Critical / Important / Minor / Cosmetic)
- 각 결함에 대한 fix 패치 또는 V5 deferral 판단
- preliminary verdict (SHIP / SHIP-WITH-MINOR / NEEDS-FIX / NEEDS-MAJOR-REWORK)

### 결함 분류 rubric

| 분류 | 정의 | 처리 |
|---|---|---|
| **Critical** | ship 차단 — V4 paradigm 약속 깨짐 (자급자족 못 함, 4원칙 시스템적 위반) | Spike XIV 즉시 fix |
| **Important** | 사용자가 stuck하거나 ship-blocking UX | fix or carryforward 판단 |
| **Minor** | nice-to-have, 우회 가능 | V5 deferral |
| **Cosmetic** | wording / glyph / 빈약한 메시지 | V5 deferral |

### Commit

```
docs(v4-spike-xiii-D): B-19 lived dogfood 캡쳐 분석 + 결함 분류

- 40 캡쳐 모두 검토 (또는 가져온 만큼)
- Critical N개 / Important N개 / Minor N개 / Cosmetic N개
- preliminary verdict: <verdict>
- docs/dogfood/spike-xiii-b19.md 작성

Refs: docs/specs/2026-05-06-v4-spike-xiii-design.md § B-19
```

---

## Phase E — Overall review + ship verdict (1 task)

**Task E1**: `superpowers:code-reviewer` 또는 직접 분석으로 종합 review →
`docs/dogfood/spike-xiii-overall-review.md` + final verdict.

### 운영 방식

이 세션. B-18 + B-19 종합.

### Acceptance

- `docs/dogfood/spike-xiii-overall-review.md` 생성
- B-18 + B-19 종합 결과 정리
- V4 정체성 invariant 최종 확인
- final verdict:
  - **SHIP-READY** — V4 출시 가능
  - **SHIP-WITH-CARRYFORWARDS** — V4 출시 + V5 backlog 명시
  - **NEEDS-FIX** — Spike XIV cleanup 후 재실행
  - **NEEDS-MAJOR-REWORK** — 결함 종류에 따라 추가 spike 다수

### Codex retro 결정

표준 skip. 단:
- Critical 결함 발견 시 → Codex retro로 root cause 검증
- 4원칙 시스템적 위반 발견 시 → Codex retro로 patch 적정성 검증

### Commit

```
docs(v4-spike-xiii-E): overall review + ship verdict — <verdict>

B-18 + B-19 종합:
- B-18 자동 sanity probe: 12/12 AC PASS (or fail)
- B-19 lived dogfood: <count> 캡쳐, Critical N / Important N / Minor N / Cosmetic N

Final verdict: <verdict>

V4 정체성 invariant 최종 확인:
- canonical preamble v3 sha unchanged
- ALLOWED_PROMPT_FILES = 42, _BUNDLES = 10, STAGE_CATEGORY_PRIORITY = 10

Refs: docs/dogfood/spike-xiii-b18.md, docs/dogfood/spike-xiii-b19.md
```

---

## Phase F — (조건부) CHANGELOG flip + ship commit (1 task)

**Task F1**: verdict가 SHIP-READY OR SHIP-WITH-CARRYFORWARDS면 진행.

### 운영 방식

이 세션. CHANGELOG.md에 Spike XIII 항목 추가 + V4 release gate PASS 명시.

### Acceptance

- `CHANGELOG.md`에 Spike XIII 블록 추가
- ship commit message에 "V4 release gate PASS" 명시
- 메모리 갱신 (`project_assemble_v4_spike_xiii.md` + MEMORY.md index)
- master push
- V4 ship 알림 (텔레그램)

### NEEDS-FIX 분기

verdict가 NEEDS-FIX OR NEEDS-MAJOR-REWORK면:
- Phase F skip
- Spike XIV spec/plan 작성 시작
- B-19 캡쳐 분석 결과를 Spike XIV 입력으로

### Commit (SHIP 분기)

```
docs(v4-spike-xiii): ship — V4 PASSED release gate, paradigm verified

V4 결정 #6 release gate PASS — Spike XIII Phase G blank-environment
dogfood 통과. 빈손 환경 + 사용자 perspective에서 V4 paradigm 약속이
실제로 작동하는 것을 검증.

검증 결과:
- B-18 자동 sanity probe: 12/12 AC PASS
- B-19 lived dogfood: 한 프로젝트 완주, <count> 캡쳐, 결함 분류 끝
- final verdict: <verdict>

V4 release-gate progression (완료):
✅ V4 결정 #1 라인업 10/10 (Spike XI)
✅ /assemble eject 인프라 (Spike XII)
✅ Phase G 빈손 컴 dogfood (Spike XIII, this commit)

V4 ship — 다음은 V5 backlog (roles.json 파일화 / F4 perf / symlink mode / etc.)

Refs: docs/specs/2026-05-06-v4-spike-xiii-design.md
```

---

## V4 정체성 보호 (변경 X)

Locked invariants — Spike XIII에서 어떤 변경도 안 됨:

- ✅ canonical preamble v3 sha: `8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9`
- ✅ ALLOW_LIST = {v1, v2, v3}
- ✅ ALLOWED_PROMPT_FILES = 42 entries (basename form)
- ✅ _PROMPT_TO_STAGE = 42 entries
- ✅ STAGE_CATEGORY_PRIORITY = 10 stages
- ✅ _BUNDLES / _BUNDLED_DIR_TO_STAGE = 10 entries (BOTH harness + inventory)
- ✅ 7 ★ + 3 표준 bundle prompts
- ✅ V3 concierge §1-§7 default flow
- ✅ orchestrator-only V4 #9 — eject은 IO exception
- ✅ harness.py / inventory.py public API

위 항목 변경 발견 시 = 결함. 즉시 Spike XIV로.

---

## Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | ASSEMBLE_HOME tempdir이 fresh와 다름 | medium | low | setup script `env -i` 격리 |
| R2 | 별도 세션도 같은 Claude 모델 → 100% 외부 X | high | medium | V5 외부 베타로 보완 |
| R3 | 캡쳐 누락 결함 | medium | medium | 40 캡쳐 표준화 |
| R4 | 사용자 시간 부담 | low | low | 비동기 진행 |
| R5 | B-19 결함 → Spike XIV 추가 비용 | medium | medium | 자연스러움 |
| R6 | 별도 세션 ASSEMBLE_HOME 인식 안 됨 | low | high | setup script verify |

---

## Carryforward register (Spike XIV+ / V5 inheritance)

Spike XIII에서 발견될 수 있는 결함은 모두 Phase D 분석에서 분류:

- **Critical** → Spike XIV 즉시 fix
- **Important** → 결함 종류에 따라 fix or carryforward
- **Minor / Cosmetic** → V5 backlog
- **이전 spike에서 누적된 V5 backlog** (M-XII4 등) → 그대로 유지

---

## Source

- Plan: this file
- Spec: `docs/specs/2026-05-06-v4-spike-xiii-design.md`
- Pre-scan baseline: master `ea15ea1`, pytest 813, ALLOWED_PROMPT_FILES 42, STAGE_CATEGORY_PRIORITY 10
- Parent: `~/.claude/projects/-Users-yonghaekim-my-folder/memory/project_assemble_v4_spec.md`
- Sibling: `~/.claude/projects/-Users-yonghaekim-my-folder/memory/project_assemble_v4_spike_xii.md`
