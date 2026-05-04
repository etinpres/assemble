"""Unit tests for `bundled/keeper/prompts/subagent/keeper_ledger_step4.md`
(V4 Spike X, Tasks B5+B7).

Grep-gate tests on the prompt body — these lock in the structural
contracts that other parts of the keeper bundle (D1 allowlist,
B5 ledger_update.py invocation, harness Bash-grant audit) rely on:

  * F5 grep gate (Spike VI inheritance) — `## Bash tool access GRANTED`
    heading must be present so the harness's allowlist audit recognizes
    the prompt as a Bash-grant prompt rather than a default-deny one.
  * Spike VII Track A — `{{RUN_DIR}}` token (NOT `runs/{{RUN_ID}}`) so
    auto-derivation works.
  * Step 4's job is to invoke ``ledger_update.py`` and forward its
    WROTE: line — the prompt body must reference the script by name.
"""

import re
from pathlib import Path

import pytest

PROMPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "bundled"
    / "keeper"
    / "prompts"
    / "subagent"
    / "keeper_ledger_step4.md"
)


@pytest.fixture(scope="module")
def prompt_body() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def test_prompt_file_exists():
    assert PROMPT_PATH.is_file(), (
        f"keeper_ledger_step4.md prompt missing at {PROMPT_PATH}"
    )


def test_bash_grant_heading_present(prompt_body):
    """F5 grep gate (Spike VI inheritance): exact heading string must
    appear so the harness's Bash-grant audit recognizes the prompt.
    """
    assert re.search(
        r"^## Bash tool access GRANTED\s*$", prompt_body, re.MULTILINE
    ), (
        "prompt must contain '## Bash tool access GRANTED' heading "
        "(F5 grep gate from Spike VI)"
    )


def test_invokes_ledger_update_script(prompt_body):
    """The whole point of Step 4 is to call ledger_update.py — the
    canned bash invocation must reference it by name.
    """
    assert "ledger_update.py" in prompt_body, (
        "prompt must reference ledger_update.py — that's the canned "
        "bash payload Step 4 invokes"
    )


def test_uses_run_dir_token(prompt_body):
    """Spike VII Track A: prompt MUST use {{RUN_DIR}} token, not the
    legacy `runs/{{RUN_ID}}` string. RUN_DIR is auto-derived by the
    harness — hard-coded `runs/` paths break custom run roots.
    """
    assert "{{RUN_DIR}}" in prompt_body, (
        "prompt must reference {{RUN_DIR}} token (Spike VII Track A)"
    )
    # Belt-and-suspenders: catch the legacy pattern explicitly.
    assert "runs/{{RUN_ID}}" not in prompt_body, (
        "prompt must NOT hard-code runs/{{RUN_ID}} — use {{RUN_DIR}} instead"
    )


def test_emits_single_wrote_line(prompt_body):
    """Spike VII F7: orchestrator parses stdout with `^WROTE: (.+)$`
    last-match. Prompt body must instruct the sub-agent to forward
    `WROTE: ` (the regex anchor — note the space + colon).
    """
    assert "WROTE: " in prompt_body, (
        "prompt must instruct sub-agent to forward `WROTE: <path>` on stdout"
    )


def test_documents_one_canned_invocation_only(prompt_body):
    """Defense in depth: the prompt body must enumerate the
    'ONE canned invocation only' scope guard (mirrors keeper_extract_step2).
    """
    # Match the standard wording used by Step 2's prompt — keeps the
    # bundle's Bash-grant prose consistent.
    assert "ONE canned invocation only" in prompt_body, (
        "prompt must document Bash scope as 'ONE canned invocation only' "
        "(mirrors keeper_extract_step2 — defense in depth)"
    )
