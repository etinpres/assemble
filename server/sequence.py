import json
import re

SEQUENTIAL_ORDER = ["discover","plan","design","execute","debug","review","verify","ship"]
ORDER_INDEX = {s: i for i, s in enumerate(SEQUENTIAL_ORDER)}

PROMPT_TEMPLATE = """\
User task: {task}

There are 8 sequential stages:
  discover -> plan -> design -> execute -> debug -> review -> verify -> ship

Pick *only the stages this task needs* and list them in order.
- Preserve the flow above (skipping is OK, reordering is not)
- `safety` and `meta` are orthogonal — do not include them in the sequence
- Trivial tasks may use just 1-2 stages

Respond with JSON only:
{{
  "sequence": ["<stage>", ...],
  "reasoning": "<one line — why these stages>"
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
