"""Verbatim-contract registry meta-test (Item D — test ↔ spec wording drift).

Reads `tests/contracts/contracts.json` and asserts that each registered
contract's `phrase` appears as a literal substring within the named
`section` of `spec_path`. This catches plan-time wording drift between
test grep literals and spec block prose — the failure mode that B-4
retro #4 surfaced (test required "design direction", spec had
"design-direction").

Each contract test runs as a parametrized case so a registry of N
contracts produces N test results, each citing its `id` on failure.
"""
import json
from pathlib import Path

import pytest


SKILL_ROOT = Path.home() / ".claude/skills/assemble"
CONTRACTS_FILE = SKILL_ROOT / "tests/contracts/contracts.json"


def _section(body: str, heading: str) -> str:
    """Return the body block from `heading` through the next sibling-or-shallower heading.

    Identical to the helper in `test_plan_pack_skill.py`; duplicated here
    so this meta-test stays standalone. (Promoting both to a shared
    `tests/_util.py` is queued for a future quality pass.)
    """
    start = body.index(heading)
    depth = len(heading) - len(heading.lstrip("#"))
    nl = body.find("\n", start)
    if nl == -1:
        return body[start:]
    cursor = nl + 1
    while cursor < len(body):
        next_nl = body.find("\n", cursor)
        line_end = next_nl if next_nl != -1 else len(body)
        line = body[cursor:line_end]
        if line.startswith("#"):
            line_depth = len(line) - len(line.lstrip("#"))
            if line_depth <= depth and not line.startswith(heading):
                return body[start:cursor]
        if next_nl == -1:
            break
        cursor = next_nl + 1
    return body[start:]


def _load_contracts() -> list[dict]:
    raw = json.loads(CONTRACTS_FILE.read_text())
    return raw["contracts"]


CONTRACTS = _load_contracts()


def test_contracts_registry_loads():
    """Sanity: registry file parses and is non-empty."""
    assert CONTRACTS_FILE.exists(), f"missing: {CONTRACTS_FILE}"
    assert len(CONTRACTS) >= 1, "contracts registry must contain at least one entry"


def test_contracts_have_required_fields():
    """Each registry entry must carry id, phrase, spec_path, section, tag."""
    required = {"id", "phrase", "spec_path", "section", "tag"}
    for c in CONTRACTS:
        missing = required - c.keys()
        assert not missing, f"contract {c.get('id', '<no-id>')} missing fields: {missing}"


@pytest.mark.parametrize(
    "contract",
    CONTRACTS,
    ids=[c["id"] for c in CONTRACTS],
)
def test_contract_phrase_present_in_spec_section(contract):
    """Each registered phrase must appear as a literal substring within its
    declared spec section. If this fails, either:

    1. The spec block was edited and the phrase no longer appears verbatim
       (drift introduced — fix the spec or update the contract entry).
    2. The contract entry was added without the corresponding spec
       prose landing first (spec is missing — write the spec first).
    3. The `section` heading anchor is wrong (typo in the contract entry).
    """
    spec_path = SKILL_ROOT / contract["spec_path"]
    assert spec_path.exists(), f"contract {contract['id']}: spec file not found at {spec_path}"
    body = spec_path.read_text()

    try:
        section = _section(body, contract["section"])
    except ValueError:
        pytest.fail(
            f"contract {contract['id']}: heading anchor "
            f"{contract['section']!r} not found in {contract['spec_path']}"
        )

    assert contract["phrase"] in section, (
        f"contract {contract['id']} ({contract['tag']}): "
        f"phrase {contract['phrase']!r} not found in section "
        f"{contract['section']!r} of {contract['spec_path']}. "
        "Either spec drifted from contract or contract entry is stale."
    )


def test_contract_ids_are_unique():
    """Registry entries must have unique ids (so parametrize IDs don't collide)."""
    ids = [c["id"] for c in CONTRACTS]
    assert len(ids) == len(set(ids)), (
        f"duplicate contract ids in registry: {sorted([i for i in ids if ids.count(i) > 1])}"
    )
