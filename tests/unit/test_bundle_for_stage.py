"""bundle_for_stage helper — A1 carryforward FIX-2 (Spike VIII)."""

import pytest
from server.harness import bundle_for_stage, _BUNDLED_DIR_TO_STAGE


def test_bundle_for_stage_plan():
    assert bundle_for_stage("plan") == "plan-pack"


def test_bundle_for_stage_execute():
    assert bundle_for_stage("execute") == "builder"


def test_bundle_for_stage_review():
    assert bundle_for_stage("review") == "reviewer"


def test_bundle_for_stage_debug():
    assert bundle_for_stage("debug") == "debugger"


def test_bundle_for_stage_verify():
    assert bundle_for_stage("verify") == "verifier"


def test_bundle_for_stage_ship():
    # Spike IX Phase D2 — shipper ★ wired into _BUNDLED_DIR_TO_STAGE.
    assert bundle_for_stage("ship") == "shipper"


def test_bundle_for_stage_unknown_returns_none():
    assert bundle_for_stage("nonexistent") is None
    assert bundle_for_stage("") is None


def test_bundle_for_stage_case_sensitive():
    # Documented exact-match behavior. "Verify" (capitalized) should miss.
    assert bundle_for_stage("Verify") is None
    assert bundle_for_stage("PLAN") is None


def test_map_is_1to1_invariant():
    # If 2 bundles ever map to the same stage, bundle_for_stage's
    # "first match wins" docstring becomes load-bearing. Assert the
    # invariant holds today.
    stages = list(_BUNDLED_DIR_TO_STAGE.values())
    assert len(stages) == len(set(stages)), (
        f"_BUNDLED_DIR_TO_STAGE has duplicate stage values: {stages}"
    )
