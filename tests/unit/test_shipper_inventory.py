import re
from pathlib import Path

import pytest

import server
from server.inventory import scan, _BUNDLED_DIR_TO_STAGE as INV_BUNDLED_DIR_TO_STAGE
from server.harness import (
    ALLOWED_PROMPT_FILES,
    ORCHESTRATOR_ONLY_PROMPTS,
    _BUNDLED_DIR_TO_STAGE as HARNESS_BUNDLED_DIR_TO_STAGE,
    _BUNDLES,
)

SKILL_MD = Path(__file__).resolve().parents[2] / "bundled" / "shipper" / "SKILL.md"


SHIPPER_SUBAGENT_PROMPTS = (
    "shipper_preflight_step1.md",
    "shipper_version_step2.md",
    "shipper_build_step3.md",
    "shipper_tag_step4.md",
)


def _touch(p: Path, body: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def test_shipper_skill_md_exists():
    assert SKILL_MD.is_file()


def test_shipper_frontmatter_declares_ship_stage_inline():
    text = SKILL_MD.read_text()
    # inline form per Spike VI B1 fix — block-list form would be parsed as empty
    assert re.search(r'stages:\s*\[\s*"ship"\s*\]', text), 'stages: ["ship"] inline form required'


def test_shipper_appears_in_inventory_after_d2_wiring(tmp_path, monkeypatch):
    """After Phase D2 lands _BUNDLED_DIR_TO_STAGE['shipper']='ship', inventory scan classifies shipper.

    Mirrors `test_verifier_in_inventory_scan` (Spike VIII A1): write a synthetic
    bundled shipper SKILL.md into a tmp_path-rooted ASSEMBLE_HOME and confirm
    the scan classifies it as `bundled=True` with stage='ship' in mappings.
    Real bundled SKILL.md declares `stages: ["ship"]` inline so the
    frontmatter-declared path is exercised; the harness/inventory map is the
    fallback for bundles that omit `stages:` and is also asserted in
    `test_shipper_resolves_to_ship_stage` below.
    """
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    body = (
        '---\n'
        'name: "shipper"\n'
        'description: "Ship-stage ★ bundle. Local pre-flight + version + build + tag pipeline."\n'
        'stages: ["ship"]\n'
        '---\n\n'
        '# shipper ★ — local ship-stage gate\n'
    )
    _touch(
        tmp_path / ".claude/skills/assemble/bundled/shipper/SKILL.md",
        body,
    )
    inv = scan(force=True)

    assert "shipper" in inv["skills"], "shipper not found in inventory scan"
    entry = inv["skills"]["shipper"]
    assert entry["bundled"] is True, "shipper should be marked bundled=True"
    stages_found = [m["stage"] for m in entry["mappings"]]
    assert "ship" in stages_found, (
        f"shipper mappings should contain stage='ship', got: {stages_found}"
    )


# -------------------------------------------------------------------------
# Phase D wiring tests — Spike IX
# -------------------------------------------------------------------------

def test_shipper_subagent_prompts_in_allowlist():
    """D1 — all 4 shipper subagent prompt filenames are present in ALLOWED_PROMPT_FILES."""
    for prompt in SHIPPER_SUBAGENT_PROMPTS:
        assert prompt in ALLOWED_PROMPT_FILES, (
            f"D1 wiring incomplete: {prompt} missing from ALLOWED_PROMPT_FILES"
        )


def test_shipper_iter_revisit_NOT_in_allowlist():
    """D1 negative — orchestrator helper must NOT appear in subagent allowlist.

    Mirrors the Spike VIII verifier_iter_revisit invariant: orchestrator
    helpers are loaded by main directly, not dispatched as subagents, so
    they must not pass through `dispatch_prompt`.
    """
    assert "shipper_iter_revisit.md" not in ALLOWED_PROMPT_FILES


def test_shipper_iter_revisit_in_orchestrator_only():
    """D3 — shipper_iter_revisit.md is registered as orchestrator-only."""
    assert "shipper_iter_revisit.md" in ORCHESTRATOR_ONLY_PROMPTS


def test_dispatch_prompt_raises_for_shipper_iter_revisit():
    """D5 — dispatch_prompt raises ValueError for orchestrator-only prompt.

    Positive enforcement: attempting to subagent-dispatch the orchestrator
    helper trips the ALLOWED_PROMPT_FILES allowlist check (shipper_iter_revisit.md
    deliberately NOT in the allowlist). Confirms the dual-list contract from
    `test_orchestrator_only_prompts.py::test_disjoint_with_allowed_prompt_files`.
    """
    with pytest.raises(ValueError, match=r"prompt_file.*not allowed"):
        server.dispatch_prompt("shipper_iter_revisit.md")


def test_dispatch_prompt_accepts_shipper_subagent_prompts():
    """D6 — dispatch_prompt resolves and wraps each of the 4 shipper subagent prompts.

    This validates the round trip: prompt file is in ALLOWED_PROMPT_FILES,
    `_resolve_prompt_path` finds it under bundled/shipper/prompts/subagent/,
    and `wrap_with_preamble` succeeds.
    """
    for prompt in SHIPPER_SUBAGENT_PROMPTS:
        out = server.dispatch_prompt(prompt)
        # Harness preamble must be prepended (Korean substring from the canonical preamble)
        assert "read·grep 금지" in out, (
            f"{prompt}: dispatch_prompt did not prepend harness preamble"
        )


def test_shipper_in_bundles_tuple():
    """D2 — `_BUNDLES` registers shipper for `_resolve_prompt_path` lookup order."""
    assert "shipper" in _BUNDLES


def test_harness_bundled_dir_to_stage_has_shipper():
    """D2 — harness `_BUNDLED_DIR_TO_STAGE` maps shipper -> ship."""
    assert HARNESS_BUNDLED_DIR_TO_STAGE.get("shipper") == "ship"


def test_inventory_bundled_dir_to_stage_has_shipper():
    """D2 — inventory `_BUNDLED_DIR_TO_STAGE` maps shipper -> ship.

    The two maps mirror each other (both module-level docstrings cite the
    Spike VIII A10 cross-reference convention). Both must agree.
    """
    assert INV_BUNDLED_DIR_TO_STAGE.get("shipper") == "ship"


def test_allowed_prompt_files_grew_by_exactly_four_for_shipper():
    """AC D.1 — ALLOWED_PROMPT_FILES contains exactly 4 full-mode shipper-prefixed
    entries (plus 1 quick-mode entry from Spike XIV Phase B).

    Guards against accidental over-broad addition (e.g. someone adding
    shipper_iter_revisit.md to the subagent allowlist by mistake).

    Spike XIV Phase B: `shipper_quick.md` was added as the paradigm-hybrid
    single-dispatch fallback. Excluded from the full-mode 4-file count because
    full-mode (4 step prompts) and quick-mode (1 fallback prompt) are distinct
    contracts.
    """
    shipper_full_mode = [
        p for p in ALLOWED_PROMPT_FILES
        if p.startswith("shipper_") and p != "shipper_quick.md"
    ]
    assert len(shipper_full_mode) == 4, (
        f"expected exactly 4 shipper_* full-mode entries in ALLOWED_PROMPT_FILES, "
        f"got {len(shipper_full_mode)}: {shipper_full_mode}"
    )
    assert set(shipper_full_mode) == set(SHIPPER_SUBAGENT_PROMPTS)
