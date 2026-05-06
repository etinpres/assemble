# V4 Spike XIV Design — Spike XIII NEEDS-FIX cleanup (paradigm hybrid)

**Date**: 2026-05-06
**Status**: draft (pre-review)
**Parent**: `project_assemble_v4_spec.md`, `project_assemble_v4_spike_xiii.md`

---

## Scope

Spike XIII (V4 release gate) verdict = **NEEDS-FIX**. 본 dogfood 90분 23초 완주 후
산출물은 정상이지만 V4 paradigm 약속과 실제 동작 사이 5+ gap 발견. Spike XIV는
그 gap 들을 닫는 *fix spike* — 코드/SKILL.md/contract 정정 + B-20 재검증으로
SHIP-READY 도달.

### Spike XIII NEEDS-FIX 결함 (입력)

| Severity | ID | 결함 | 본 spike Phase |
|---|---|---|---|
| Critical | C1 | ASSEMBLE_HOME env 비전파 (별도 세션 sub-agent dispatch에 미상속) | A |
| Critical | C2 | V4 #11 parallel violation 시스템적 (★ paradigm 통합 1 dispatch 단축) | B |
| Important | I1 | iter1 default = "no" — plan-pack ★ multi-iteration 약속 위배 | C |
| Important | I2 | interview 단축 패턴 (메인 자가 결정, C2와 같은 root cause) | B |
| Important | I3 | orthogonal stage marker (mark_stage('safety'/'meta')) ValueError | D |
| Important | I4 | SKILL.md doc drift (dispatch_prompt 시그니처 stale) | E |
| Minor (V5) | M1/M2/M3 | Bash hook recurring blockage / 메뉴 옵션 6개 / design-pack vs plan-pack UI_GUIDE 중복 | (V5) |

### Paradigm 결정 — Option 3 hybrid (Spike XIII에서 동결, 본 spec에서 구현)

3 옵션 토론 후 hybrid 채택:
- **default = full spec follow** (★ paradigm 약속 보존: 4-7 sub-agent dispatch + 3-7 iteration)
- **opt-in 단축 모드** — 사용자가 stage 시작 시 *명시 동의* 후에만 통합 1 dispatch 허용
- **AskUserQuestion 시스템적 강제** — 텍스트 룰 → workflow 분기 강제. C2 root cause (메인 자가 판단) 완전 제거.
- **harness preamble v3 sha 보존** (v4 bump X) — 4원칙 #1 wording 강화는 *SKILL.md 머리말 + dispatch contract description* 측에서 하고 preamble 본문 미변경 유지.

이유:
1. V4 약속 보존 (default = full)
2. 현실 budget 인정 (opt-in 단축)
3. 4원칙 #1 진짜 작동 (사용자 명시 동의 시스템적 강제)
4. C1 fix는 paradigm과 직교 — 무조건 1순위
5. iter1 default = yes (I1)와 일관
6. ALLOW_LIST 확장 비용·과거 audit 데이터 호환·preamble 본문 부족 아닌 enforcement 인프라 부족이 root cause인 점에서 v3 보존이 옳음

거부:
- Option 1 (강화) — 메인 후속 위반 위험. 빈손 사용자 90분 dogfood 견디기 어려움
- Option 2 (retreat) — V4 ★ paradigm 가치 무력화. "★" 의미 모호화
- Option v4 bump — preamble 본문 자체에 "사용자 동의 없이 단축 금지" 한 줄 추가 가능하지만, 이미 v3에 7 rule (4원칙 + rule 5/6/7) 있어 8번째 rule 추가 시 ALLOW_LIST 확장 + audit 데이터 호환 비용. enforcement는 SKILL.md 측이 더 자연.

### Out of scope (V4 비범위 — V5)

- ❌ M1 Bash guard hook 학습 메커니즘 — V5
- ❌ M2 메뉴 옵션 6개 → 3개 reduce — V5 UX polish
- ❌ M3 design-pack과 plan-pack UI_GUIDE 중복 area — V5 bundle scope 재검토
- ❌ 진짜 새 맥북 dogfood — V5 외부 베타
- ❌ Codex CLI / Gemini CLI 호환 — V4 비범위 동결
- ❌ harness preamble v4 bump — 본 spec § "Paradigm 결정"에서 명시 거부
- ❌ Spike XIII 누적 V5 backlog (M-XII4 / F-XII1~5 / F4 perf / roles.json / multi-language version bumping / multi-run concurrency / PII redaction / build sandboxing)

---

## Phase A learnings to apply (Spike XIII codebase enforcement scan)

Per `project_assemble_v4_spec.md` § "Spec/plan 작성 전 codebase enforcement scan".
Pre-scan 7-step 결과 (master `6b989a2` 기준):

| # | 항목 | 결과 |
|---|---|---|
| 1 | pytest baseline | **813 passed** in 17.16s |
| 2 | frontmatter convention | `test_yaml_strict_load.py` enforced (double-quoted + JSON-array stages) |
| 3 | bidirectional integrity | `test_allowed_prompt_files_matches_bundle_inventory` auto-derived from disk + ORCHESTRATOR_ONLY_PROMPTS exclusion |
| 4 | _PROMPT_TO_STAGE values ⊆ STAGE_CATEGORY_PRIORITY keys | enforced via `test_prompt_to_stage_values_are_known_stages` |
| 5 | STAGE_CATEGORY_PRIORITY count | 10 (debug/design/discover/execute/meta/plan/review/safety/ship/verify) |
| 6 | WROTE: contract | line 2 of dispatchable prompts (line 1 = H1 title) — 38 prompts 모두 준수 |
| 7 | ALLOWED_PROMPT_FILES count | 42 BASENAMES |

추가 finding (Spike XIII에서 발견 못 한 것):
- preamble v3 본문은 **이미 7-rule** (rule 5 외래어 / rule 6 task scope seed / rule 7 인프라 코드 격리). canonical sha = `8d22a29c…089a9` 보존 결정 → 본 spec은 본문 미변경.
- I4 doc drift 사전 식별: `bundled/design-pack/SKILL.md:34` (`dispatch_prompt('design_draft_step1.md', run_id)`) + `bundled/idea-shaper/SKILL.md:33` (full path + run_id)
- Phase D (mark_orthogonal_stage) — 현 `mark_stage`는 sequence 기반 검증 (`if idx is None: raise ValueError`). orthogonal stages는 sequence와 별도 → progress.json schema에 `orthogonal_stages` field 신설 + 새 API 함수가 자연.

V4 정체성 invariant — 모두 변경 X.

---

## V4 정체성 보호 (변경 X)

본 spike 가 변경하지 않는 invariants:

- ✅ canonical preamble v3 sha = `8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9` (Phase A는 [TASK] body 안 ASSEMBLE_HOME 주입, preamble 본문 미변경)
- ✅ ALLOW_LIST = `{v1, v2, canonical=v3}` 그대로 (확장 X)
- ✅ ALLOWED_PROMPT_FILES = 42, _PROMPT_TO_STAGE = 42, _BUNDLES = 10, _BUNDLED_DIR_TO_STAGE = 10
- ✅ STAGE_CATEGORY_PRIORITY = 10 stages 그대로
- ✅ V3 concierge §1-§7 default flow textually unchanged
- ✅ V4 결정 16개 그대로 (#1 라인업 10/10, #6 release gate, #9 orchestrator-only, #11 parallel)
- ✅ 7 ★ + 3 표준 bundle prompts 본문 unchanged (Phase B는 SKILL.md 머리말 wording + AskUserQuestion gate 추가만)
- ✅ harness.py / inventory.py / eject.py public API unchanged

---

## Phase A — C1 fix (ASSEMBLE_HOME auto-prepend in dispatch body)

**시간 예산**: ~1h | **subagent 1번** | **commit 단위**: 1 atomic

### 문제 진단

별도 Claude Code 세션에서 `ASSEMBLE_HOME=<path> claude` 진입해도 sub-agent
dispatch 시 메인이 캡쳐한 env가 미상속됨. 빈손 dogfood 환경 격리 (V4 결정 #6
본질) 깨짐. 수동 우회: 매 dispatch prompt에 `os.environ['ASSEMBLE_HOME']`
prepend — 사용자 부담 + setup script로는 강제 불가.

### Fix design (preamble 본문 미변경)

`server/harness.py::wrap_with_preamble` 호출 시점에 *body 영역* 첫 줄로
ASSEMBLE_HOME 설정 instruction을 자동 주입. preamble 자체는 byte-identity
유지 (sha v3 보존):

```python
def wrap_with_preamble(prompt: str) -> str:
    pre = _load_preamble()
    if pre is None:
        return prompt
    asm_home = os.environ.get("ASSEMBLE_HOME")
    if asm_home:
        # body region: ASSEMBLE_HOME pin이 있으면 본문 첫 줄에 명시.
        # preamble portion은 미변경 → canonical sha 보존.
        body = (
            f"[ENV] 이 dispatch는 ASSEMBLE_HOME={asm_home} 환경에서 실행됨. "
            f"sub-agent가 server.* 모듈을 import 할 때 메인과 동일 home 보장. "
            f"코드에서 `os.environ['ASSEMBLE_HOME']` 또는 Path 조립 시 이 값 우선.\n\n"
            f"{prompt}"
        )
    else:
        body = prompt
    return f"{pre}\n[TASK]\n{body}"
```

### Acceptance criteria

| AC | Check | PASS condition |
|---|---|---|
| A.AC1 | preamble portion 미변경 | `_split_preamble_body` 결과의 preamble bytes == `_load_preamble()` bytes |
| A.AC2 | canonical sha v3 보존 | `canonical_preamble_sha256()` 반환값 unchanged after Phase A |
| A.AC3 | ASSEMBLE_HOME 미설정 시 동작 | `del os.environ['ASSEMBLE_HOME']` 후 `wrap_with_preamble("foo")`는 ASSEMBLE_HOME 줄 없이 반환 |
| A.AC4 | ASSEMBLE_HOME 설정 시 body 첫 줄 주입 | `os.environ['ASSEMBLE_HOME']='/tmp/x'` 후 wrap 결과 body가 `[ENV] 이 dispatch는 ASSEMBLE_HOME=/tmp/x` 로 시작 |
| A.AC5 | dispatches.jsonl 호환 | record_dispatch가 preamble_sha256 그대로 기록, audit verify 그대로 PASS |
| A.AC6 | record_dispatch + verify_dispatches 회귀 0 | 기존 813 tests + 새 4 tests 모두 PASS |

### Test 추가

`tests/unit/test_wrap_with_preamble_assemble_home.py` (NEW, ~4 tests):
- `test_assemble_home_unset_no_injection` — env 없으면 body 미변경
- `test_assemble_home_set_injects_first_body_line` — env 있으면 body 첫 줄 주입
- `test_preamble_portion_byte_identity` — preamble 부분은 항상 v3 sha
- `test_record_dispatch_audit_still_green` — record_dispatch 후 verify_dispatches OK

### Risk register

- R-A1: dispatchable prompt 본문 자체가 `[ENV]` 시작이면 충돌 → 38 prompts 모두 line 2 = `WROTE:` 명시. `[ENV]` 시작은 0개. 검증 통과.
- R-A2: 기존 dogfood data (Spike XIII B-18) 가 ENV 줄 없는 prompt body로 기록되어 있으면 audit 깨질까? → audit는 *preamble sha*만 체크. body는 비교 X. 회귀 0.

---

## Phase B — C2/I2 fix (★ paradigm hybrid: default=full + opt-in --quick)

**시간 예산**: ~2h | **subagent 1번** | **commit 단위**: 1 atomic (7 ★ 번들 SKILL.md + 4원칙 #1 wording 강화)

### 문제 진단

7 ★ stage가 시스템적으로 통합 1 dispatch 로 단축됨 (spec 명시 4-7 sub-agent dispatch 무시).
메인 Claude가 자가 판단 ("시간 한계") — 사용자에게 묻지 않음. harness 4원칙 #1 + V4 #11
+ V4 #9 모두 위반. 단축 결정이 메인 머릿속에 갇혀 audit row 누락.

★ paradigm 자체가 메인 컨텍스트 budget 한계로 작동 불가 → V4 약속의 fundamental
한계. 텍스트 룰 ("4-7 dispatch 분할") 으로는 못 막음.

### Fix design — Option β (AskUserQuestion 시스템적 강제)

각 ★ 번들 SKILL.md 머리말에 *Stage 진입 mode-gate* 추가:

```markdown
## Mode gate (V4 Spike XIV — paradigm enforcement)

★ 번들 진입 직후 (Step 0 직전), 메인은 다음 AskUserQuestion 을 무조건 발사:

  "이번 stage 모드 — 어떻게 진행할까?"

  옵션:
    1. full mode (추천) — spec 명시 N-step pipeline 그대로. 정확·완성도 우선.
       예상 시간: <X분>. dispatch 수: <Y회>.
    2. quick mode — 통합 1 dispatch 로 압축. 시간 부족 시만 선택.
       precision 손실 + iteration 권장량 미달 위험. KEEPER_REPORT 에 카운트 기록.

`full` 선택 시 → 아래 Step 0~N 순서대로 spec 그대로 진행.
`quick` 선택 시 → §"Quick mode flow" 단축 분기로 진입.

**메인 자가 판단 금지** — 시간 부족 추측·budget 추측·맥락 추측 모두 사용자
질문 강제 trigger. 4원칙 #1 ("불확실하면 추측 금지, 사용자 질문 우선") 시스템적
강제.
```

각 ★ 번들 SKILL.md 끝부분에 § "Quick mode flow" 추가 — 통합 1 dispatch fallback.
산출물 1개 + dispatches.jsonl 에 `mode=quick` 메타 표기. KEEPER_REPORT 가 stage 별
mode 카운트 표시.

### 4원칙 #1 wording 강화 (preamble 본문 미변경 — sha v3 보존)

preamble v3 본문은 그대로. 강화는 다음 두 surface 에서:

1. **★ 번들 SKILL.md 머리말** (위 mode-gate block) — 모든 ★ 번들 동일 wording.
2. **dispatch contract description** — `bundled/<name>/SKILL.md` § "Step dispatch contract"
   에 다음 한 줄 추가:
   > **사용자 명시 동의 없이 단축 금지** — N-step pipeline 의 각 step 은
   > 별도 sub-agent dispatch 로 진행. 메인이 단축 결정 시 4원칙 #1 위반.
   > Mode-gate 가 quick 으로 답한 경우만 §"Quick mode flow" 분기 허용.

### 적용 범위 (★ 번들 7개)

| ★ 번들 | full mode N-step | quick fallback 산출물 |
|---|---|---|
| plan-pack | 13 step (4-way parallel docs) | PRD 1 doc 통합 + 4 sections (ARCH/ADR/UI_GUIDE 인라인) |
| builder | 7 step | IMPL_REPORT 1 doc 통합 |
| debugger | 6 step | DEBUGGER_LOG 1 doc 통합 |
| reviewer | 5 step | REVIEW_REPORT 1 doc 통합 |
| verifier | 4 step | VERIFY_REPORT 1 doc 통합 |
| shipper | 4 step | SHIPPER_LOG 1 doc 통합 |
| keeper | 6 step | KEEPER_REPORT 1 doc 통합 |

각 ★ 번들 quick mode 는 *동일 산출물 schema* 유지 (sections 보존), dispatch 만 1 회.

### KEEPER_REPORT 단축 모드 카운트 (선택, 가벼움)

`bundled/keeper/templates/KEEPER_REPORT.md.template` 에 다음 section 추가:

```markdown
## Mode usage

| stage | mode | dispatches | rationale |
|---|---|---|---|
| {{STAGE}} | {{full|quick}} | {{N}} | {{user reason or "—"}} |

quick 카운트 ≥ 1 시 노란색 경고 표시. 빈손 사용자가 다음 run 에서 더 시간 확보
권장.
```

### Acceptance criteria

| AC | Check | PASS condition |
|---|---|---|
| B.AC1 | 7 ★ 번들 SKILL.md 모두 mode-gate 머리말 보유 | grep "Mode gate" 에서 7 hit |
| B.AC2 | 7 ★ 번들 SKILL.md 모두 § "Quick mode flow" 분기 보유 | grep "Quick mode flow" 7 hit |
| B.AC3 | dispatch contract 에 "사용자 명시 동의 없이 단축 금지" 한 줄 박힘 | 7 hit |
| B.AC4 | preamble v3 sha 보존 | `canonical_preamble_sha256()` unchanged (text 변경 X) |
| B.AC5 | quick fallback 산출물 schema 일치 | 각 quick 분기 wrote_path = full mode 와 동일 산출물 path |
| B.AC6 | KEEPER_REPORT.md.template 에 Mode usage section | grep "Mode usage" 1 hit |
| B.AC7 | 표준 번들 (idea-shaper / design-pack / guardian) mode-gate 미변경 | 표준은 단일 dispatch 가 default — gate 도입 X (V4 #9 IO 예외 guardian 포함) |
| B.AC8 | 회귀 테스트 0 | pytest 813 + 새 ~7 tests 모두 PASS |

### Test 추가

`tests/unit/test_mode_gate_consistency.py` (NEW):
- `test_seven_star_bundles_have_mode_gate` — 7 SKILL.md 모두 머리말 패턴 보유
- `test_seven_star_bundles_have_quick_mode_flow_section` — 7 SKILL.md 모두 § "Quick mode flow"
- `test_dispatch_contract_has_no_self_shortcut_rule` — 7 SKILL.md 모두 한 줄 보유
- `test_three_standard_bundles_have_no_mode_gate` — idea-shaper/design-pack/guardian 머리말에 mode-gate 패턴 없음
- `test_keeper_report_template_has_mode_usage_section` — template 에 section 1 hit

### Risk register

- R-B1: SKILL.md 머리말 wording 만으로는 또 다시 메인이 우회 가능 — Spike XIII C2 root cause 재발 가능. **AskUserQuestion 강제 가 핵심**: 메인이 머릿속 판단으로 quick 진입 시도 시, mode-gate 자체가 발사 안 되면 audit 에 row 0 → 감지 가능. 추후 Spike XV 에서 PreToolUse hook 으로 `Agent` tool 호출 직전 mode-gate 발사 여부 강제 가능 (V5 후보).
- R-B2: quick mode 산출물 품질 저하 가능 — KEEPER_REPORT 카운트 표시로 사용자에게 가시화. 다음 run 에서 시간 확보 유도. quality gate 자동 차단은 V5.
- R-B3: 7 ★ 번들 일관 wording 유지 비용 — Phase E (doc drift) 와 같은 enforcement 테스트 (`test_mode_gate_consistency`) 로 사전 catch.

---

## Phase C — I1 plan-pack Step 6 default fix

**시간 예산**: ~30m | **subagent 1번** | **commit 단위**: 1 atomic

### 문제 진단

`bundled/plan-pack/SKILL.md:296` `### Step 6 prompt selector` 의 AskUserQuestion
options 빌드 시, 메인이 dogfood 시간 한계 사유로 "no — 종료" 를 1번 옵션 + 추천
으로 박음. 형 dogfood 시 iter1 stop condition (resolved=5 new=1 → spec 은 iter2
권장) 이 default 추천에 의해 무력화. plan-pack ★ 핵심 가치 (iteration 3~7회) 위배.

현 SKILL.md table 자체에는 "(추천)" 마크 없음 — runtime 메인이 박는 것. 따라서
fix 는 SKILL.md 에 *추천 알고리즘 명시* 가 핵심.

### Fix design

`bundled/plan-pack/SKILL.md` § "Step 6 prompt selector" 에 다음 추가:

```markdown
### Recommendation policy

각 prompt 호출 직전, orchestrator 가 `iteration_state.json` 의
counts (`resolved`, `new`, `unresolved`) 와 `iteration_count` 를 읽고
다음 알고리즘으로 default-recommended option 선택:

```python
def recommend_iter_continue(iteration_count, resolved, new, unresolved):
    if iteration_count >= 7:
        return "no"   # max iteration reached, ★ guideline
    if iteration_count <= 3:
        # 초기 iteration — 거의 항상 yes 권장
        if new > 0 or unresolved > 0:
            return "yes"
        if resolved < 5:  # 이슈 자체가 적으면 더 고민할 거리 없음
            return "no"
        return "yes"
    # iteration_count 4~6
    if new > 0:
        return "yes"
    if unresolved > 0:
        return "yes"
    if resolved >= 8:  # 충분히 정제됨
        return "no"
    return "yes"  # 의심스럽다면 yes
```

`AskUserQuestion` options 빌드 시:
- recommended option 의 description 끝에 ` (추천 — 사유: <iteration_count=N, resolved=X, new=Y>)` 추가
- 추천 사유에 **"dogfood 시간 한계" 또는 "시간 부족" 같은 추측 사유 박지 말 것**.
  객관 counts 만 표기.
- 사용자는 추천 무시 가능 — 추천은 default highlight 일 뿐 강제 X.
```

### Acceptance criteria

| AC | Check | PASS condition |
|---|---|---|
| C.AC1 | SKILL.md 에 § "Recommendation policy" 추가 | grep "Recommendation policy" 1 hit |
| C.AC2 | recommend_iter_continue 알고리즘 wording 명시 | iter≤3 + (new>0 or unresolved>0) → yes 명시 |
| C.AC3 | "dogfood 시간 한계" 사유 default 추천 금지 wording | grep "dogfood 시간 한계" 0 hit (역검증) + "추측 사유 박지 말 것" 1 hit |
| C.AC4 | 회귀 테스트 0 | pytest 813 + 새 ~3 tests 모두 PASS |

### Test 추가

`tests/unit/test_plan_pack_step6_recommendation.py` (NEW):
- `test_step6_skillmd_has_recommendation_policy_section` — grep
- `test_step6_skillmd_no_dogfood_time_limit_phrase` — 역검증
- `test_step6_skillmd_documents_recommend_algorithm` — iter 임계값 명시 확인

### Risk register

- R-C1: 추천 알고리즘이 SKILL.md text 만 — 메인이 또 다시 자가 판단 가능. *반드시* iteration_state.json 의 counts 를 *읽고* 박으라고 강제 wording. 알고리즘 자체는 단순 — 시각적으로 표시 가능 → 메인 우회 가능성 낮음.
- R-C2: counts 가 missing/malformed 일 때 default → SKILL.md 에 "counts 읽기 실패 시 default = yes" 한 줄 명시.

---

## Phase D — I3 orthogonal stage marker API

**시간 예산**: ~30m | **subagent 1번** | **commit 단위**: 1 atomic

### 문제 진단

`server/progress.py:48 mark_stage(rid, stage, status)` 가 `p["sequence"]` 에 없는
stage 받으면 `ValueError("stage not in sequence")`. orthogonal stages (safety/meta)
는 sequence 와 별도 → progress.json 추적 불가. dogfood 에서 메인이 우회로
mark_stage 안 부르고 기록 누락.

### Fix design

progress.json schema 확장 + 새 함수:

```python
# server/progress.py 에 추가

def _ensure_orthogonal_field(p: dict) -> None:
    """Backwards-compat: schema 확장 — 'orthogonal_stages' field 없으면 생성."""
    if "orthogonal_stages" not in p:
        p["orthogonal_stages"] = {}


VALID_ORTHOGONAL_STAGES = {"safety", "meta"}


def mark_orthogonal_stage(run_id: str, stage: str, status: str,
                           tool_used: str | None = None,
                           notes: str = "") -> dict:
    """Mark an orthogonal stage (safety, meta) — separate from main sequence.

    orthogonal stages 는 V4 결정 #1 라인업 의 가로축 (sequence 8) + 세로축
    (orthogonal 2). main sequence 와 독립적으로 활성/완료될 수 있음.
    """
    if stage not in VALID_ORTHOGONAL_STAGES:
        raise ValueError(
            f"orthogonal stage must be one of {VALID_ORTHOGONAL_STAGES}, "
            f"got {stage!r}. main-sequence stages use mark_stage()."
        )
    if status not in VALID_STATUS:
        raise ValueError(f"bad status: {status}")
    if status == "back":
        raise ValueError("'back' is sequence-only — orthogonal stages have no cursor")

    def upd(p: dict) -> dict:
        _ensure_orthogonal_field(p)
        now = datetime.now().isoformat()
        entry = p["orthogonal_stages"].get(stage, {
            "stage": stage, "status": "pending", "tool_used": None,
            "started_at": None, "ended_at": None, "notes": "",
        })

        if status == "in_progress" and entry["started_at"] is None:
            entry["started_at"] = now
        if status in TERMINAL_STATUS:
            if entry["started_at"] is None:
                entry["started_at"] = now
            entry["ended_at"] = now
            if tool_used:
                entry["tool_used"] = tool_used
        entry["status"] = status
        if notes:
            entry["notes"] = notes
        p["orthogonal_stages"][stage] = entry
        p["updated_at"] = now
        return p

    return update_json_locked(_progress_path(run_id), upd)
```

또한 `mark_stage` 가 'safety'/'meta' 받으면 자동 라우팅 (back-compat 친화):

```python
def mark_stage(run_id, stage, status, tool_used=None, notes=""):
    if stage in VALID_ORTHOGONAL_STAGES:
        # auto-route: orthogonal stages 는 mark_orthogonal_stage 로 forwarding
        return mark_orthogonal_stage(run_id, stage, status, tool_used, notes)
    # ... 기존 sequence-based 로직
```

### Acceptance criteria

| AC | Check | PASS condition |
|---|---|---|
| D.AC1 | mark_orthogonal_stage 함수 export | `from server.progress import mark_orthogonal_stage` 성공 |
| D.AC2 | 'safety' 마킹 후 progress.json 에 orthogonal_stages.safety 존재 | json 확인 |
| D.AC3 | 'meta' 마킹 후 동일 | json 확인 |
| D.AC4 | mark_stage('safety') auto-route OK | ValueError 없이 orthogonal_stages 에 기록 |
| D.AC5 | back-compat — 기존 progress.json (orthogonal_stages 없음) load 시 ValueError 없음 | _ensure_orthogonal_field 동작 |
| D.AC6 | 'safety'/'meta' 외 stage mark_orthogonal_stage 호출 시 ValueError | guard |
| D.AC7 | 회귀 테스트 0 | pytest 813 + 새 ~6 tests 모두 PASS |

### Test 추가

`tests/unit/test_mark_orthogonal_stage.py` (NEW):
- `test_mark_orthogonal_safety_creates_entry`
- `test_mark_orthogonal_meta_creates_entry`
- `test_mark_orthogonal_unknown_stage_raises`
- `test_mark_stage_safety_auto_routes_to_orthogonal`
- `test_legacy_progress_json_without_orthogonal_field_loads_ok`
- `test_mark_orthogonal_back_status_raises` — 'back' 은 sequence-only

### Risk register

- R-D1: 기존 progress.json 파일이 있는 run 들 (Spike I~XIII 이전 dogfood data) — `_ensure_orthogonal_field` 가 missing 일 때 빈 dict 채움. read-only 호환.
- R-D2: dispatches.jsonl 등 다른 곳에서 mark_stage('safety') 호출하던 코드가 있을까? grep 으로 사전 확인 — 없으면 OK, 있으면 auto-route 로 살아남음.

---

## Phase E — I4 SKILL.md doc drift sweep

**시간 예산**: ~30m | **subagent 1번** | **commit 단위**: 1 atomic

### 문제 진단

`dispatch_prompt(prompt_file)` 는 1-arg basename 시그니처. 일부 SKILL.md 가 stale
2-arg 또는 full path 를 보유:

| SKILL.md | 현재 wording | 정정 |
|---|---|---|
| `bundled/design-pack/SKILL.md:34` | `dispatch_prompt('design_draft_step1.md', run_id)` | `dispatch_prompt('design_draft_step1.md')` |
| `bundled/idea-shaper/SKILL.md:33` | `dispatch_prompt('bundled/idea-shaper/prompts/subagent/idea_shape_step1.md', run_id)` | `dispatch_prompt('idea_shape_step1.md')` |

빈손 사용자가 SKILL.md 시그니처 그대로 호출 시 `TypeError: takes 1 positional
argument but 2 were given` 또는 `ValueError: prompt file not in allowlist`.

### Fix design

1. 두 SKILL.md 정정 (atomic edit)
2. enforcement test 추가 — 모든 bundled/*/SKILL.md grep `dispatch_prompt(` →
   1-arg basename 패턴만 허용. 미래 drift 사전 차단.

### Acceptance criteria

| AC | Check | PASS condition |
|---|---|---|
| E.AC1 | design-pack SKILL.md 1-arg basename | grep `dispatch_prompt('design_draft_step1.md')` 1 hit, 2-arg 0 hit |
| E.AC2 | idea-shaper SKILL.md 1-arg basename | grep `dispatch_prompt('idea_shape_step1.md')` 1 hit, full-path 0 hit |
| E.AC3 | 모든 SKILL.md drift 검증 통과 | enforcement test PASS |
| E.AC4 | 회귀 테스트 0 | pytest 813 + 새 ~2 tests 모두 PASS |

### Test 추가

`tests/unit/test_skillmd_dispatch_prompt_signature.py` (NEW):
- `test_all_bundled_skillmd_dispatch_prompt_uses_1arg_basename` — regex 검증
- `test_no_skillmd_uses_full_path_in_dispatch_prompt` — 역검증

regex pattern:
```python
# OK: dispatch_prompt('foo.md') or dispatch_prompt("foo.md") — basename only
# OK: dispatch_prompt("<file>.md") — placeholder in prose context
# FAIL: dispatch_prompt('...', run_id) — extra arg
# FAIL: dispatch_prompt('bundled/.../foo.md') — full path
PROMPT_CALL_RE = re.compile(r"dispatch_prompt\(\s*['\"]([^'\"]+)['\"]\s*([,)])")
```

### Risk register

- R-E1: SKILL.md 가 prose context 에서 `dispatch_prompt(...)` 형식 placeholder 사용 (예: 설명 문구에 `dispatch_prompt('<file>.md')`) — regex 가 잘못 fail. test 에서 `<file>.md` 같은 placeholder 는 허용 (basename 패턴 검증 — `<` 또는 `{` 같은 placeholder marker 무시).

---

## Phase F — B-20 재검증 (V4 release gate 재시도)

**시간 예산**: ~2-3h | **운영**: 자동 probe (메인) + lived dogfood (사용자)

### 운영 분할

Spike XIII 패턴 동일:

| 트랙 | 범위 | 운영 |
|---|---|---|
| **B-20a** | 자동 sanity probe | 이 세션, ASSEMBLE_HOME tempdir, 12 AC. 본 spike Phase A~E 회귀 검증 + Spike XIII B-18 12 AC 재실행. |
| **B-20b** | lived dogfood (사용자 운전) | 별도 세션, 사용자가 새 task 1개 완주 + 단축 모드 명시 검증 |

### B-20a 12 AC

Spike XIII B-18 의 12 AC 그대로 + 본 spike fix 검증 추가:

| # | Check | PASS condition |
|---|---|---|
| F.AC1~12 | Spike XIII B-18 12 AC 그대로 | tempdir + 빈손 환경 + 12 inventory/menu/contract 검증 |
| F.AC13 | Phase A — wrap_with_preamble ASSEMBLE_HOME 주입 (set + unset 양쪽) | tempdir 안에서 검증 |
| F.AC14 | Phase B — 7 ★ SKILL.md 모두 mode-gate + Quick mode flow section 보유 | grep |
| F.AC15 | Phase C — plan-pack SKILL.md 에 § Recommendation policy + iter≤3 알고리즘 | grep |
| F.AC16 | Phase D — mark_orthogonal_stage import + 'safety'/'meta' 마킹 OK | tempdir 안 progress 호출 |
| F.AC17 | Phase E — SKILL.md doc drift 0 | enforcement test |
| F.AC18 | preamble v3 sha 보존 | canonical_preamble_sha256() 결과 == `8d22a29c...089a9` |

### B-20b lived dogfood 가이드

별도 세션, 사용자 운전. 가이드 doc `docs/dogfood/spike-xiv-b20b-capture-guide.md`
신규 작성 — Spike XIII B-19 capture-guide 기반 + 본 spike fix 검증 추가:

추가 capture point:
- **C20**: ★ stage 진입 시 mode-gate AskUserQuestion 발사 여부 (full / quick 메뉴 보임)
- **C21**: full mode 선택 시 spec 명시 N-step pipeline 모두 실행되는지 (dispatches.jsonl row N+ 개)
- **C22**: quick mode 선택 시 단일 dispatch + KEEPER_REPORT 에 mode=quick 카운트
- **C23**: ASSEMBLE_HOME 별도 세션 진입 후 모든 sub-agent dispatch 가 자동으로 home 경로 사용 (수동 prepend X)
- **C24**: plan-pack iter1 default = "yes" (iter≤3 + new>0 or unresolved>0 시)
- **C25**: orthogonal stage (safety/meta) 마킹 시 ValueError 없이 progress.json 에 orthogonal_stages.* 기록

### V4 release gate 통과 조건 (재시도)

**B-20a 모든 18 AC PASS + B-20b verdict ∈ {SHIP-READY, SHIP-WITH-MINOR-CARRYFORWARDS}** → V4 출시.

B-20b verdict ∈ {NEEDS-FIX, NEEDS-MAJOR-REWORK} → Spike XV+ cleanup spike(s) 후
재시도. 단, 본 spike 에서 fix 한 5 항목 (C1, C2/I2, I1, I3, I4) 의 *재발* 은 0
이어야 함 — 재발 시 fix design 자체 재검토.

### Risk register

- R-F1: B-20b 운영 비용 (사용자 90분+) — 단축 가능: 형이 task 1개를 짧은 scope (예: bash script 50줄) 로 잡으면 30~45분 가능.
- R-F2: 단축 모드 검증 시 사용자가 의도적으로 quick 골라야 함 — capture-guide 에 명시 ("의도적으로 1번 stage 는 quick, 2번 stage 는 full 골라보세요").

---

## Codex retro: SKIP

본 spike 는 *fix spike* — 새 contract 도입 X, paradigm enforcement 추가만. Codex
review 보다는 자체 dogfood B-20b 가 더 ROI 높음. 만약 B-20b 가 NEEDS-FIX 로 끝나면
그 시점에 Codex retro 호출.

---

## V5 backlog (본 spike scope 외)

- Spike XIII 누적 V5 모두 (M1/M2/M3 + M-XII4 + F-XII1~5 + F4 perf + roles.json + multi-language version bumping + multi-run concurrency safety + PII redaction + build sandboxing + Codex CLI / Gemini CLI 호환)
- 본 spike 신규 V5: PreToolUse hook 으로 Agent tool 호출 직전 mode-gate 발사 여부 시스템적 강제 (R-B1 미래 강화)
- 본 spike 신규 V5: quick mode quality gate 자동 차단 (KEEPER_REPORT 가 carryforward 5+ 일 때 자동 quick 비허용) — R-B2 미래 강화

---

## Source references

- Parent spec: `~/.claude/projects/-Users-yonghaekim-my-folder/memory/project_assemble_v4_spec.md`
- Spike XIII memory: `~/.claude/projects/-Users-yonghaekim-my-folder/memory/project_assemble_v4_spike_xiii.md`
- Spike XIII spec: `docs/specs/2026-05-06-v4-spike-xiii-design.md` (commit `4799781`)
- Spike XIII B-19 분석: `docs/dogfood/spike-xiii-b19.md` (commit `6b989a2`)
- pre-scan baseline: master `6b989a2` / pytest 813 passed / 17.16s
- harness preamble v3: `bundled/_shared/harness-preamble.md` (sha `8d22a29c…089a9`)
