from server.classify import build_prompt


def test_prompt_contains_skill_metadata():
    p = build_prompt(name="my-tool",
                     description="Use when X happens",
                     body_excerpt="step 1: do thing\nstep 2: more thing")
    assert "my-tool" in p
    assert "Use when X happens" in p
    assert "step 1: do thing" in p
    for s in ["discover","plan","design","execute","debug","review","verify","ship"]:
        assert s in p
    assert "safety" in p and "meta" in p
    assert "JSON" in p

import pytest
from server.classify import parse_response


def test_parse_well_formed():
    raw = '{"mappings":[{"stage":"plan","role":"x"}],"confidence":"high","reasoning":"ok"}'
    r = parse_response(raw)
    assert r["mappings"] == [{"stage": "plan", "role": "x"}]
    assert r["confidence"] == "high"


def test_parse_strips_markdown_fence():
    raw = "```json\n" \
          '{"mappings":[{"stage":"verify","role":"qa"}],"confidence":"low","reasoning":"unsure"}\n' \
          "```"
    r = parse_response(raw)
    assert r["mappings"][0]["stage"] == "verify"


def test_parse_rejects_unknown_stage():
    raw = '{"mappings":[{"stage":"deploy","role":"x"}],"confidence":"high","reasoning":""}'
    with pytest.raises(ValueError, match="invalid stage"):
        parse_response(raw)


def test_parse_rejects_missing_field():
    raw = '{"mappings":[{"stage":"plan"}],"confidence":"high","reasoning":""}'
    with pytest.raises(ValueError, match="role"):
        parse_response(raw)


def test_parse_clamps_confidence():
    raw = '{"mappings":[{"stage":"plan","role":"x"}],"confidence":"super","reasoning":""}'
    r = parse_response(raw)
    assert r["confidence"] == "low"  # unknown → low
