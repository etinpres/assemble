"""F1 — shipper dispatch path: allowlist, preamble, RUN_DIR, audit invariants.

Mirrors verifier ★ Spike VIII A9 pattern (`test_verifier_dispatch_path.py`)
and extends it with shipper-specific coverage:
  - dispatches.jsonl row-count invariant (4 rows per iteration per spec § AC8)
  - preamble v3 sha canonical equality (Spike VIII A9 carryforward)
  - `_BUNDLED_DIR_TO_STAGE` cross-module consistency (Spike VIII A10)
  - `extract_wrote_paths` last-match contract (Spike VII F7)
  - `ORCHESTRATOR_ONLY_PROMPTS` sibling consistency

Tests:
  1. test_shipper_step_prompts_dispatchable — 4 prompts dispatch w/ preamble + body marker.
  2. test_shipper_run_dir_substitution — `{{RUN_DIR}}` substituted in Inputs section.
  3. test_shipper_iter_revisit_NOT_dispatchable — orchestrator-only, raises ValueError.
  4. test_non_allowlisted_shipper_prompt_raises — allowlist gate raises.
  5. test_shipper_preamble_sha_canonical — preamble file sha matches canonical sha.
  6. test_shipper_dispatch_chain_preamble_sha — wrapped prompt's preamble byte-equal.
  7. test_shipper_record_dispatch_writes_row — 1 dispatch → 1 row in dispatches.jsonl.
  8. test_shipper_record_dispatch_4_rows_per_iter — 4 dispatches → 4 audit rows w/ step names.
  9. test_bundled_dir_to_stage_consistency — harness + inventory both map shipper → ship.
  10. test_orchestrator_only_prompts_includes_shipper_iter_revisit — sibling consistency.
  11. test_shipper_in_bundles_tuple — shipper registered in `_BUNDLES`.
  12. test_extract_wrote_paths_last_match_for_shipper — last `WROTE:` line wins.
"""

import hashlib
import json
from pathlib import Path

import pytest

import server
import server.harness as h

# Canonical v3 preamble fragment — presence confirms preamble was prepended.
_PREAMBLE_MARKER = "read·grep 금지"

# V4 Spike VIII corrected canonical preamble v3 sha (locked in spec § Identity guards).
_CANONICAL_PREAMBLE_SHA = (
    "8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9"
)

# The 4 shipper subagent prompt files in allowlist order.
_SHIPPER_SUBAGENT_PROMPTS = [
    "shipper_preflight_step1.md",
    "shipper_version_step2.md",
    "shipper_build_step3.md",
    "shipper_tag_step4.md",
]

_TEST_RUN_ID = "test-rid"


def _read_jsonl(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_shipper_step_prompts_dispatchable():
    """All 4 shipper subagent prompts dispatch successfully.

    For each prompt:
      - dispatch_prompt returns a non-empty string
      - preamble marker is present (preamble prepended)
      - prompt body H1 step heading marker is present
    """
    body_markers = {
        "shipper_preflight_step1.md": "# shipper Step 1",
        "shipper_version_step2.md": "# shipper Step 2",
        "shipper_build_step3.md": "# shipper Step 3",
        "shipper_tag_step4.md": "# shipper Step 4",
    }

    for prompt_file in _SHIPPER_SUBAGENT_PROMPTS:
        raw = server.dispatch_prompt(prompt_file)
        assert isinstance(raw, str) and raw, (
            f"{prompt_file}: dispatch_prompt returned empty"
        )
        assert _PREAMBLE_MARKER in raw, (
            f"{prompt_file}: v3 preamble marker missing after dispatch"
        )
        assert body_markers[prompt_file] in raw, (
            f"{prompt_file}: body H1 heading marker missing"
        )


def test_shipper_run_dir_substitution():
    """For each of 4 prompts, substitute_inputs replaces literal {{RUN_DIR}}.

    Spike VII Track A: `RUN_ID` auto-derives `RUN_DIR` to the canonical run-dir
    absolute path. The substituted bytes must contain `runs/<run_id>` and the
    full assemble channels root.
    """
    for prompt_file in _SHIPPER_SUBAGENT_PROMPTS:
        raw = server.dispatch_prompt(prompt_file)
        substituted = h.substitute_inputs(raw, {"RUN_ID": _TEST_RUN_ID})

        # Inputs section: literal {{RUN_DIR}} token must be gone from the
        # Inputs block (everything before the next `## ` header).
        inputs_section = (
            substituted.split("## Inputs")[1].split("\n##")[0]
            if "## Inputs" in substituted else ""
        )
        assert "{{RUN_DIR}}" not in inputs_section, (
            f"{prompt_file}: {{{{RUN_DIR}}}} literal survived in Inputs section"
        )
        # The substituted absolute path must appear in the result.
        assert f"runs/{_TEST_RUN_ID}" in substituted, (
            f"{prompt_file}: expected 'runs/{_TEST_RUN_ID}' in substituted result"
        )
        assert ".claude/channels/assemble/runs/" + _TEST_RUN_ID in substituted, (
            f"{prompt_file}: expected absolute run path in substituted result"
        )


def test_shipper_iter_revisit_NOT_dispatchable():
    """shipper_iter_revisit.md is an orchestrator helper, not a subagent prompt.

    It must NOT appear in ALLOWED_PROMPT_FILES (main Claude reads it directly),
    and dispatch_prompt must raise when given this filename.
    """
    assert "shipper_iter_revisit.md" not in server.ALLOWED_PROMPT_FILES, (
        "shipper_iter_revisit.md must remain outside ALLOWED_PROMPT_FILES "
        "(orchestrator-only, never dispatched via harness)"
    )
    with pytest.raises(ValueError, match=r"not allowed"):
        server.dispatch_prompt("shipper_iter_revisit.md")


def test_non_allowlisted_shipper_prompt_raises():
    """A shipper-prefixed filename not in ALLOWED_PROMPT_FILES raises ValueError."""
    with pytest.raises(ValueError, match=r"not allowed"):
        server.dispatch_prompt("shipper_nonexistent_step99.md")


def test_shipper_preamble_sha_canonical():
    """The on-disk preamble file's sha256 must equal the canonical v3 sha.

    Locks the preamble byte-content per spec § Identity guards. Drift here
    invalidates every audit row and every dispatched prompt's identity claim.
    """
    preamble_path = (
        Path.home()
        / ".claude/skills/assemble/bundled/_shared/harness-preamble.md"
    )
    assert preamble_path.exists(), (
        f"preamble file missing at {preamble_path}"
    )
    raw_bytes = preamble_path.read_text(encoding="utf-8").rstrip() + "\n"
    actual_sha = hashlib.sha256(raw_bytes.encode("utf-8")).hexdigest()
    assert actual_sha == _CANONICAL_PREAMBLE_SHA, (
        f"preamble sha drift: got {actual_sha}, want {_CANONICAL_PREAMBLE_SHA}"
    )


def test_shipper_dispatch_chain_preamble_sha():
    """Dispatched prompt's preamble portion must byte-equal the canonical preamble.

    For each of 4 shipper subagent prompts, split the wrapped prompt on the
    [TASK] delimiter and confirm the preamble portion's sha256 matches the
    canonical preamble file sha (catches preamble drift at runtime).
    """
    canonical = h.canonical_preamble_sha256()
    assert canonical == _CANONICAL_PREAMBLE_SHA, (
        f"canonical_preamble_sha256() drift: got {canonical}"
    )
    for prompt_file in _SHIPPER_SUBAGENT_PROMPTS:
        wrapped = server.dispatch_prompt(prompt_file)
        preamble, body = h._split_preamble_body(wrapped)
        actual_sha = hashlib.sha256(preamble.encode("utf-8")).hexdigest()
        assert actual_sha == _CANONICAL_PREAMBLE_SHA, (
            f"{prompt_file}: dispatched preamble sha drift "
            f"(got {actual_sha}, want {_CANONICAL_PREAMBLE_SHA})"
        )
        # Body must contain the H1 step heading (sanity — preamble was split off,
        # not the body).
        assert "# shipper Step" in body, (
            f"{prompt_file}: body lost step heading after preamble split"
        )


def test_shipper_record_dispatch_writes_row(tmp_path, monkeypatch):
    """One dispatch → one row in dispatches.jsonl with expected fields.

    Uses ASSEMBLE_HOME redirection to isolate the test's run-dir from real
    user data. The preamble must be staged under the temp HOME so dispatch +
    record share byte-for-byte preamble identity.
    """
    real_home = Path.home()
    real_preamble = (
        real_home
        / ".claude/skills/assemble/bundled/_shared/harness-preamble.md"
    )
    # Stage real bundled tree under tmp HOME via symlink so dispatch_prompt
    # resolves prompts AND wrap_with_preamble loads the same canonical preamble.
    bundled_link = tmp_path / ".claude/skills/assemble"
    bundled_link.parent.mkdir(parents=True, exist_ok=True)
    bundled_link.symlink_to(real_home / ".claude/skills/assemble")

    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    # Reset preamble cache so the redirect takes effect in this test.
    h._CACHED_PREAMBLE.clear()

    prompt = server.dispatch_prompt("shipper_preflight_step1.md")
    out = h.record_dispatch(
        "rid-shipper-1",
        "step1.iter1.preflight",
        prompt,
        subagent_type="general-purpose",
        description="shipper Step 1 pre-flight",
        prompt_file="shipper_preflight_step1.md",
    )
    assert out.exists()
    rows = _read_jsonl(out)
    assert len(rows) == 1
    rec = rows[0]
    assert rec["step"] == "step1.iter1.preflight"
    assert rec["subagent_type"] == "general-purpose"
    assert rec["prompt_file"] == "shipper_preflight_step1.md"
    assert rec["status"] == "dispatched"
    # Preamble sha must equal canonical (audit anchor).
    assert rec["preamble_sha256"] == _CANONICAL_PREAMBLE_SHA


def test_shipper_record_dispatch_4_rows_per_iter(tmp_path, monkeypatch):
    """Four dispatches (Step 1-4) → 4 rows w/ expected step names per spec § AC8.

    Spec § Iteration audit invariant: every iteration produces exactly 4 rows
    in dispatches.jsonl with step names step{N}.iter1.<atom>.
    """
    real_home = Path.home()
    bundled_link = tmp_path / ".claude/skills/assemble"
    bundled_link.parent.mkdir(parents=True, exist_ok=True)
    bundled_link.symlink_to(real_home / ".claude/skills/assemble")

    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    h._CACHED_PREAMBLE.clear()

    expected_steps = [
        ("shipper_preflight_step1.md", "step1.iter1.preflight"),
        ("shipper_version_step2.md", "step2.iter1.version"),
        ("shipper_build_step3.md", "step3.iter1.build"),
        ("shipper_tag_step4.md", "step4.iter1.tag"),
    ]
    for prompt_file, step_name in expected_steps:
        prompt = server.dispatch_prompt(prompt_file)
        h.record_dispatch(
            "rid-shipper-iter1",
            step_name,
            prompt,
            subagent_type="general-purpose",
            description=f"shipper {step_name}",
            prompt_file=prompt_file,
        )

    runs_root = tmp_path / ".claude/channels/assemble/runs"
    out = runs_root / "rid-shipper-iter1" / "dispatches.jsonl"
    rows = _read_jsonl(out)
    assert len(rows) == 4, (
        f"expected 4 rows (one per step), got {len(rows)}"
    )
    actual_steps = [r["step"] for r in rows]
    assert actual_steps == [s for _, s in expected_steps], (
        f"step ordering / names drift: got {actual_steps}"
    )
    # All rows must share the canonical preamble sha (audit anchor).
    for r in rows:
        assert r["preamble_sha256"] == _CANONICAL_PREAMBLE_SHA


def test_bundled_dir_to_stage_consistency():
    """harness._BUNDLED_DIR_TO_STAGE and inventory._BUNDLED_DIR_TO_STAGE agree on shipper.

    Spike VIII A10 cross-reference invariant: the two copies serve different
    purposes (dispatch routing vs scan-time fallback) but MUST agree on
    every bundle's stage label. Drift produces silent classification bugs.
    """
    from server.harness import _BUNDLED_DIR_TO_STAGE as harness_map
    from server.inventory import _BUNDLED_DIR_TO_STAGE as inventory_map

    assert harness_map["shipper"] == "ship", (
        f"harness.shipper drift: {harness_map.get('shipper')!r}"
    )
    assert inventory_map["shipper"] == "ship", (
        f"inventory.shipper drift: {inventory_map.get('shipper')!r}"
    )
    assert harness_map["shipper"] == inventory_map["shipper"]


def test_orchestrator_only_prompts_includes_shipper_iter_revisit():
    """ORCHESTRATOR_ONLY_PROMPTS registers shipper_iter_revisit.md (sibling of verifier_iter_revisit).

    Spike VIII Pre-IX FIX-3 contract: orchestrator helpers live in this
    frozenset (not ALLOWED_PROMPT_FILES). Spike IX D3 wires the shipper
    sibling.
    """
    from server.harness import ORCHESTRATOR_ONLY_PROMPTS

    assert "shipper_iter_revisit.md" in ORCHESTRATOR_ONLY_PROMPTS, (
        "shipper_iter_revisit.md missing from ORCHESTRATOR_ONLY_PROMPTS"
    )
    # Sibling consistency — verifier_iter_revisit must still be present too.
    assert "verifier_iter_revisit.md" in ORCHESTRATOR_ONLY_PROMPTS


def test_shipper_in_bundles_tuple():
    """shipper is registered in `_BUNDLES` so `_resolve_prompt_path` finds it.

    Tested at unit level in Phase D, but pinned here at integration level so
    a future bundle-tuple regression surfaces in this dispatch-path file too.
    """
    from server.harness import _BUNDLES

    assert "shipper" in _BUNDLES, (
        f"shipper missing from _BUNDLES: {_BUNDLES!r}"
    )


def test_extract_wrote_paths_last_match_for_shipper():
    """`extract_wrote_paths` returns all WROTE: lines; last-match wins by convention.

    Spike VII F7 fix: multi-write steps (e.g. shipper Step 4 writes both
    tag_result.json AND SHIP_REPORT.md) emit one WROTE line per file in
    write order. Orchestrator takes `paths[-1]` for the canonical artifact.
    """
    stdout = (
        "random prose summarizing the shipper run\n"
        "WROTE: /tmp/preflight.json\n"
        "more diagnostic prose\n"
        "WROTE: /tmp/version_bump.json"
    )
    paths = h.extract_wrote_paths(stdout)
    assert paths == ["/tmp/preflight.json", "/tmp/version_bump.json"], (
        f"extract_wrote_paths order drift: got {paths}"
    )
    # Convention: last-match is the canonical artifact path.
    assert paths[-1] == "/tmp/version_bump.json"
