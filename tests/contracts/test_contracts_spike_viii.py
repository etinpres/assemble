"""Spike VIII — verifier ★ contract entry presence + regression guard.

Four tests:
1. spike-viii-verifier-allowlist entry exists with exactly 4 files.
2. spike-viii-verifier-verdict-invariant entry exists; rule references
   exit_code == 0, skipped, and timed_out.
3. spike-viii-verifier-artifact-invariant entry exists; rule/phrase
   mentions all 7 VERIFY_REPORT.md section titles.
4. Regression guard — Spike VII entry count (1) is preserved.
"""
import json
from pathlib import Path

ASSEMBLE = Path.home() / ".claude/skills/assemble"
CONTRACTS_FILE = ASSEMBLE / "tests/contracts/contracts.json"

SPIKE_VII_ENTRY_COUNT = 1  # pre-A8a baseline from `git show`

# 7 canonical VERIFY_REPORT.md section titles (Spike VIII artifact invariant)
_VERIFY_REPORT_SECTIONS = [
    "Summary",
    "Completion command",
    "Execution result",
    "Stdout sample",
    "Stderr sample",
    "Verdict reasoning",
    "Recommendations",
]

# The 4 verifier subagent prompt files (Spike VIII allowlist)
_VERIFIER_FILES = [
    "verifier_extract_step1.md",
    "verifier_execute_step2.md",
    "verifier_classify_step3.md",
    "verifier_report_step4.md",
]


def _load_contracts() -> list[dict]:
    raw = json.loads(CONTRACTS_FILE.read_text())
    return raw["contracts"]


def _by_id(contracts: list[dict], entry_id: str) -> dict | None:
    for c in contracts:
        if c.get("id") == entry_id:
            return c
    return None


def test_spike_viii_verifier_allowlist_entry_present():
    """Entry spike-viii-verifier-allowlist exists; phrase references all 4 verifier prompts."""
    contracts = _load_contracts()
    entry = _by_id(contracts, "spike-viii-verifier-allowlist")
    assert entry is not None, (
        "spike-viii-verifier-allowlist not found in contracts.json; "
        f"existing ids: {[c['id'] for c in contracts]}"
    )
    phrase = entry.get("phrase", "")
    for filename in _VERIFIER_FILES:
        assert filename in phrase, (
            f"spike-viii-verifier-allowlist phrase missing file {filename!r}; "
            f"phrase: {phrase!r}"
        )
    # Exactly 4 file references
    found = [f for f in _VERIFIER_FILES if f in phrase]
    assert len(found) == 4, (
        f"expected exactly 4 verifier files in allowlist phrase, found {len(found)}: {found}"
    )


def test_spike_viii_verifier_verdict_invariant_present():
    """Entry spike-viii-verifier-verdict-invariant exists; phrase/rule references
    exit_code == 0, skipped, and timed_out."""
    contracts = _load_contracts()
    entry = _by_id(contracts, "spike-viii-verifier-verdict-invariant")
    assert entry is not None, (
        "spike-viii-verifier-verdict-invariant not found in contracts.json; "
        f"existing ids: {[c['id'] for c in contracts]}"
    )
    # In the existing schema the invariant is encoded in `phrase`
    phrase = entry.get("phrase", "") or entry.get("rule", "")
    assert "exit_code == 0" in phrase, (
        f"verdict invariant phrase missing 'exit_code == 0'; phrase: {phrase!r}"
    )
    assert "skipped" in phrase, (
        f"verdict invariant phrase missing 'skipped'; phrase: {phrase!r}"
    )
    assert "timed_out" in phrase, (
        f"verdict invariant phrase missing 'timed_out'; phrase: {phrase!r}"
    )


def test_spike_viii_verifier_artifact_invariant_present():
    """Entry spike-viii-verifier-artifact-invariant exists; phrase mentions all 7
    VERIFY_REPORT.md section titles."""
    contracts = _load_contracts()
    entry = _by_id(contracts, "spike-viii-verifier-artifact-invariant")
    assert entry is not None, (
        "spike-viii-verifier-artifact-invariant not found in contracts.json; "
        f"existing ids: {[c['id'] for c in contracts]}"
    )
    phrase = entry.get("phrase", "") or entry.get("rule", "")
    for section_title in _VERIFY_REPORT_SECTIONS:
        assert section_title in phrase, (
            f"artifact invariant phrase missing section title {section_title!r}; "
            f"phrase: {phrase!r}"
        )


def test_existing_contracts_unchanged():
    """Regression guard — Spike VII entry count (pre-A8a baseline) is preserved.

    A8a is APPEND-ONLY; existing spike-vii-* entries must not be removed.
    """
    contracts = _load_contracts()
    # Match exactly "spike-vii-*" (not "spike-viii-*") by requiring the 4th segment is "vii"
    spike_vii_entries = [
        c for c in contracts
        if c.get("id", "").startswith("spike-vii-")
        and not c.get("id", "").startswith("spike-viii-")
    ]
    assert len(spike_vii_entries) == SPIKE_VII_ENTRY_COUNT, (
        f"expected {SPIKE_VII_ENTRY_COUNT} spike-vii entries (pre-A8a baseline), "
        f"found {len(spike_vii_entries)}: {[c['id'] for c in spike_vii_entries]}"
    )
