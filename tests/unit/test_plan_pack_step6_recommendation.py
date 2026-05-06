"""Regression tests for Phase C — Step 6 Recommendation policy section.

V4 Spike XIV I1 fix: plan-pack/SKILL.md must document a deterministic
algorithm for picking the default-recommended `AskUserQuestion` option at
each Step 6 iteration boundary, and must explicitly forbid speculative
rationale strings (e.g. "dogfood 시간 한계", "시간 부족") in the
recommendation wording. See
`docs/specs/2026-05-06-v4-spike-xiv-design.md` § "Phase C".
"""
from pathlib import Path


SKILL = Path.home() / ".claude/skills/assemble/bundled/plan-pack/SKILL.md"


def _body() -> str:
    return SKILL.read_text()


def test_step6_skillmd_has_recommendation_policy_section():
    """The new `### Recommendation policy` heading must exist, and it must
    sit between `### Step 6 prompt selector` and
    `### Step 6 yes-path detail` so the orchestrator reads the policy
    immediately after picking a prompt and before entering the yes-path."""
    body = _body()
    assert "### Recommendation policy" in body, (
        "Phase C contract: plan-pack/SKILL.md must contain a "
        "`### Recommendation policy` subsection under `## Step 6`."
    )

    selector_idx = body.index("### Step 6 prompt selector")
    policy_idx = body.index("### Recommendation policy")
    yes_path_idx = body.index("### Step 6 yes-path detail")

    assert selector_idx < policy_idx < yes_path_idx, (
        "Recommendation policy must be ordered between `Step 6 prompt "
        "selector` and `Step 6 yes-path detail` (got: "
        f"selector={selector_idx}, policy={policy_idx}, "
        f"yes_path={yes_path_idx})."
    )


def test_step6_skillmd_no_dogfood_time_limit_phrase():
    """The Recommendation policy section must explicitly forbid using
    speculative rationale strings (e.g. "dogfood 시간 한계", "시간 부족")
    as the default-recommendation 사유. We assert the *forbidding wording*
    is present, not the absence of the phrases per se — the spec body
    quotes the forbidden phrases inside the prohibition itself."""
    body = _body()
    # The forbid-clause from the spec body, verbatim:
    assert "추측 사유 박지 말 것" in body, (
        "Phase C contract: Recommendation policy must explicitly forbid "
        "speculative rationale (e.g. 'dogfood 시간 한계', '시간 부족') "
        "as the default-recommendation 사유 — the wording "
        "'추측 사유 박지 말 것' must appear in SKILL.md."
    )

    # The forbid-clause must reside inside the Recommendation policy
    # section, not floating elsewhere in the doc.
    policy_idx = body.index("### Recommendation policy")
    forbid_idx = body.index("추측 사유 박지 말 것")
    # Find the next sibling heading after Recommendation policy.
    next_heading_idx = body.index("### Step 6 yes-path detail")
    assert policy_idx < forbid_idx < next_heading_idx, (
        "The forbidding wording must live inside the `### Recommendation "
        "policy` section."
    )


def test_step6_skillmd_documents_recommend_algorithm():
    """The Recommendation policy must document the actual algorithm:
    a `recommend_iter_continue` function with `iteration_count <= 3`
    threshold logic and `resolved` / `new` / `unresolved` counts as
    inputs, plus the missing/malformed default = `yes` fallback."""
    body = _body()

    # Function signature must be present (the spec body shows the def line).
    assert "def recommend_iter_continue" in body, (
        "Recommendation policy must include the `recommend_iter_continue` "
        "algorithm signature."
    )

    # Threshold check (the early-iteration branch).
    assert "iteration_count <= 3" in body, (
        "Algorithm must document the `iteration_count <= 3` early-iteration "
        "threshold (initial iterations almost always recommend `yes`)."
    )

    # All three count variables must be referenced as algorithm inputs.
    for var in ("resolved", "new", "unresolved"):
        assert var in body, (
            f"Recommendation policy must reference `{var}` count variable."
        )

    # Risk register R-C2 fallback: missing/malformed iteration_state.json
    # must default to `yes` to preserve the multi-iteration promise.
    assert "missing 또는 malformed" in body, (
        "Recommendation policy must document the missing/malformed "
        "`iteration_state.json` fallback (default = `yes`, conservative)."
    )
