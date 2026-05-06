# V4 Spike XIII Design — Phase G blank-Mac dogfood (V4 release gate)

**Date**: 2026-05-06
**Status**: draft (pre-review)
**Parent**: `project_assemble_v4_spec.md`, `project_assemble_v4_spike_xii.md`

---

## Scope

V4 결정 #6 명시: "**빈손 컴 dogfood가 V4 출시 게이트**". Spike XIII는 그 게이트.
이전 Spike I~XII는 모두 *내부* dogfood (assemble을 자체 dogfood로 운영) 였으나
Spike XIII는 *외부* dogfood — fresh user perspective + 빈손 환경에서 V4 paradigm
약속이 실제로 지켜지는지 검증.

### 현실적 제약 + 절충

완전 새 맥북 / 새 사용자 계정 마련은 비용·시간 큼. 본질은 *fresh 하드웨어*가
아니라 *fresh 사용자 perspective + 빈손 환경*. 따라서 Spike XIII = 자동 sanity
probe (코드/contract 무결성) + 사용자 lived dogfood (UX/판단) **분할 운영**:

| 트랙 | 범위 | 운영 방식 |
|---|---|---|
| **B-18** | 빈손 환경 sanity probe (자동) | 이 세션, ASSEMBLE_HOME tempdir, 12 AC |
| **B-19** | lived dogfood (사용자 운전) | 별도 세션, 40 캡쳐, 한 프로젝트 완주 |

B-18은 코드/contract 무결성 80%를 미리 잡아 사용자 부담 최소화. B-19는 UX/4원칙
판단 등 인간 시야가 필요한 20%만 사용자에게 위임.

### Ship gate

**B-18 PASS + B-19 verdict ∈ {SHIP-READY, SHIP-WITH-MINOR-CARRYFORWARDS}** → V4 출시.

B-19 verdict ∈ {NEEDS-FIX, NEEDS-MAJOR-REWORK} → Spike XIV+ cleanup spike(s) 후
재실행.

### Out of scope (V4 비범위 — Spike XIV+ 또는 V5)

- ❌ 진짜 새 맥북 (완전 hardware-fresh) dogfood — V5 외부 사용자 베타 트랙
- ❌ Codex CLI / Gemini CLI 호환 검증 — V4 비범위 동결
- ❌ Multi-user / shared `~/.claude` 환경 검증 — V5
- ❌ Windows / WSL 환경 검증 — V4 macOS/Linux 전용
- ❌ 새 사용자 신규 가입 시뮬레이션 — V5 외부 베타
- ❌ 7 minor carryforwards (M-XII4 backup OSError wrapping / F4 perf collapse / F-XII1~5) — V5
- ❌ roles.json 파일 도입 (메모리에만 spec, 디스크 X) — separate spike
- ❌ 새 번들 추가 — V4 결정 #1 라인업 10/10 동결

---

## Phase A learnings to apply (Spike XII codebase enforcement scan)

Per `project_assemble_v4_spec.md` § "Spec/plan 작성 전 codebase enforcement scan".
Pre-scan 7-step 결과 (master `ea15ea1` 기준):

| # | 항목 | 결과 |
|---|---|---|
| 1 | pytest baseline | **813 passed** (Spike XII cleanup 후) |
| 2 | frontmatter convention | `test_yaml_strict_load.py` enforced |
| 3 | bidirectional integrity | `test_allowed_prompt_files_matches_bundle_inventory` auto-derived |
| 4 | _PROMPT_TO_STAGE values ⊆ STAGE_CATEGORY_PRIORITY keys | 10 stages |
| 5 | STAGE_CATEGORY_PRIORITY count | 10 (debug/design/discover/execute/meta/plan/review/safety/ship/verify) |
| 6 | WROTE: contract | line 1 of dispatchable prompts |
| 7 | ALLOWED_PROMPT_FILES count | 42 BASENAMES |

Spike XIII은 코드 변경 거의 없음 (B-18 probe 신규 + setup script + 가이드 doc).
변경 footprint:
- `tests/dogfood/spike_xiii_b18.py` (NEW)
- `scripts/spike_xiii_b19_setup.sh` (NEW, optional)
- `docs/dogfood/spike-xiii-b19-capture-guide.md` (NEW)
- `docs/dogfood/spike-xiii-b18.md` (B-18 결과 리포트)
- `docs/dogfood/spike-xiii-b19.md` (B-19 캡쳐 분석 리포트)
- `docs/dogfood/spike-xiii-overall-review.md` (Phase E)
- 결함 발견 시: 해당 fix commit (스코프는 결함 종류에 따라)

V4 정체성 invariant — 모두 변경 X.

---

## B-18 — automated blank-environment sanity probe (Phase A)

이 세션에서 실행. 자동, 결정적, 12 AC 형식.

### Setup contract

1. `tempfile.mkdtemp(prefix='spike-xiii-b18-')` 으로 fresh ASSEMBLE_HOME 생성
2. 실제 `~/.claude/skills/assemble/` 전체를 tempdir에 복사 (assemble은 있어야 동작)
3. 다른 스킬 / 에이전트 / 플러그인 캐시는 **0개** (빈손 환경)
4. `ASSEMBLE_HOME=<tempdir>` env 설정
5. `inventory.scan(force=True)` 호출 → 결과 검증
6. 메뉴 렌더링 (build_stage_options) → bundled-only fallback hint 검증
7. 모든 번들 SKILL.md frontmatter / contracts / prompts 무결성 검증
8. cleanup: `shutil.rmtree(tempdir)` in finally

### 12 acceptance criteria

| # | Check | PASS condition |
|---|---|---|
| AC1 | tempdir setup successful | assemble dir copied with all 10 bundles + _shared |
| AC2 | inventory.scan() returns ≥10 skills | bundled 번들 모두 인식 |
| AC3 | 모든 번들 entry has `bundled=True` | inventory `_is_bundled` 정상 |
| AC4 | 사용자 스킬 0개 | bundled-only 환경 검증 |
| AC5 | menu shows ★ prefix on bundled bundles | i18n keys `menu.bundled_prefix` 정상 |
| AC6 | menu fallback hint shown | `notices.bundled_only_hint` 정상 |
| AC7 | 모든 번들 SKILL.md frontmatter parses (yaml.safe_load) | yaml 무결성 |
| AC8 | 모든 dispatchable prompt 등재 in ALLOWED_PROMPT_FILES | bidirectional integrity |
| AC9 | 모든 contract entries (contracts.json) loadable | 번들 contracts 무결성 |
| AC10 | canonical preamble v3 sha = `8d22a29c97...089a9` | identity invariant |
| AC11 | /assemble eject sub-command resolves | SKILL.md sub-command router 작동 (text scan) |
| AC12 | dogfood doc generated | `docs/dogfood/spike-xiii-b18.md` |

### Wall-time budget

≤30s for all 12 AC. 참조: B-17 0.018s, B-15 0.26s, B-16 0.422s. B-18은 inventory.scan
+ frontmatter parse 정도라 ≤2s 예상.

### Output

- `tests/dogfood/spike_xiii_b18.py` (probe, ~250 LoC)
- `tests/dogfood/__init__.py` (이미 존재)
- `docs/dogfood/spike-xiii-b18.md` (verdict 리포트)

### B-18 발견 가능 결함 유형

- inventory.scan() 폴백 깨짐
- 번들 SKILL.md frontmatter 깨짐
- contracts.json schema drift
- canonical preamble v3 sha drift
- bundled-only menu hint 깨짐
- prompt 등재 누락
- /assemble eject sub-command router 깨짐 (regex/text-level)

이 결함들은 사용자가 운전 시작 전 잡혀야 함 — B-18 fail = B-19 시작 안 됨.

---

## B-19 — lived dogfood (Phase B+C, 별도 세션, 사용자 운전)

핵심 — UX / 판단 / 4원칙 위반은 인간 시야가 필요. 자동 검증 불가.

### Setup script (Phase B)

`scripts/spike_xiii_b19_setup.sh` 작성 — 사용자가 별도 세션에서 실행:

```bash
#!/usr/bin/env bash
# Spike XIII B-19 lived dogfood — 빈손 환경 setup
set -euo pipefail

# Fresh tempdir for ASSEMBLE_HOME
TEMP_HOME=$(mktemp -d -t spike-xiii-b19-XXXXXX)
echo "ASSEMBLE_HOME: $TEMP_HOME"

# Copy assemble (only assemble — 다른 스킬 0개)
mkdir -p "$TEMP_HOME/.claude/skills"
cp -R "$HOME/.claude/skills/assemble" "$TEMP_HOME/.claude/skills/assemble"

# Verify 빈손
SKILL_COUNT=$(ls -1 "$TEMP_HOME/.claude/skills/" | wc -l | tr -d ' ')
if [ "$SKILL_COUNT" != "1" ]; then
    echo "ERROR: 빈손 환경 검증 실패 — $SKILL_COUNT skills present"
    exit 1
fi

# Print env export instructions
cat <<EOF

✅ Setup complete.

다음 명령으로 별도 세션 진입:

    ASSEMBLE_HOME=$TEMP_HOME claude

별도 세션에서 시작 명령 (예시):

    /assemble 작은 CLI 도구 만들고 싶어

캡쳐 가이드:

    cat ~/.claude/skills/assemble/docs/dogfood/spike-xiii-b19-capture-guide.md

종료 후 cleanup:

    rm -rf $TEMP_HOME
EOF
```

### 캡쳐 표준 (Phase B, 가이드 문서)

`docs/dogfood/spike-xiii-b19-capture-guide.md` 작성 — 형이 별도 세션에서 따라할
표준화된 40 캡쳐 (10 stages × 4 항목).

각 stage 종료 시 4 항목:

1. **Stage 시작 명령 + main Claude 응답 헤더 (~5줄)** — text 캡쳐
2. **산출물 파일 경로** — `~/.assemble/runs/<rid>/<artifact>.md` 위치 + 파일 크기
3. **막힌 지점 / 어색한 UX** — 자유 노트 (한 줄~ 한 단락)
4. **4원칙 위반 의심** — 메인 직접 작업 / 추측 코딩 / 곁가지 수정 / AC 자기선언 (있으면 노트)

### Stage 진행 순서 + 검증 게이트

| # | Stage | 번들 | 검증 게이트 |
|---|---|---|---|
| 1 | discover | idea-shaper (표준) | IDEA.md 5 sections 채워짐, 사용자 / 문제 / wedge / non-goals 명확 |
| 2 | plan | plan-pack ★ | PRD/ARCH/ADR/UI_GUIDE 4종 docs 일관성, AC bash 실행 가능 |
| 3 | design | design-pack (표준) | DESIGN.md + ANTI_PATTERNS.md 작성, AI 슬롭 회피 |
| 4 | execute | builder ★ | TDD 흐름 강제, surgical change boundary 준수 |
| 5 | debug | debugger ★ | 가설→재현→이등분→근본원인 흐름, Iron Law 준수 |
| 6 | review | reviewer ★ | diff 범위 vs SCOPE 비교, 객관 위험 항목 0건 |
| 7 | verify | verifier ★ | AC bash 실제 실행, exit code 기반 verdict |
| 8 | ship | shipper ★ | preflight pass, version bump, build, tag (local-only) |
| 9 | safety | guardian (표준) | GUARDIAN.md 4 placeholder + 5 checkbox 명확 |
| 10 | meta | keeper ★ | KEEPER_REPORT 7-section, audit-clean OR audit-flagged |

각 stage 끝나면 형이 4 캡쳐 → 다음 stage. 마지막 keeper에서 트레이스 자가 점검 +
학습 회수 동작 확인.

### Project 선택 옵션 (사용자 결정)

3 후보:
1. **(권장) 작은 CLI 도구 신규** — 예: 마크다운 → Plain text 변환기. 30분~1시간.
2. **가상 PRD** — "X 기능 추가" 가상 시나리오. 산출물만 검증.
3. **(메타) Spike XII 자체를 재현** — recursive dogfood. Spike XII spec/plan/code를
   빈손 환경에서 다시 만들기. 시간 큼 — 비추.

권장 = 1. 시간 적당하고 모든 stage 자연스럽게 통과.

### 캡쳐 분석 (Phase D, 다시 이 세션)

형이 캡쳐 가져오면 분석:

| 결함 분류 | 처리 |
|---|---|
| **Critical** | ship 차단 — fix spike (Spike XIV) 즉시 필요 |
| **Important** | ship 차단 가능 — 결함 종류에 따라 fix or carryforward |
| **Minor** | ship-with-carryforward — V5 deferral |
| **Cosmetic** | nice-to-have — V5 deferral |

### 발견 가능 결함 유형 (B-19에서만 잡힘)

- 사용자가 어디서 막히는지 (UX 결함)
- 메뉴 옵션이 헷갈리는지
- 메인 Claude가 4원칙 위반하는지 (추측 코딩, 곁가지 수정 등)
- 산출물 품질 미달 (PRD MVP 제외 누락 / ADR 트레이드오프 빠짐 / etc.)
- harness preamble prepend 효과 부족
- 트레이스 학습 회수가 다음 run에 효과 미반영
- /assemble eject UX (Spike XII cleanup으로 보강한 부분 실전 검증)

---

## V4 정체성 보호 (변경 X)

- ✅ Spike I~XII core contracts unchanged
- ✅ canonical preamble v3 sha unchanged: `8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9`
- ✅ ALLOW_LIST = {v1, v2, v3} unchanged
- ✅ ALLOWED_PROMPT_FILES = 42 entries unchanged
- ✅ _PROMPT_TO_STAGE = 42, _BUNDLES = 10
- ✅ STAGE_CATEGORY_PRIORITY = 10 stages
- ✅ 7 ★ + 3 표준 bundle prompts unchanged
- ✅ V3 concierge §1-§7 default flow unchanged
- ✅ orchestrator-only V4 #9 — eject은 IO exception, V3 concierge default
- ✅ harness.py / inventory.py public API unchanged

Spike XIII는 본질적으로 *검증 spike*이지 *변경 spike*가 아님. fix가 필요하면
별도 Spike XIV로 분리.

---

## Surgical change boundary

| File | Change kind | Lines |
|---|---|---|
| `tests/dogfood/spike_xiii_b18.py` | NEW | ~250 |
| `scripts/spike_xiii_b19_setup.sh` | NEW | ~50 |
| `docs/dogfood/spike-xiii-b19-capture-guide.md` | NEW | ~150 |
| `docs/dogfood/spike-xiii-b18.md` | NEW (Phase A 산출) | ~80 |
| `docs/dogfood/spike-xiii-b19.md` | NEW (Phase D 분석) | ~150 |
| `docs/dogfood/spike-xiii-overall-review.md` | NEW (Phase E) | ~100 |
| `docs/specs/2026-05-06-v4-spike-xiii-design.md` | NEW (this) | — |
| `docs/plans/2026-05-06-v4-spike-xiii.md` | NEW | — |
| `CHANGELOG.md` | append entry | ~15 |

총 9 NEW + 1 EDIT (CHANGELOG). 코드 변경 거의 없음.

---

## Codex retro 결정

표준 skip. Spike XIII는 *검증* spike — 새 코드 surface 거의 없음. B-18 probe도
read-only inventory + frontmatter parse. Bash surface = 0.

Codex retro 승격 조건:
- B-18에서 V4 identity invariant 깨짐 발견 → Codex retro로 승격해서 root cause
- B-19 lived dogfood에서 Critical 결함 발견 → fix spike 시작 시 Codex retro 사용

---

## Phase mapping

| Phase | Scope | 운영 |
|---|---|---|
| A | B-18 자동 sanity probe | 이 세션, 자동 |
| B | B-19 setup 스크립트 + 캡쳐 가이드 | 이 세션, doc/script 작성 |
| C | B-19 lived dogfood 실행 | **별도 세션, 형이 운전** (비동기) |
| D | 캡쳐 분석 + verdict | 이 세션, 형이 캡쳐 가져온 후 |
| E | overall review + ship verdict | 이 세션, 종합 |
| F | (조건부) CHANGELOG flip + ship | verdict가 SHIP이면. NEEDS-FIX면 Spike XIV로 |

---

## Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | ASSEMBLE_HOME tempdir이 fresh 환경과 다름 (~/.zshrc 영향) | medium | low | setup script `env -i` 격리 권장 |
| R2 | 별도 세션도 Claude 같은 모델 → 100% 외부 검증 X | high | medium | V5 외부 베타로 보완. V4 ship gate는 이 단계로 충분 |
| R3 | 캡쳐 항목에서 빠진 결함 | medium | medium | spec에 표준화된 40 캡쳐 명확 정의 |
| R4 | 사용자 시간 부담 (~50분) | low | low | 비동기 — 시간 날 때 진행 |
| R5 | B-19 결함 발견 → Spike XIV 추가 비용 | medium | medium | 자연스러운 진행. Spike XII cleanup도 5건 처리했음 |
| R6 | 별도 세션에서 ASSEMBLE_HOME 인식 안 됨 | low | high | setup script가 verify 명령 포함 |

---

## Carryforward openness

B-18 / B-19에서 발견될 잠재 carryforwards (Spike XIV+ 또는 V5):

- 빈손 환경에서만 reproducible한 inventory 결함 → fix in Spike XIV
- 4원칙 위반 패턴 발견 → 해당 번들 prompt 강화 spike
- 산출물 템플릿 빈약 → 템플릿 polish spike
- 메뉴 UX 어색함 → menu i18n / wording polish spike
- /assemble eject 실전 결함 → eject 추가 polish spike
- Cosmetic / 메모리 spec drift → reconciliation commit (Spike XI 패턴)

---

## V5 backlog (V4 비범위 — Spike XIII 끝나도 안 건드림)

이전 spike에서 누적된 V5 후보 (확인용):

- M-XII4 backup OSError → EjectError wrapping
- F-XII1 symlink mode (--link)
- F-XII2 auto-rename on conflict
- F-XII3 frontmatter rewrite on copy
- F-XII4 trace ledger entry for eject events
- F-XII5 .bak.<ts> cleanup helper
- F4 perf collapse (reviewer ★ deterministic shell)
- roles.json 파일 도입
- Multi-language version bumping
- Multi-run concurrency safety
- PII redaction in evidence
- Build command sandboxing
- Codex CLI / Gemini CLI 호환
- 외부 사용자 베타 (진짜 새 맥북)

---

## Source

- Spec: this file
- Plan: `docs/plans/2026-05-06-v4-spike-xiii.md`
- Parent: `~/.claude/projects/-Users-yonghaekim-my-folder/memory/project_assemble_v4_spec.md`
- Sibling: `~/.claude/projects/-Users-yonghaekim-my-folder/memory/project_assemble_v4_spike_xii.md`
- Pre-scan: master `ea15ea1`, pytest 813, ALLOWED_PROMPT_FILES 42, STAGE_CATEGORY_PRIORITY 10
