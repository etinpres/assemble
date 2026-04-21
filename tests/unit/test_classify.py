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
