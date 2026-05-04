"""Unit tests for `bundled/keeper/prompts/subagent/keeper_summarize_step3.md`
(V4 Spike X, Task B4).

Grep-gate tests on the prompt body — these lock in the structural
contracts that other parts of the keeper bundle (D1 allowlist,
B5 ledger_update, harness Bash-grant audit) rely on:

  * Step 3 is NO-Bash (verified by absence of `## Bash tool access GRANTED`
    heading — F5 grep gate convention from Spike VI).
  * Spike VII Track A — `{{RUN_DIR}}` token (NOT `runs/{{RUN_ID}}`) so
    auto-derivation works.
  * V4 deterministic-template implementation — fallback templates for
    R1/R2/R3 in both English and Korean must be present.
  * Evidence preservation — body must instruct sub-agent NOT to modify
    `evidence` / `evidence_hash` (ledger dedup desync risk).
  * Output filename `learnings_to_emit.json` is canonical for B5
    ledger_update consumer.
  * Spike VII F7 — single trailing `WROTE:` line on stdout.
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
    / "keeper_summarize_step3.md"
)


@pytest.fixture(scope="module")
def prompt_body() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def test_prompt_file_exists():
    assert PROMPT_PATH.is_file(), (
        f"keeper_summarize_step3.md prompt missing at {PROMPT_PATH}"
    )


def test_no_bash_grant_heading(prompt_body):
    """Step 3 is pure Read/Write — NO Bash. The F5 grep-gate convention
    (Spike VI inheritance) means absence of `## Bash tool access GRANTED`
    is the signal to the harness's allowlist audit that this prompt
    runs default-deny on Bash.
    """
    assert not re.search(
        r"^## Bash tool access GRANTED\s*$", prompt_body, re.MULTILINE
    ), (
        "Step 3 must NOT contain '## Bash tool access GRANTED' heading — "
        "Step 3 is pure Read/Write (no Bash grant)"
    )


def test_save_block_uses_run_dir_token(prompt_body):
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


def test_writes_learnings_to_emit_json(prompt_body):
    """The prompt's deliverable filename is canonical — keeper Step 4
    (B5 ledger_update) reads this exact filename.
    """
    assert "learnings_to_emit.json" in prompt_body, (
        "prompt body must reference output filename learnings_to_emit.json"
    )


def test_fallback_templates_present(prompt_body):
    """Body must contain template strings for at least R1, R2, R3 in
    both English and Korean variants (deterministic-template path is
    the V4 implementation, not just a fallback).
    """
    # English templates — distinguishing fragments.
    assert "Dispatch failure at step" in prompt_body, (
        "missing R1 English template fragment"
    )
    assert "matches deny pattern" in prompt_body, (
        "missing R2 English template fragment"
    )
    assert "Verify command exited fail" in prompt_body, (
        "missing R3 English template fragment"
    )

    # Korean templates — distinguishing fragments.
    assert "디스패치 실패" in prompt_body, (
        "missing R1 Korean template fragment"
    )
    assert "deny 패턴" in prompt_body, (
        "missing R2 Korean template fragment"
    )
    assert "검증 명령 fail" in prompt_body, (
        "missing R3 Korean template fragment"
    )


def test_evidence_preserved_verbatim(prompt_body):
    """Body must instruct sub-agent NOT to modify `evidence` /
    `evidence_hash` from Step 2. The hash covers the canonical-form
    evidence object, so any mutation desyncs ledger dedup downstream.
    """
    # Look for the verbatim/preserve directive near 'evidence_hash'.
    assert "verbatim" in prompt_body, (
        "prompt must instruct sub-agent to preserve evidence verbatim"
    )
    assert "evidence_hash" in prompt_body, (
        "prompt must reference evidence_hash field"
    )
    # Body must explicitly say DO NOT modify (caps preserved as a flag).
    assert "DO NOT modify" in prompt_body or "DO NOT modify or recompute" in prompt_body, (
        "prompt must contain explicit 'DO NOT modify' instruction "
        "for evidence / evidence_hash preservation"
    )


def test_emits_single_wrote_line(prompt_body):
    """Spike VII F7: orchestrator parses stdout with `^WROTE: (.+)$`
    last-match. Prompt body must instruct the sub-agent to emit
    `WROTE: ` (the regex anchor — note the space + colon).
    """
    assert "WROTE: " in prompt_body, (
        "prompt must instruct sub-agent to emit `WROTE: <path>` on stdout"
    )
    # Canonical print(f"WROTE: {out}") line should be present.
    assert 'print(f"WROTE: {out}")' in prompt_body, (
        "prompt must contain `print(f\"WROTE: {out}\")` invocation"
    )


def test_does_not_import_server_modules(prompt_body):
    """Step 3 is pure stdlib — must NOT import server.* (no LLM helper,
    no harness internals, no scope_parser).
    """
    forbidden = [
        "from server.",
        "import server.",
    ]
    for needle in forbidden:
        assert needle not in prompt_body, (
            f"Step 3 prompt must not contain {needle!r} — pure stdlib only"
        )


def test_summary_length_constraint_documented(prompt_body):
    """Body must document the ≤200 char single-line constraint
    (truncation at 197 + ellipsis).
    """
    assert "200" in prompt_body, (
        "prompt must document the 200-char summary cap"
    )
    assert "197" in prompt_body, (
        "prompt must document the 197-char truncation point"
    )


def test_language_detection_documented(prompt_body):
    """Body must document the Hangul-range heuristic for ko/en split."""
    assert "0xAC00" in prompt_body, (
        "prompt must document the Hangul Syllables range start (0xAC00)"
    )
    assert "0xD7A3" in prompt_body, (
        "prompt must document the Hangul Syllables range end (0xD7A3)"
    )
