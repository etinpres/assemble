import json
import re

SEQUENTIAL_ORDER = ["discover","plan","design","execute","debug","review","verify","ship"]
ORDER_INDEX = {s: i for i, s in enumerate(SEQUENTIAL_ORDER)}

PROMPT_TEMPLATE = """\
사용자 작업: {task}

8개 sequential stage가 있어:
  discover → plan → design → execute → debug → review → verify → ship

이 작업에 *필요한 stage만* 골라서 순서대로 배열로 만들어줘.
- 순서는 위 흐름을 어기지 마 (skip은 OK, 순서 뒤집기 금지)
- safety / meta는 직교 카테고리라 sequence에 포함하지 마
- 단순한 작업이면 1~2개 stage만 골라도 돼

JSON으로만 답해:
{{
  "sequence": ["<stage>", ...],
  "reasoning": "<한 줄 — 왜 이 stage들을 골랐는지>"
}}
"""

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def build_prompt(task: str) -> str:
    return PROMPT_TEMPLATE.format(task=task)


def parse_response(raw: str) -> dict:
    cleaned = _FENCE.sub("", raw.strip()).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"not valid JSON: {e}") from e

    seq = data.get("sequence")
    if not isinstance(seq, list) or not seq:
        raise ValueError("sequence must be a non-empty list")
    last = -1
    for s in seq:
        if s not in ORDER_INDEX:
            if s in {"safety","meta"}:
                raise ValueError(f"sequential-only — {s} is orthogonal")
            raise ValueError(f"invalid stage: {s}")
        if ORDER_INDEX[s] <= last:
            raise ValueError(f"order violation at {s}")
        last = ORDER_INDEX[s]

    return {"sequence": seq, "reasoning": str(data.get("reasoning","")).strip()}
