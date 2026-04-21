import pytest
from server.sequence import build_prompt, parse_response


def test_prompt_lists_all_stages():
    p = build_prompt(task="iOS 계산기 앱 만들기")
    for s in ["discover","plan","design","execute","debug","review","verify","ship"]:
        assert s in p
    assert "iOS 계산기" in p
    assert "JSON" in p


def test_parse_valid_subset():
    raw = '{"sequence":["plan","design","execute","review","ship"],"reasoning":"new app"}'
    r = parse_response(raw)
    assert r["sequence"] == ["plan","design","execute","review","ship"]


def test_parse_rejects_unknown_stage():
    raw = '{"sequence":["plan","launch"],"reasoning":""}'
    with pytest.raises(ValueError, match="invalid stage"):
        parse_response(raw)


def test_parse_rejects_orthogonal_in_sequence():
    raw = '{"sequence":["plan","safety","execute"],"reasoning":""}'
    with pytest.raises(ValueError, match="sequential"):
        parse_response(raw)


def test_parse_rejects_out_of_order():
    raw = '{"sequence":["execute","plan"],"reasoning":""}'
    with pytest.raises(ValueError, match="order"):
        parse_response(raw)


def test_parse_strips_fence():
    raw = "```json\n" '{"sequence":["execute","review"],"reasoning":""}' "\n```"
    assert parse_response(raw)["sequence"] == ["execute","review"]
