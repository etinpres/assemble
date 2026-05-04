"""Phase D2 — `keeper_iter_revisit.md` joins `ORCHESTRATOR_ONLY_PROMPTS`.

The keeper iter-revisit helper is loaded by main Claude directly (not
via subagent dispatch), so it MUST appear in `ORCHESTRATOR_ONLY_PROMPTS`
and MUST NOT appear in `ALLOWED_PROMPT_FILES`. Mirrors the verifier
and shipper iter-revisit precedents (Spike VIII A7 / Spike IX D2).
"""

from pathlib import Path

import server
from server.harness import ORCHESTRATOR_ONLY_PROMPTS


ASSEMBLE = Path.home() / ".claude/skills/assemble"


def test_keeper_iter_revisit_in_orchestrator_only():
    """`keeper_iter_revisit.md` MUST be in `ORCHESTRATOR_ONLY_PROMPTS`."""
    assert "keeper_iter_revisit.md" in ORCHESTRATOR_ONLY_PROMPTS


def test_keeper_iter_revisit_not_in_allowed_prompt_files():
    """Orchestrator-only helpers MUST NOT leak into the subagent allowlist —
    that would create an unguarded dispatch surface."""
    assert "keeper_iter_revisit.md" not in server.ALLOWED_PROMPT_FILES


def test_keeper_iter_revisit_resolvable_on_disk():
    """The orchestrator helper must exist at the expected path so
    main Claude can read it without falling back to dispatch routing."""
    target = (
        ASSEMBLE / "bundled" / "keeper" / "prompts" / "orchestrator"
        / "keeper_iter_revisit.md"
    )
    assert target.exists(), f"keeper_iter_revisit.md not found at {target}"
