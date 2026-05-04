"""Spike X C3 + C4 — keeper bundle stage routing wiring (universal-defense convention).

Mirrors `test_verifier_inventory_scan.py` from Spike VIII. Asserts that
`keeper` is registered with stage `meta` in BOTH `_BUNDLED_DIR_TO_STAGE`
maps (server.inventory and server.harness). The two maps serve different
purposes (scan-time fallback vs dispatch routing / contract introspection)
but MUST stay in sync — Spike VIII A1 carryforward FIX-2 codified this as
the universal-defense convention.
"""
from server.harness import _BUNDLED_DIR_TO_STAGE as HARNESS_MAP
from server.inventory import _BUNDLED_DIR_TO_STAGE as INVENTORY_MAP


def test_keeper_bundle_maps_to_meta_stage():
    """C3 — inventory `_BUNDLED_DIR_TO_STAGE` maps keeper -> meta."""
    assert INVENTORY_MAP["keeper"] == "meta", (
        f"inventory.keeper drift: {INVENTORY_MAP.get('keeper')!r}"
    )


def test_keeper_in_harness_bundled_stage_map():
    """C4 — harness `_BUNDLED_DIR_TO_STAGE` maps keeper -> meta."""
    assert HARNESS_MAP["keeper"] == "meta", (
        f"harness.keeper drift: {HARNESS_MAP.get('keeper')!r}"
    )


def test_keeper_stage_consistency_across_modules():
    """Universal-defense — both maps agree on keeper's stage label.

    Spike VIII A1 carryforward FIX-2 cross-reference invariant: the two
    copies serve different purposes (dispatch routing vs scan-time
    fallback) but MUST agree on every bundle's stage label. Drift
    produces silent classification bugs.
    """
    assert HARNESS_MAP["keeper"] == INVENTORY_MAP["keeper"], (
        "keeper stage label drift across modules: "
        f"harness={HARNESS_MAP.get('keeper')!r} vs "
        f"inventory={INVENTORY_MAP.get('keeper')!r}"
    )


def test_both_maps_have_identical_key_sets():
    """Universal-defense — entire bundle key-set must be identical between maps.

    Spike X C3+C4 strengthens the symmetry contract: not just keeper, but
    every bundled name must appear in both maps. Adding keeper to only
    one side is a regression we want to catch immediately.
    """
    assert set(HARNESS_MAP.keys()) == set(INVENTORY_MAP.keys()), (
        "_BUNDLED_DIR_TO_STAGE key-set drift between modules: "
        f"harness_only={set(HARNESS_MAP) - set(INVENTORY_MAP)} "
        f"inventory_only={set(INVENTORY_MAP) - set(HARNESS_MAP)}"
    )
