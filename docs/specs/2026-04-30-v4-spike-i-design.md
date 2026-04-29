---
name: V4 Spike I — plan-pack SKILL.md 재설계 (sub-agent path-only return + harness v2 + hook v1)
date: 2026-04-30
status: draft
ledger_items: [B-prime+K, L, J-5, J-6]
sequencing: post-tuning ledger Sequencing #2 — Spike I
---

# V4 Spike I — plan-pack SKILL.md 재설계

## 1. Context / Motivation

V4 Phase B-5 dogfood (run `20260429-214423-4c5d`, 22m 47s, master `e61ab1a`) 에서 distribution blocker가 한 번에 잡혔다. 이 spec은 그중 4개 ledger 항목 — **B-prime+K**, **L**, **J-5**, **J-6** — 을 단일 spike에서 묶어 처리한다. 다른 항목(A, J-1~J-4, C, D, E, F)은 Spike II/III/quality/hygiene으로 분리.

핵심 진단 (ledger Tier 0 §"Item B-prime + K"):
- 메인 Claude는 SKILL.md를 읽지 않거나, 읽고도 무시한다 (3회 dogfood 모두 동일 패턴 재현).
- 결과: 메인이 `Bash + python3 + heredoc + write_run_artifact()` 우회로 4개 doc(PRD/ARCH/ADR/UI_GUIDE) 본문 직접 write. PreToolUse hook v0(`Edit|Write|NotebookEdit` matcher)는 0번 fired.
- 텍스트 룰만으로는 30~40% 무시 (V4 spec memo §Harness 4원칙 — `harness_framework` 인사이트).

Spike I의 결론: SKILL.md 텍스트로 메인을 설득하는 layer는 본질적으로 약하다. 메인이 본문을 *받지 않게* 하고, 받았더라도 *write할 표면이 없게* 만드는 구조 변경 + Bash 우회 차단 hook의 이중 방어가 필요하다.

## 2. Decisions (브레인스토밍 결과)

| # | 결정 사항 | 선택 옵션 | 비고 |
|---|---|---|---|
| D1 | sub-agent에 write 권한 위임 방식 | **A. sub-agent 직접 호출** | sub-agent가 `write_run_artifact` 자체 호출. ledger 권장 방향. |
| D2 | J-6 라벨 fix 방향 | **A. 라벨을 워크플로에 맞춤** | 워크플로 변경 X. 라벨이 (1) emphasis 인터뷰 + (2) 4-doc 재작성 + (3) cross-doc 재검증 모두 명시. |
| D3 | Spike I 적용 폭 | **A. plan-pack 단독 + harness-preamble v2** | 다른 번들(builder/debugger 등)은 placeholder, 자연 수혜. server 코드 변경 0(추후 D4 일부 예외). |
| D4 | 메인의 SKILL.md 무시 lock 방식 | **E. D + hook v1 (Spike III 흡수)** | sub-agent path-only return + SKILL.md 압축 + Bash matcher 추가. 이중 방어. |

## 3. Architecture — sub-agent dispatch contract

### 3.1 기존 contract (B-prime origin)

```
[main] interview → sub-agent dispatch (prompt: write body)
[sub-agent] returns: <markdown body>
[main] receives body → split_sections / template fill / write_run_artifact
```

메인 손에 본문이 떨어지는 순간 우회 본능 발동. SKILL.md Step 5/8/11/13 코드 (split_sections, placeholder fill, write_run_artifact 호출)이 모두 메인 책임.

### 3.2 새 contract — sub-agent path-only return

```
[main] interview → sub-agent dispatch (prompt: build body, fill template, write to disk, return path)
[sub-agent] internal:
            build body
            → load template from bundled/plan-pack/templates/{DOC}.template
            → fill placeholders
            → write_run_artifact(rid, doc_name, filled)
            → print(f"WROTE: {path}")
[main] receives stdout → parse "^WROTE: (.+)$" → show path to user
```

메인은 본문을 보지도, write도 호출하지 않는다. 자유의지 영역 = `dispatch 1번 + path 1줄 출력` 뿐.

> **Note — `record_dispatch`는 contract 안**: 메인이 sub-agent dispatch 직후 호출하는 `server.harness.record_dispatch`는 preamble/body의 sha256 hash와 bytes 카운트만 기록한다. 본문 텍스트를 read·write 하지 않으므로 path-only return contract와 충돌하지 않는다. 새 `wrote_path` 필드(§8.1)는 sub-agent stdout `WROTE: <path>` 1줄 파싱 결과 — 메인이 본문이 아닌 path 문자열만 받음.

### 3.3 Sub-agent canonical save block (prompt 안에 인라인)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact

# Doc-specific build/fill code lives in each prompts/<step>.md file.
# Pattern shape (varies per doc — PRD/ARCH/ADR/UI):
#   1. (sub-agent writes body content for this doc)
#   2. load template at bundled/plan-pack/templates/{DOC}.template
#   3. substitute placeholders ({{TASK}}, {{STACK}}, {{DECISIONS_BLOCK}}, ...)
#   4. assign result to `filled`

path = write_run_artifact(rid, doc_name, filled)
print(f"WROTE: {path}")
```

각 `prompts/<step>.md` 파일이 doc-specific build+fill 코드를 인라인으로 포함 (§4.2 prompts/ 디렉토리). canonical save block은 그 doc-specific 코드 *직후*에 등장하는 마지막 4-5줄로 일관됨.

첫 줄의 `# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE` 주석은 hook v1의 magic marker로도 기능 (§6 참조).

### 3.4 Anti-fallback rule (SKILL.md 머리말 CRITICAL 블록)

```markdown
## CRITICAL — orchestrator-only enforcement

If a sub-agent dispatch fails (returns `ERROR: ...` or no `WROTE:` line),
the main Claude MUST NOT fall back to writing the artifact directly via
Bash/Edit/Write/python3. The only allowed recovery is:
1. Show error to user via terminal
2. AskUserQuestion: retry / abort
3. If retry: re-dispatch the same sub-agent with the failure context appended.

Direct artifact body writes by the main Claude are a contract violation
and are independently blocked by `hooks/guard_run_dir.sh` (see §6).
```

이 블록은 SKILL.md head에 두어 메인이 SKILL.md를 부분만 읽어도 보임. 명령 표면은 단 하나 — "직접 쓰지 마라."

### 3.5 Edge case — sub-agent write 실패

- sub-agent stdout으로 `ERROR: <reason>` 보고 → 메인이 그대로 사용자에게 표시 + AskUserQuestion("재시도 / 중단").
- 재시도: 동일 sub-agent에게 같은 prompt + "previous attempt failed: <reason>" 추가하여 dispatch.
- 메인이 직접 write로 폴백 금지 (§3.4 anti-fallback rule).

## 4. SKILL.md re-architecture

현재 ~735줄 → 새로 ~280줄 추정. 각 Step이 "dispatch + path 수령" 1-2단락으로 압축.

### 4.1 Step 별 새 책임

| Step | 현재 책임 | 새 책임 |
|---|---|---|
| 0 | run_dir 해석 | 그대로 |
| 1 | PRD 인터뷰 (8q × 2 calls) | 그대로 |
| 2+3 (병렬) | sub-agent 2개가 본문/AC bash 텍스트 반환 | sub-agent 2개가 본문 작성 + template fill + `PRD.md` write + path 반환 |
| 4 | second-opinion critique 텍스트 → 메인이 `## Review notes` append | second-opinion sub-agent가 `read_run_artifact("PRD.md") → critique → 새 내용으로 ## Review notes 섹션 추가한 full text → write_run_artifact(rid, "PRD.md", new_full)` (full overwrite) → path 반환 |
| **5** | **메인이 split_sections / template fill / write_run_artifact 직접 호출** | **삭제** |
| 7 | ARCH 인터뷰 | 그대로 |
| 8 | sub-agent 본문 → 메인이 split_sections + 7-placeholder fill + write | sub-agent가 fill+write → path. 메인은 split_sections 안 봄 |
| 10 | ADR 인터뷰 | 그대로 |
| 11 | sub-agent 본문 → 메인이 fill + write | sub-agent가 fill+write → path 반환 |
| 12 | UI 인터뷰 | 그대로 |
| 13 | sub-agent 본문 → 메인이 PRD 파싱(design_direction) + fill + write | sub-agent가 PRD 직접 read + design_direction 추출 + fill + write → path 반환 |
| 9 | cross-doc sub-agent critique → 메인이 ADR.md 읽고 append + 검증 | sub-agent가 4개 read + critique + ADR append write + iteration 헤딩 결정 → path 반환 |
| 6 | yes-path: emphasis 인터뷰 → 4-doc redraft → Step 9 재실행. 메인이 일부 path 정리 | yes-path: emphasis 인터뷰만 메인. 4-doc redraft + Step 9 모두 sub-agent path-only return. **라벨 변경 (J-6, §7)** |

### 4.2 Prompt 외부화 — `bundled/plan-pack/prompts/` 신설

각 dispatch의 prompt가 길어 SKILL.md에 다 박으면 압축 효과 ↓. 외부 markdown 파일로 빼고 SKILL.md는 메타데이터만.

```
bundled/plan-pack/
├── SKILL.md                   (압축됨 ~280줄)
├── templates/                 (기존 — 변경 없음)
│   ├── PRD.md.template
│   ├── ARCHITECTURE.md.template
│   ├── ADR.md.template
│   └── UI_GUIDE.md.template
└── prompts/                   (신설)
    ├── prd_step2.md           PRD body 작성 + fill + write 지시
    ├── prd_step3.md           AC bash 작성 + fill + write 지시
    ├── prd_step4.md           PRD read + critique + append + write
    ├── arch_step8.md
    ├── adr_step11.md
    ├── ui_step13.md
    ├── cross_doc_step9.md
    └── iter_emphasis.md       Step 6 yes-path 4-doc 재dispatch 안내
```

각 prompt 파일 안에 §3.3 canonical save block 인라인. 8개 파일 모두 magic marker 포함.

### 4.3 SKILL.md Step 텍스트 새 모양 예시

```markdown
### Step 8 — ARCH dispatch

Load `prompts/arch_step8.md`, substitute `{{TASK}}` and `{{INTERVIEW_ANSWERS}}`.
Wrap via `server.harness.wrap_with_preamble`. Dispatch to `general-purpose`
(single Agent call).

Sub-agent returns `WROTE: <path>` on stdout. Parse the path, show to user.
Proceed to Step 10 (ADR interview).

If sub-agent returns `ERROR: <reason>` or no `WROTE:` line, follow §CRITICAL
anti-fallback recovery — never fall back to direct write.
```

3-5줄. 메인이 무시할 외면 표면 거의 없음.

## 5. harness-preamble v2

`bundled/_shared/harness-preamble.md` 변경. 기존 4개 룰 유지 + 2개 추가.

### 5.1 v1 (변경 없음)

1. 불확실하면 추측 금지, 사용자 질문 우선
2. 과설계 금지, YAGNI
3. 요청 범위 밖 코드 임의 수정 금지
4. 버그 수정 시 재현 테스트 → 실패 확인 → 수정 → 재검증 루프

### 5.2 v2 추가 룰

**5. (J-5) 한국어 quality**

> 사용자에게 표시되는 한국어 라벨·옵션은 자연스러운 한국어로 정제. 직역체 (예: "좌히기"), 자작 한자어 (예: "키디텍터"), 한영 혼합 단어 (예: "PRD emp") 금지. 의미 모호하면 더 길어도 풀어서 표기. 사용자 메시지가 한국어면 응답·옵션도 한국어로.

**6. (L) Anti-downscale**

> 사용자가 진술한 task scope은 *seed*이지 contract가 아니다. ★ 번들 풀번들이 contract. 사용자 표현이 작게 들려도 doc 스킵·iteration 다운스케일·풀번들 일부 생략 금지. content density(밀도) 조정으로만 반응 — 짧은 task → 짧은 PRD body, 그러나 PRD/ARCH/ADR/UI_GUIDE 4개 doc 모두 작성. AskUserQuestion 옵션 만들 때도 다운스케일 옵션 생성 금지.

### 5.3 효과 / 한계 솔직 명시

- **Rule 5**: sub-agent에 prepend되어 sub-agent가 옵션 라벨을 만들 때 직접 작용. dogfood 데이터(PRD emp / 좌히기)가 sub-agent 압축 단계에서 발생 → 효과 직접.
- **Rule 6**: sub-agent 자율 영역에 효과. 그러나 옵션 라벨 생성 주체가 메인일 때(J-2/J-3/J-4 일부)는 텍스트 룰 의존이라 약함. 그래서 SKILL.md 머리말 CRITICAL 블록에도 anti-downscale rule 별도 박음. Spike II에서 메뉴 layer 강제 보강 예정.

### 5.4 sha256 영향

- `server.harness.canonical_preamble_sha256()` 값 변동 → `runs/<rid>/dispatches.jsonl`의 hash 자동 갱신 (새 run부터).
- 기존 dogfood data와의 호환은 §8.3 참조.

## 6. Hook v1 (Bash matcher 추가)

기존 v0 한계: matcher가 `Edit|Write|NotebookEdit` 만 → Bash + python3 + heredoc 우회 0 차단.

### 6.1 settings.json 변경

```json
{
  "matcher": "Edit|Write|NotebookEdit|Bash",
  "hooks": [{"command": "~/.claude/skills/assemble/hooks/guard_run_dir.sh"}]
}
```

또는 별도 entry로 Bash 전용 매처 분리. 1-script 분기 (tool name 별 처리)를 추천 — 단일 파일 관리.

### 6.2 guard_run_dir.sh Bash 분기 로직

`$CLAUDE_TOOL_NAME == "Bash"` 분기:

- **트리거**: `tool_input.command` 안에 `python3` / `python` / `sh -c` / `bash -c` 중 하나 + (`runs/[^/]+/[^/]+\.(md|json|txt)` 정규식 또는 리터럴 `write_run_artifact` 또는 리터럴 `runs_dir`) 패턴 발견. (정규식의 `[^/]+`가 `<rid>`와 파일명 자리; 정확한 grep 패턴은 plan 단계에서 hook 스크립트 작성 시 확정.)
- **통과 조건**: command 안에 magic marker `ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE` 발견 시.
- **차단**: 위 통과 조건 미충족 시 `exit 2` + stderr 메시지.

### 6.3 차단 메시지 (한국어, rule 5 적용)

```
[assemble guard] ❌ 메인 Claude의 runs/ 경로 직접 write 차단됨.
경로 일부: <command 발췌>
이유: Spike I 후 plan-pack은 sub-agent가 자체 write 책임 — 메인은 dispatch + path 수령만.
복구: sub-agent dispatch로 재시도하세요. (canonical save block에 magic marker 포함됨)
```

### 6.4 hook 단위 테스트 (`tests/test_guard_bash_matcher.py`)

| 케이스 | 입력 command | 기대 |
|---|---|---|
| A | `bash -c "python3 -c 'from server import write_run_artifact; ...'"` (marker 없음) | exit 2 + stderr 차단 메시지 |
| B | A와 동일 + `# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE` 포함 | exit 0 통과 |
| C | `ls /tmp` (무관 명령) | exit 0 통과 |
| D | `python3 -c "print(1)"` (runs/ 미포함) | exit 0 통과 |

### 6.5 한계 솔직 명시

- 메인이 마커를 의도적으로 따라치면 우회 가능 (낮은 위험, B-5에서 본 적 없는 패턴).
- 다른 번들이 향후 sub-agent-write 패턴 채택할 때 동일 marker 컨벤션 필요 — V4 spec memo + Spike II 메모.
- 모든 Bash 호출에 1번 grep 통과 → 성능 영향 미미.

## 7. J-6 라벨 변경 (Step 6 yes-path 정합성)

### 7.1 현재 라벨 vs 실제 액션 시퀀스

현재 (SKILL.md line 593-608):
```
> "All four docs saved — PRD.md, ARCHITECTURE.md, ADR.md, UI_GUIDE.md. Run one iteration?"
> options: ["yes — refine all four", "no — done"]
```

실제 yes-path:
1. follow-up `AskUserQuestion` — 4개 emphasis 인터뷰 (PRD/ARCH/ADR/UI 의도)
2. 4-doc parallel sub-agent dispatch (path-only return)
3. Step 9 cross-doc review (sub-agent path-only return)
4. (B-5 multi-iter 진입) — 다시 emphasis 인터뷰 ...

라벨 "refine all four"는 (2)만 약속 → (1)+(3)+(4)와 mismatch.

### 7.2 새 라벨

**진입 (`iteration_count == 0` 직후)**
```
> "네 문서 작성 완료 — PRD.md, ARCHITECTURE.md, ADR.md, UI_GUIDE.md. 한 차례 반복 진행할까?"
> options: ["yes — 강조점 인터뷰 + 4-doc 재작성 + cross-doc 재검증", "no — 종료"]
```

**multi-iter 진입 (`iteration_count ≥ 1`)** — 현재 SKILL.md line 707-712 "Continue iterating?"도 동일 fix:
```
> "반복을 계속할까?"
> options: ["yes — 강조점 인터뷰 + 4-doc 재작성 + cross-doc 재검증 한 라운드 더", "no — 여기서 종료"]
```

### 7.3 Spike I 한계 명시 (J-4 분리)

> Spike I는 라벨↔워크플로 정합성만 다룸. J-4 dynamic Recommended (CRITICAL unresolved 시 yes Recommended) 는 Spike II에서 메뉴 layer와 함께 처리. 새 라벨에는 Recommended 표기 없음 (중립 fallback).

### 7.4 영향 범위

- SKILL.md Step 6 entry prompt 라벨 1군데
- SKILL.md Step 6 multi-iter `User exit override` 라벨 1군데
- 라벨 grep 테스트 있으면 갱신

## 8. Migration / Tests

### 8.1 변경 파일 인벤토리

| 파일 | 변경 종류 | 비고 |
|---|---|---|
| `bundled/plan-pack/SKILL.md` | 거의 전면 재작성 (~735 → ~280줄) | Step 5 삭제, 8/11/13 압축, 6 라벨, head CRITICAL block |
| `bundled/plan-pack/prompts/*.md` | 8개 신규 파일 | prd_step2/3/4, arch_step8, adr_step11, ui_step13, cross_doc_step9, iter_emphasis |
| `bundled/_shared/harness-preamble.md` | v2 (rules 5/6 추가) | sha256 변동 |
| `hooks/guard_run_dir.sh` | Bash matcher 분기 추가 | tool_name 별 처리 |
| `~/.claude/settings.json` | matcher 확장 (Bash 추가) | hook entry 1개 |
| `server/harness.py` | `record_dispatch` schema에 `wrote_path: str \| null` 옵셔널 필드 추가 | 기존 hash 유지 |

server/run_dir.py / server/menu.py / server/inventory.py / server/sequence.py 등 코어는 변경 없음 (D3 정합).

### 8.2 깨지는 테스트 카테고리

**카테고리 1 — SKILL.md text grep 테스트**
- 메인-write 패턴(`write_run_artifact`, `split_sections`) grep을 sub-agent prompt 파일 grep으로 전환
- 일부 테스트는 prompts/ 파일 read해서 검증 (`prompts/arch_step8.md`에 `WROTE:` 출력 컨벤션)
- window-slice 패턴(`body[:2000]`)은 Item C 영역. 새 SKILL.md 길이가 짧아 자연 통과 가능성. 깨지면 `_section()` helper 신규 사용 (Item C 일부 흡수).

**카테고리 2 — preamble sha256 hard-coded 테스트**
- `canonical_preamble_sha256()` hard-code한 테스트 식별 → 갱신
- B-1~B-5 dogfood `runs/<rid>/dispatches.jsonl` 비교 테스트 → §8.3 호환

**카테고리 3 — Hook 신규 테스트** (4 케이스, §6.4)

**카테고리 4 — 새 contract 테스트**
- `tests/test_plan_pack_subagent_path_return.py` — sub-agent stdout `WROTE: <path>` 파싱 검증
- `tests/test_plan_pack_anti_fallback.py` — sub-agent dispatch 실패 시 메인이 직접 write로 폴백 안 함 (SKILL.md 텍스트 grep)

### 8.3 B-5 이전 데이터 호환

- `runs/20260429-214423-4c5d/` 등 기존 dogfood data는 v1 preamble sha256으로 기록.
- `verify_dispatches()` 함수가 v1/v2 sha256 모두 받도록 ALLOW LIST 짧은 코드 추가 (또는 cutoff 날짜 코멘트 처리).
- `docs/research/` 한 줄 메모로 마이그레이션 시점 기록.

### 8.4 마이그레이션 순서 (plan에 들어갈 단계 — 순서 보장)

1. harness-preamble.md v2 작성 + sha256 갱신 → 깨진 테스트 1차 식별 (preamble hash)
2. prompts/ 디렉토리 신설 + 8개 markdown 파일 작성 (canonical save block 포함, magic marker 포함)
3. SKILL.md 새로 작성 (압축 + CRITICAL block + Step 6 라벨)
4. 깨진 SKILL.md grep 테스트 갱신 (카테고리 1)
5. server/harness.py — `record_dispatch` schema에 `wrote_path` 옵셔널 필드 추가 + verify_dispatches v1/v2 ALLOW LIST
6. guard_run_dir.sh Bash matcher 추가 + settings.json 갱신
7. 새 테스트 작성 (카테고리 3, 4)
8. 전체 테스트 통과 확인 (목표: 67/67 → 새 수)
9. CHANGELOG `[Unreleased] V4 Spike I` 항목
10. dogfood 준비 — Spike II/III 미적용 환경에서 sub-agent path-only return 단독 검증

## 9. Acceptance criteria (B-6 dogfood, post-Spike I)

1. **0 메인 직접-write**: `runs/<rid>/dispatches.jsonl`에 메인 trace 없음. 모든 doc write의 `wrote_path` 필드는 sub-agent dispatch trace에 기록.
2. **0 hook block (정상 경로)**: sub-agent canonical block 통과. 메인 우회 시도는 0건이거나 차단.
3. **새 라벨 워크플로 정합**: Step 6 entry 라벨 = "강조점 인터뷰 + 4-doc 재작성 + cross-doc 재검증" + 실제 액션 시퀀스 1:1 일치.
4. **한국어 quality**: sub-agent가 만드는 옵션 라벨에 직역체/자작 한자어/한영혼합 0건.
5. **Anti-downscale**: dogfood 트레이스에 doc 스킵·iteration 다운스케일 0건 (Step 6 yes-path 진입 + emphasis 인터뷰 → 4-doc redraft 정상 진행).

## 10. Out of scope (Spike I이 다루지 *않는* 항목)

- **J-1/J-2/J-3/J-4** (메뉴 layer, dynamic Recommended) → Spike II
- **Item A** (multi-iter stop condition algorithm) → Spike II
- **Item C/D** (테스트 패턴 / 스펙 드리프트) → 후속 quality pass
- **Item E/F** (instruction ambiguity / line-anchored regex) → hygiene pass
- **다른 ★ 후보 번들** (builder/debugger/reviewer) → 별도 spike

## 11. Open questions

1. `general-purpose` sub-agent에 Bash 도구가 자동 부여되는지 구현 시 1차 확인 (Plan 단계 first task).
2. `from server import write_run_artifact` import path가 sub-agent 환경에서 작동하는지 1차 확인 — `sys.path.insert`로 명시했지만 실제 검증 필요.
3. `wrap_with_preamble`이 magic marker를 sub-agent prompt에 그대로 전달하는지 (preamble 자체는 marker 미포함 — sub-agent prompt 본문 안에만 marker. wrap이 byte-identical 보존하면 OK).
4. settings.json matcher 확장 시 다른 hook entry와 충돌 여부 — `~/.claude/settings.json`에 다른 PreToolUse 항목이 있으면 우선순위/순서 점검.

## 12. Sources

- Ledger: `~/.claude/projects/-Users-yonghaekim-my-folder/memory/project_assemble_v4_phase_b_posttuning.md`
  - Tier 0 §"Item B-prime + K"
  - Tier 0 §"Item J — Menu / UX identity erosion" (J-5, J-6 sub-findings)
  - Tier 0 §"Item L — Main LLM's task-scope downranking instinct"
  - §"Sequencing recommendation (revised post-B-5)" Spike I
- V4 spec memo: `~/.claude/projects/-Users-yonghaekim-my-folder/memory/project_assemble_v4_spec.md`
  - 결정 #5/#7/#9/#11/#12 (★ 보증, 오케스트레이터-only, 병렬 dispatch)
  - § "Harness 4원칙 흡수" (text-rule limit + sub-agent prompt prepend)
- 현 SKILL.md: `~/.claude/skills/assemble/bundled/plan-pack/SKILL.md` (Phase B-4 master `e61ab1a`)
- B-5 live dogfood run: `runs/20260429-214423-4c5d/` (22m 47s, user-terminated at iter1)
