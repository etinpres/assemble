"""Unit tests for `bundled/keeper/prompts/subagent/keeper_extract_step2.md`
(V4 Spike X, Task B3).

Grep-gate tests on the prompt body — these lock in the structural
contracts that other parts of the keeper bundle (D1 allowlist,
B3 extract_rules.py invocation, harness Bash-grant audit) rely on:

  * F5 grep gate (Spike VI inheritance) — `## Bash tool access GRANTED`
    heading must be present so the harness's allowlist audit recognizes
    the prompt as a Bash-grant prompt rather than a default-deny one.
  * Spike VII Track A — `{{RUN_DIR}}` token (NOT `runs/{{RUN_ID}}`) so
    auto-derivation works.
  * Step 2's job is to invoke ``extract_rules.py`` and forward its
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
    / "keeper_extract_step2.md"
)


@pytest.fixture(scope="module")
def prompt_body() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def test_prompt_file_exists():
    assert PROMPT_PATH.is_file(), (
        f"keeper_extract_step2.md prompt missing at {PROMPT_PATH}"
    )


def test_bash_grant_heading_present(prompt_body):
    """F5 grep gate (Spike VI inheritance): exact heading string must
    appear so the harness's Bash-grant audit recognizes the prompt.
    """
    assert re.search(r"^## Bash tool access GRANTED\s*$", prompt_body, re.MULTILINE), (
        "prompt must contain '## Bash tool access GRANTED' heading "
        "(F5 grep gate from Spike VI)"
    )


def test_invokes_extract_rules_script(prompt_body):
    """The whole point of Step 2 is to call extract_rules.py — the
    canned bash invocation must reference it by name.
    """
    assert "extract_rules.py" in prompt_body, (
        "prompt must reference extract_rules.py — that's the canned "
        "bash payload Step 2 invokes"
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
