# /assemble — Claude Code 용 도구 컨시어지

[🇺🇸 English](README.md)

[![tests](https://github.com/etinpres/assemble/actions/workflows/test.yml/badge.svg)](https://github.com/etinpres/assemble/actions/workflows/test.yml)
[![license](https://img.shields.io/github/license/etinpres/assemble)](LICENSE)
[![python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![version](https://img.shields.io/badge/version-4.0.0-brightgreen)](CHANGELOG.md)

설치된 스킬 / 플러그인 / 에이전트를 스캔해, 주어진 task 에 맞는 스테이지별 워크플로를 추천하고, 각 스테이지에서 어떤 도구를 실행할지 사용자가 직접 선택하게 해 주는 Claude Code 스킬입니다. **v4.0.0 부터 자급자족 번들 라이브러리가 포함됩니다** — 7개의 ★ 번들 + 3개의 표준 번들이 8개의 순차 스테이지 + 2개의 직교 스테이지(safety/meta) 를 모두 커버하므로, 이 스킬 하나만 설치된 빈 맥에서도 실제 프로젝트를 처음부터 끝까지 끌고 갈 수 있습니다.

## 주요 기능

1. 머신에 설치된 모든 `SKILL.md`(사용자 + 플러그인) 와 모든 에이전트 `.md` 를 **스캔** 합니다.
2. 각 항목을 프론트매터-키워드 휴리스틱으로 스테이지(`discover / plan / design / execute / debug / review / verify / ship` + 직교 `safety / meta`) 에 **분류** 합니다. 휴리스틱이 확신하지 못하는 항목은 `unclassified` 로 남겨두고, 필요할 때 인라인 LLM 패스로 채웁니다.
3. 사용자가 입력한 task 에 맞춰 **스테이지 시퀀스를 추천** 합니다.
4. **스테이지별 메뉴 루프** 를 실행 — 각 스테이지마다 적합한 도구들 + 메타 액션(`ask / skip / manual / back / done`) + 컨텍스트별 safety/meta 헬퍼가 표시됩니다. 하나 골라 실행하고 다음으로 넘어갑니다.
5. **실행 로그를 영속화** 하므로 `/assemble resume` 으로 멈춘 지점부터 이어갈 수 있습니다.
6. **번들 도구 라이브러리** — 7개의 ★ 번들 + 3개의 표준 번들이 plan / execute / debug / review / verify / ship + discover / design / safety / meta 를 모두 커버합니다. 각 ★ 번들은 다단계 서브에이전트 파이프라인(4-7 디스패치) 으로 구조화된 산출물(PRD / SCOPE / IMPL_REPORT / DEBUGGER_LOG / 등) 을 만들어냅니다.
7. **패러다임 하이브리드 (모드 게이트)** — 모든 ★ 번들 진입 시 `AskUserQuestion` 으로 `[full / quick]` 을 묻습니다. 기본은 full(스펙 그대로의 N-스텝 파이프라인). quick 모드는 시간이 빠듯할 때만 opt-in 으로 선택 가능한 단일 디스패치 폴백입니다.

## ★ 번들 + 표준 번들 (V4 라인업)

10개 번들이 모든 스테이지를 커버합니다. ★ 번들은 다단계 서브에이전트 파이프라인을 돌리고 구조화된 산출물을 emit 하며, 표준 번들은 단일 디스패치 헬퍼(또는 V4 #9 예외에 따라 main-IO 전용) 입니다.

| 스테이지 | 번들 | 등급 | 파이프라인 |
|---|---|---|---|
| discover | `idea-shaper` | 표준 | 1-스텝 인터뷰 → IDEA.md |
| plan | `plan-pack` | ★ | 4-doc 병렬 디스패치(PRD + ARCH + ADR + UI_GUIDE) + cross-doc 리뷰 + iteration |
| design | `design-pack` | 표준 | 1-스텝 → DESIGN.md + ANTI_PATTERNS.md |
| execute | `builder` | ★ | TDD red→green 파이프라인 (SCOPE → test_first → impl → verify → review → report) |
| debug | `debugger` | ★ | systematic-debugging (가설 → 재현 → bisect → 근본원인 → 수정) |
| review | `reviewer` | ★ | SCOPE-deviation + LLM trust boundary + SQL safety + secret leak |
| verify | `verifier` | ★ | extract → execute → classify → report (AC = bash, exit-code 로 판정) |
| ship | `shipper` | ★ | preflight → 버전 bump → 빌드 → 태그 → 릴리스 노트 (로컬 범위) |
| safety | `guardian` | 표준 | main-direct IO (V4 #9 예외) — 파괴적 명령 경고 + 디렉토리 freeze |
| meta | `keeper` | ★ | 실행 audit + 5-rule 추출기 + LLM 요약 + 원장(ledger) append + prune |

모드 게이트는 ★ 번들 진입마다 한 번씩 발동합니다. 스펙대로의 파이프라인이 필요하면 `full`, 단일 디스패치 폴백으로 시간을 아끼고 싶으면 `quick` 을 고르세요(산출물 스키마는 유지되지만 정밀도는 떨어집니다).

## 출처 / 영감

V4 의 harness 프리앰블은 안드레이 카파시가 정리한 코딩 AI 실패 패턴들에서 시작된 작업의 계보를 잇고 있습니다:

- [@karpathy on X](https://x.com/karpathy/status/2015883857489522876) — LLM 코딩 함정 — 과설계, 범위 확장(scope creep), 허위 맥락(fabricated context), 증상만 고치는 fix — 을 짚어낸 트윗.
- [`forrestchang/andrej-karpathy-skills`](https://github.com/forrestchang/andrej-karpathy-skills) — 이 관찰을 65줄짜리 `CLAUDE.md` 한 파일로 정리한 저장소로, GitHub 에서 가장 많이 별을 받은 Claude Code 스킬이 되었습니다 (115k+ ★).

V4 는 같은 4원칙("Think Before Coding / Simplicity First / Surgical Changes / Goal-driven Execution") 을 흡수했지만, 다른 메커니즘 — **서브에이전트 프롬프트에 프리앰블 직접 prepend** — 으로 작동시킵니다. 디스패치 가능한 모든 번들 프롬프트는 `bundled/_shared/harness-preamble.md` 로 wrapping 되어, 규칙이 *서브에이전트의 컨텍스트 안* 에 직접 박혀 들어갑니다 — 오케스트레이터의 컨텍스트에만 머무는 게 아니라. 이 wrapping 은 바이트 동일 wrapping (canonical sha `8d22a29c…`) 이며, `dispatches.jsonl` 로 감사되고, iteration 을 거쳐도 살아남습니다.

프리앰블은 카파시의 4원칙 위에 V4 전용 3원칙을 추가합니다:
- **Rule 5** — 사용자에게 표시되는 한국어 라벨·옵션 자연스럽게 (직역체·자작 한자어·한영 혼합 단어 금지)
- **Rule 6** — 사용자가 진술한 task scope 은 *seed* 이지 contract 가 아님; ★ 번들 풀번들이 contract
- **Rule 7** — 다른 스킬의 인프라 코드 (server/, hooks/, settings.json) read·grep 금지

V4 의 4원칙은 한국어로 다음과 같이 표기됩니다:
1. 불확실하면 추측 금지, 사용자 질문 우선 (Think Before Coding)
2. 과설계 금지, YAGNI (Simplicity First)
3. 요청 범위 밖 코드 임의 수정 금지 (Surgical Changes)
4. 버그 수정 시 재현 테스트 → 실패 확인 → 수정 → 재검증 루프 (Goal-driven Execution)

### 왜 prepend 인가, 단순한 규칙 명시가 아니라

프리앰블을 서브에이전트 프롬프트로 prepend 하는 메커니즘은, 단순히 `CLAUDE.md` 와 `SKILL.md` 에 규칙을 적어 두는 방식 대신 선택된 결정입니다. 이 결정은 본 스킬 저자와 Claude 사이의 실제 대화에서 시작됐습니다.

저자가 물었습니다 — *"솔직히, `CLAUDE.md` 와 `SKILL.md` 에 적힌 규칙 중에서 Claude 가 무시하는 비율이 얼마나 돼?"* Claude 의 답: **30~40%**. 저자의 후속 질문 — *"그럼 `.md` 파일에 규칙을 실컷 적어봐야 소용없는 거 아니야?"* Claude 가 동의했고, 역방향 제안을 내놓았습니다 — 규칙을 적어 두고 읽히길 기대하는 대신, **디스패치되는 모든 서브에이전트 프롬프트에 규칙을 직접 prepend 해서 다시 쓰지 않는 한 무시할 수 없게 만들자**. 이 대화가 V4 개발의 출발점입니다.

30~40% 라는 인정이 V4 의 prepend 메커니즘을 비협상 가능한 결정으로 만든 이유입니다. `CLAUDE.md` 의 규칙이 아무리 잘 적혀 있어도, 그중 1/3 가량은 실제 실행 시점에 닿지 않습니다. 번들 라이브러리는 그 간극을 메우기 위해, 규칙이 실제로 발화되는 자리 — 서브에이전트가 받는 프롬프트 안 — 에 직접 박는 방식으로 작동합니다. canonical 프리앰블 sha 와 바이트 단위로 대조 감사됩니다.

## 설치

```bash
git clone https://github.com/etinpres/assemble ~/.claude/skills/assemble
# Python 3 + PyYAML 필요 — `pip install pyyaml`. 다른 의존성 없음.
```

Claude Code 를 리로드한 뒤 실행:

```
/assemble build a small CLI for parsing CSV files
```

`/assemble` 의 진행 흐름:
1. 인벤토리 스캔 (머신에 있는 스킬 + 에이전트 + 플러그인).
2. 스테이지 시퀀스 추천 → 사용자가 `approve` / `edit` / `cancel`.
3. 스테이지별 메뉴 — 도구 선택. ★ 번들은 앞에 `★` 가 붙고 정렬도 먼저 됩니다.
4. ★ 번들이면 모드 게이트가 `full` (스펙 파이프라인) 또는 `quick` (단일 디스패치) 을 묻습니다.
5. 도구 실행. 서브에이전트 디스패치는 `dispatches.jsonl` 에 로그되고, 산출물은 `~/.claude/channels/assemble/runs/<run_id>/` 에 떨어집니다.
6. 스테이지 완료 마킹. 다음 스테이지 메뉴 표시. 시퀀스가 끝날 때까지 반복.

진행 도중 멈췄으면 `/assemble resume` 으로 재개합니다.

## 분류 동작 방식

휴리스틱 분류기는 보수적으로 동작합니다 — 확신할 수 없는 항목은 `unclassified` 로 남겨둡니다. 일괄 pre-warm 패스 대신, 인라인 LLM 분류기가 현재 `/assemble <task>` 와 가장 관련 있는 unclassified 항목 top-2 를 즉시 분류합니다. 결과는 `~/.claude/channels/assemble/inventory.json` 에 영속화되어 실행 간에 공유되므로, 각 task 는 자기와 관련된 분류 비용만 부담합니다 — 인벤토리 전체 비용을 매번 내지 않습니다.

`bin/classify-inventory` CLI 도 있어 일괄 실행 전용으로 쓸 수 있습니다; stdout 으로 JSONL 프롬프트 번들을 emit 하고, `--apply <file>` 로 JSONL 응답을 적용합니다. 대부분의 사용자는 이걸 직접 쓸 일이 없습니다.

## 언어 / 로케일

기본은 영어입니다. 한국어 로케일이 함께 번들됩니다:

```bash
export ASSEMBLE_LOCALE=ko   # 메뉴 라벨과 헬퍼 텍스트가 한국어로 전환
```

다른 로케일을 추가하려면 `config/i18n/en.json` → `config/i18n/<code>.json` 으로 복사한 뒤 문자열을 번역하고 `ASSEMBLE_LOCALE=<code>` 로 설정하면 됩니다. 누락된 키는 영어로 폴백되므로 부분 번역이라도 동작합니다.

## 요구사항

- Python 3 (stdlib + **PyYAML**, 예: `pip install pyyaml`)
- `Skill` + `AskUserQuestion` 도구를 갖춘 Claude Code.
- 선택: 테스트 스위트를 돌릴 거면 pytest

## 저장소 구조

```
SKILL.md                  # Claude 가 실행하는 절차 (실제 스킬)
server/                   # stdlib 만 사용하는 Python 모듈
  __init__.py             # Facade — 항상 `server` 에서 import
  inventory.py            # 스킬/에이전트 스캔, 휴리스틱 분류기
  classify.py             # LLM 분류 프롬프트 + 파서
  sequence.py             # 스테이지 시퀀스 프롬프트 + 파서
  menu.py                 # 스테이지 메뉴 빌더 (도구 + 메타 + 헬퍼)
  progress.py             # 실행 라이프사이클 (create / mark / resume / list)
  state_store.py          # 파일 락이 걸린 원자적 JSON read/write
  i18n.py                 # 로케일 로더 (env-var 기반)
  harness.py              # 서브에이전트 디스패치 + 프리앰블 wrapping + audit
  eject.py                # /assemble eject 서브커맨드 (V4 #9 IO 예외)
bundled/                  # V4 번들 라이브러리 — 자급자족 스킬 10개
  _shared/
    harness-preamble.md   # 7-rule 프리앰블 (카파시 4원칙 + V4 전용 3원칙)
  plan-pack/              # ★ — 13-스텝 PRD/ARCH/ADR/UI_GUIDE 파이프라인
  builder/                # ★ — TDD red→green 파이프라인
  debugger/               # ★ — systematic-debugging 파이프라인
  reviewer/               # ★ — SCOPE deviation + trust boundary 리뷰
  verifier/               # ★ — AC-as-bash exit-code 판정
  shipper/                # ★ — 로컬 빌드/태그/릴리스 파이프라인
  keeper/                 # ★ — 실행 audit + 학습 원장(ledger)
  idea-shaper/            # 표준 — 인터뷰 → IDEA.md
  design-pack/            # 표준 — DESIGN.md + ANTI_PATTERNS.md
  guardian/               # 표준 — main-IO safety (V4 #9 예외)
bin/
  classify-inventory      # 오프라인 일괄 분류 CLI
config/
  stages.json             # 스테이지 id 만 (표시 텍스트는 i18n/ 에 있음)
  stage_roles.json        # contextual_helpers 가 사용하는 역할 이름
  i18n/
    en.json               # 영어 (기본)
    ko.json               # 한국어
docs/                     # 아키텍처 + 실행 문서
tests/                    # pytest 케이스 833개 (단위 + e2e + contracts + dogfood)
```

## 테스트 실행

```bash
cd ~/.claude/skills/assemble
python3 -m pytest tests
```

기대 결과: `833 passed`, 20초 이내. (CI 매트릭스: 3.10 / 3.11 / 3.12 — `.github/workflows/test.yml` 참고.)

## 설계 노트

- **글로벌 스킬-이름 테이블 없음.** 이전 설계에는 알려진 스킬 목록을 박아놓은 `pre_mapping.json` 이 있었습니다. 설치되지도 않은 스킬을 미리 매핑할 수 없어서 폐기했습니다. 분류는 이제 각 스킬 자체의 `SKILL.md` 프론트매터를 읽습니다.
- **사용자 > 플러그인 우선순위.** 두 스킬이 같은 이름을 공유하면, 경로 우선순위 기반 first-wins dedupe 로 사용자 설치본이 이깁니다.
- **손상된 캐시는 격리될 뿐 조용히 파괴되지 않음.** 손상된 `inventory.json` 은 `inventory.json.bad-<ts>` 로 이름이 바뀌고 다시 빌드됩니다. 나중에 그 bad 파일을 직접 들여다볼 수 있습니다.
- **동시 writer 안전.** `scan()` 과 `apply_classification()` 은 `update_json_locked` 를 공유하므로, `/assemble` 실행과 백그라운드 `classify-inventory` 가 서로를 덮어쓰지 않습니다.
- **메뉴에 스킬 본문 없음.** `build_stage_options()` 는 `{label, kind, description(≤80), tool_path}` 만 반환합니다 — 본문은 실제로 `Skill` 이 도구를 invoke 할 때 lazy 하게 로드됩니다.
- **다른 플러그인과 잘 공존.** 설치된 플러그인(Vercel, gstack 등) 의 SessionStart 와 파일 패턴 hook 은 Claude Code 런타임 동작이므로 `/assemble` 스테이지 루프를 방해하지 않습니다. 오히려 그 플러그인의 스킬들이 스테이지로 분류되어 후보 도구가 됩니다 — 예를 들어 `vercel-cli` 는 `ship` 아래, `vercel-agent` 는 `review`/`debug` 아래에 노출됩니다.
- **canonical 프리앰블 sha v3 invariant.** 디스패치되는 모든 서브에이전트 프롬프트는 `wrap_with_preamble` 로 wrapping 되며, wrapping 된 프리앰블 부분은 항상 `8d22a29c…089a9` 로 해시됩니다 — `dispatches.jsonl` 에 레코드별로 audit 됩니다. ALLOW_LIST = {v1, v2, v3} 이므로 이전 실행도 여전히 그린으로 검증됩니다.
- **번들은 번들이지 nested 스킬이 아님.** 사용자의 `~/.claude/skills/builder/` 에 있는 `builder` 스킬과 `~/.claude/skills/assemble/bundled/builder/` 아래의 번들된 `builder` 는 공존합니다; 메뉴에는 둘 다 표시되고, 번들된 쪽에만 `★` 가 붙습니다.
- **패러다임 하이브리드는 opt-in 전용.** 사용자가 AskUserQuestion 모드 게이트에서 명시적으로 quick 을 고르지 않는 한 quick 모드는 절대 발동하지 않습니다; 오케스트레이터가 알아서 "시간 절약하자" 고 결정하는 일은 없습니다. (V4 #11 + 4원칙 #1 강제.)
- **`/assemble eject <bundle>` 은 번들을 사용자 스킬 트리(`~/.claude/skills/<name>/`) 로 복사** 하므로, 번들된 원본을 변형하지 않고 fork + 커스터마이징 가능합니다. 기본 흐름은 그대로 유지됩니다.

## 기여

- 코드 주석은 모두 영어로 작성하세요.
- 사용자에게 보이는 문자열은 `config/i18n/*.json` 에 두세요 — 절대 하드코딩 금지.
- `from server import ...` 만 사용 — 서브모듈을 직접 reach in 하지 마세요.
- PR 열기 전 `python3 -m pytest tests` 를 돌리세요.

## 라이선스

MIT.
