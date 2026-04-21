PROMPT_TEMPLATE = """\
Classify the following Claude Code skill.

name: {name}
description: {description}
body excerpt: {body_excerpt}

8 sequential stages: discover, plan, design, execute, debug, review, verify, ship
2 orthogonal:        safety, meta

Stage definitions:
- discover: idea exploration, problem definition
- plan:     architecture / spec writing, plan review
- design:   UI / visual design, design systems
- execute:  code implementation, plan execution, parallel work
- debug:    bug tracking, root-cause analysis
- review:   code / PR review, second opinion
- verify:   self-check, QA, security audit, performance measurement
- ship:     deploy, merge, release docs, retro
- safety:   edit-scope limits, destructive-command warnings
- meta:     state persistence, skill discovery, external-tool bridges

Respond with JSON only. If the tool spans multiple stages, include them all:
{{
  "mappings": [
    {{"stage": "<stage>", "role": "<snake_case_label>"}}
  ],
  "confidence": "high" | "medium" | "low",
  "reasoning": "<one line>"
}}
"""


def build_prompt(name: str, description: str | None, body_excerpt: str) -> str:
    return PROMPT_TEMPLATE.format(
        name=name,
        description=description or "(no description)",
        body_excerpt=body_excerpt[:500] or "(no body)",
    )

import json
import re

VALID_STAGES = {"discover","plan","design","execute","debug","review","verify","ship","safety","meta"}
VALID_CONFIDENCE = {"high","medium","low"}

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_response(raw: str) -> dict:
    cleaned = _FENCE.sub("", raw.strip()).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"not valid JSON: {e}") from e

    mappings = data.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        raise ValueError("mappings must be a non-empty list")
    for m in mappings:
        if not isinstance(m, dict):
            raise ValueError("each mapping must be an object")
        if "stage" not in m or "role" not in m:
            raise ValueError("mapping missing stage or role")
        if m["stage"] not in VALID_STAGES:
            raise ValueError(f"invalid stage: {m['stage']}")

    confidence = data.get("confidence", "low")
    if confidence not in VALID_CONFIDENCE:
        confidence = "low"

    return {
        "mappings": mappings,
        "confidence": confidence,
        "reasoning": str(data.get("reasoning", "")).strip(),
    }
