PROMPT_TEMPLATE = """\
다음 Claude Code 스킬을 분류해줘.

이름: {name}
설명: {description}
본문 발췌: {body_excerpt}

8 stages: discover, plan, design, execute, debug, review, verify, ship
2 orthogonal: safety, meta

stage 정의:
- discover: 아이디어 탐색·문제 정의
- plan: 아키텍처/spec 작성, plan 리뷰
- design: UI/시각 디자인, 디자인 시스템
- execute: 코드 구현, plan 실행, 병렬 작업
- debug: 버그 추적, 근본 원인 분석
- review: 코드/PR 리뷰, second opinion
- verify: 자체 검증, QA, 보안 감사, 성능 측정
- ship: 배포, 머지, 릴리스 문서, retro
- safety: 편집 범위 제한, 위험 명령 경고
- meta: 상태 저장, 스킬 관리, 외부 도구 연결

JSON으로만 답해. 도구가 여러 stage 걸치면 다 포함:
{{
  "mappings": [
    {{"stage": "<stage>", "role": "<snake_case_label>"}}
  ],
  "confidence": "high" | "medium" | "low",
  "reasoning": "<한 줄>"
}}
"""


def build_prompt(name: str, description: str | None, body_excerpt: str) -> str:
    return PROMPT_TEMPLATE.format(
        name=name,
        description=description or "(설명 없음)",
        body_excerpt=body_excerpt[:500] or "(본문 없음)",
    )
