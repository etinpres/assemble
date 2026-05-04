"""A9 — harness preamble v3 SHA invariant + every verifier dispatch prefix check.

2 tests:
  1. test_canonical_preamble_v3_sha_unchanged — sha256 of the canonical
     preamble file must match the known v3 hex digest.
  2. test_every_verifier_dispatch_starts_with_canonical_preamble — for each
     of the 4 verifier prompts, the dispatched body starts with the canonical
     preamble bytes (verified by sha256 of the first len(preamble) bytes).
"""

import hashlib
import importlib
from pathlib import Path

import pytest

import server.harness as h

# Canonical v3 sha256 (Spike II §3.1 F12 cutoff, 2026-05-01).
# Verified by: shasum -a 256 ~/.claude/skills/assemble/bundled/_shared/harness-preamble.md
_CANONICAL_V3_SHA = (
    "8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9"
)

_PREAMBLE_PATH = (
    Path(__file__).resolve().parents[2]
    / "bundled/_shared/harness-preamble.md"
)

_VERIFIER_SUBAGENT_PROMPTS = [
    "verifier_extract_step1.md",
    "verifier_execute_step2.md",
    "verifier_classify_step3.md",
    "verifier_report_step4.md",
]


def test_canonical_preamble_v3_sha_unchanged():
    """sha256 of the preamble file bytes must equal the pinned v3 constant.

    A change here means the preamble was modified — all prior dogfood
    dispatches will appear as mismatches in verify_dispatches audits unless
    the new sha is added to the ALLOW_LIST in server.harness.
    """
    assert _PREAMBLE_PATH.exists(), (
        f"harness-preamble.md not found at {_PREAMBLE_PATH}"
    )
    raw_bytes = _PREAMBLE_PATH.read_bytes()
    actual_sha = hashlib.sha256(raw_bytes).hexdigest()
    assert actual_sha == _CANONICAL_V3_SHA, (
        f"Preamble sha256 drifted!\n"
        f"  expected: {_CANONICAL_V3_SHA}\n"
        f"  got:      {actual_sha}\n"
        "If intentional, update _CANONICAL_V3_SHA and add the old sha to "
        "server.harness ALLOW_LIST to preserve dogfood back-compat."
    )


def test_every_verifier_dispatch_starts_with_canonical_preamble():
    """Every verifier subagent dispatch must be prefixed with the canonical preamble.

    For each of the 4 prompts: dispatch, then verify the first N bytes
    (where N = len(preamble)) hash to the canonical v3 sha.
    """
    # Use canonical_preamble_sha256() rather than the hardcoded constant here
    # so the test reflects whatever preamble is currently loaded — the sha
    # invariant test above already guards that this equals _CANONICAL_V3_SHA.
    importlib.reload(h)  # ensure fresh load (clears path cache from other tests)
    canonical_sha = h.canonical_preamble_sha256()
    assert canonical_sha is not None, (
        "canonical_preamble_sha256() returned None — preamble file missing"
    )

    # Reconstruct the preamble text as wrap_with_preamble would load it.
    preamble_text = _PREAMBLE_PATH.read_text(encoding="utf-8").rstrip() + "\n"
    preamble_bytes = preamble_text.encode("utf-8")

    import server
    for filename in _VERIFIER_SUBAGENT_PROMPTS:
        dispatched = server.dispatch_prompt(filename)
        dispatched_bytes = dispatched.encode("utf-8")

        assert len(dispatched_bytes) >= len(preamble_bytes), (
            f"{filename}: dispatched result shorter than preamble "
            f"({len(dispatched_bytes)} < {len(preamble_bytes)} bytes)"
        )

        prefix_bytes = dispatched_bytes[: len(preamble_bytes)]
        prefix_sha = hashlib.sha256(prefix_bytes).hexdigest()

        assert prefix_sha == canonical_sha, (
            f"{filename}: dispatch does not start with canonical v3 preamble.\n"
            f"  expected sha: {canonical_sha}\n"
            f"  prefix sha:   {prefix_sha}\n"
            f"  first 80 chars of dispatched: {dispatched[:80]!r}"
        )
