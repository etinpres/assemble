"""Phase B guard — server.dispatch_prompt enforces allowlist + load + wrap.

Post-B1 fix (option B): substitution removed from dispatch_prompt; the
caller (orchestrator) now owns placeholder substitution. See spec §1.2
(B2 option B) for rationale.
"""

import pytest
from pathlib import Path

import server
import server.harness as h


ASSEMBLE = Path.home() / ".claude/skills/assemble"


def test_allowed_prompt_files_matches_bundle_inventory():
    """ALLOWED_PROMPT_FILES tuple must equal the on-disk prompt inventory under
    bundled/*/prompts/{subagent,orchestrator}/*.md.

    This auto-derives the expected set from disk so adding a new bundle prompt
    only requires updating ALLOWED_PROMPT_FILES — no parallel hardcoded list to
    sync. Catches both directions of drift:
      - file on disk but missing from tuple → unguarded sub-agent dispatch path
      - tuple entry with no file → dead allowlist entry

    Explicit exclusions (pure orchestrator helpers NOT dispatched via harness):
      - verifier_iter_revisit.md: loaded by main Claude directly (not a subagent
        prompt); see bundled/verifier/SKILL.md §Sub-agent matrix.
    """
    # Pure orchestrator helpers that are on disk but intentionally NOT in
    # ALLOWED_PROMPT_FILES (main Claude reads them directly, never dispatched).
    ORCHESTRATOR_ONLY_EXCLUSIONS: frozenset[str] = frozenset({
        "verifier_iter_revisit.md",
    })

    bundle_root = ASSEMBLE / "bundled"
    on_disk: set[str] = set()
    for bundle_dir in bundle_root.iterdir():
        if not bundle_dir.is_dir() or bundle_dir.name.startswith("_"):
            continue  # skip _shared/, etc.
        for subdir in ("subagent", "orchestrator"):
            d = bundle_dir / "prompts" / subdir
            if d.is_dir():
                on_disk |= {
                    p.name for p in d.glob("*.md")
                    if p.name != ".gitkeep"
                    and p.name not in ORCHESTRATOR_ONLY_EXCLUSIONS
                }

    in_tuple = set(server.ALLOWED_PROMPT_FILES)

    only_disk = on_disk - in_tuple
    only_tuple = in_tuple - on_disk

    assert not only_disk, (
        f"prompt files on disk but missing from ALLOWED_PROMPT_FILES "
        f"(unguarded dispatch path): {sorted(only_disk)}"
    )
    assert not only_tuple, (
        f"ALLOWED_PROMPT_FILES entries with no on-disk file "
        f"(dead allowlist entry): {sorted(only_tuple)}"
    )


def test_dispatch_prompt_unknown_file_raises():
    with pytest.raises(ValueError, match=r"prompt_file.*not allowed"):
        server.dispatch_prompt("evil.md")


def test_dispatch_prompt_returns_wrapped_prompt_with_placeholders_intact():
    """option B: dispatch_prompt loads + wraps only. Substitution is the
    caller's responsibility — `{{KEY}}` tokens MUST survive intact so the
    caller can route them itself (orchestrator-only inputs vs. sub-agent's
    own .replace instructions). See spec §1.2 (B2 option B)."""
    out = server.dispatch_prompt("prd_step2.md")
    # Harness preamble must be prepended
    assert "read·grep 금지" in out
    # All declared placeholders must survive intact
    assert "{{RUN_ID}}" in out
    assert "{{TASK}}" in out
    assert "{{INTERVIEW_ANSWERS}}" in out
    # Body content from the on-disk prompt must be present
    assert "PRD body sub-agent" in out  # opening paragraph


def test_record_dispatch_strict_mode_rejects_unknown_prompt_file(
    tmp_path, monkeypatch
):
    """ASSEMBLE_DISPATCH_STRICT=1 turns soft-warn into ValueError."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    monkeypatch.setenv("ASSEMBLE_DISPATCH_STRICT", "1")
    with pytest.raises(ValueError, match=r"§CRITICAL"):
        h.record_dispatch(
            "rid1", "step.x", "wrapped prompt",
            subagent_type="general-purpose",
            prompt_file="evil.md",
        )


def test_record_dispatch_soft_warn_default(tmp_path, monkeypatch, capsys):
    """Default mode (no strict env) only warns to stderr, does not raise."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    monkeypatch.delenv("ASSEMBLE_DISPATCH_STRICT", raising=False)
    out_path = h.record_dispatch(
        "rid1", "step.x", "wrapped prompt",
        subagent_type="general-purpose",
        prompt_file="evil.md",
    )
    assert out_path.exists()
    captured = capsys.readouterr()
    assert "evil.md" in captured.err
    assert "ALLOWED_PROMPT_FILES" in captured.err
