"""ORCHESTRATOR_ONLY_PROMPTS contract — Spike VIII FIX-3."""

from pathlib import Path

import pytest

from server.harness import (
    ALLOWED_PROMPT_FILES,
    ORCHESTRATOR_ONLY_PROMPTS,
)

ASSEMBLE_HOME = Path.home() / ".claude/skills/assemble"


def test_set_contains_verifier_iter_revisit():
    """A7's verifier_iter_revisit.md was the first orchestrator helper."""
    assert "verifier_iter_revisit.md" in ORCHESTRATOR_ONLY_PROMPTS


def test_disjoint_with_allowed_prompt_files():
    """A prompt cannot be BOTH a subagent dispatch target AND an orchestrator
    helper — the contract differentiates the two surfaces. Subagent prompts
    pass through dispatch_prompt (preamble + substitution + Bash grant);
    orchestrator helpers are read by main directly without those guarantees.
    """
    overlap = set(ALLOWED_PROMPT_FILES) & ORCHESTRATOR_ONLY_PROMPTS
    assert not overlap, (
        f"prompt files appear in BOTH allowlists: {overlap} — must be "
        f"either a subagent dispatch target OR an orchestrator helper, "
        f"not both"
    )


def test_every_entry_exists_under_orchestrator_dir():
    """Each registered orchestrator-only prompt must physically live under
    `bundled/<bundle>/prompts/orchestrator/<file>`. This catches typos and
    ensures the registry stays in sync with the filesystem.
    """
    found_count = 0
    for prompt_file in ORCHESTRATOR_ONLY_PROMPTS:
        matches = list(ASSEMBLE_HOME.glob(
            f"bundled/*/prompts/orchestrator/{prompt_file}"
        ))
        assert matches, (
            f"{prompt_file} registered in ORCHESTRATOR_ONLY_PROMPTS but "
            f"not found under any bundled/*/prompts/orchestrator/ dir"
        )
        found_count += 1
    assert found_count == len(ORCHESTRATOR_ONLY_PROMPTS)


def test_set_is_frozenset_immutable():
    """Frozenset is the right shape — runtime registration of orchestrator
    helpers is an anti-pattern (the set is consumed by static integrity
    tests). Forces additions to land via source code edit + commit.
    """
    assert isinstance(ORCHESTRATOR_ONLY_PROMPTS, frozenset)
