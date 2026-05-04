"""Unit tests for `bundled/keeper/prompts/subagent/keeper_audit_step1.md`
(V4 Spike X, Task B2).

Grep-gate tests on the prompt body — these lock in the structural
contracts that other parts of the keeper bundle (D1 allowlist,
B3 extract_rules, B5 ledger_update) and the harness rely on:

  * F5 grep gate (Spike VI inheritance) — `## Bash tool access GRANTED`
    heading must be present so the harness's allowlist audit recognizes
    the prompt as a Bash-grant prompt rather than a default-deny one.
  * Spike VII Track A — `{{RUN_DIR}}` token (NOT `runs/{{RUN_ID}}`) so
    auto-derivation works.
  * Argv-list discipline (T8 inheritance from Spike IX) — prompt body
    imports git probes through `server.git_helpers`, never raw subprocess.
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
    / "keeper_audit_step1.md"
)


@pytest.fixture(scope="module")
def prompt_body() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def test_prompt_file_exists():
    assert PROMPT_PATH.is_file(), (
        f"keeper_audit_step1.md prompt missing at {PROMPT_PATH}"
    )


def test_bash_grant_heading_present(prompt_body):
    """F5 grep gate (Spike VI inheritance): exact heading string must
    appear so the harness's Bash-grant audit recognizes the prompt.
    """
    assert re.search(r"^## Bash tool access GRANTED\s*$", prompt_body, re.MULTILINE), (
        "prompt must contain '## Bash tool access GRANTED' heading "
        "(F5 grep gate from Spike VI)"
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


def test_writes_audit_inventory_json(prompt_body):
    """The prompt's deliverable filename is canonical — keeper Step 2/3
    consumers (extract_rules.py, ledger_update.py) read this exact name.
    """
    assert "audit_inventory.json" in prompt_body, (
        "prompt body must reference output filename audit_inventory.json"
    )


def test_imports_git_helpers(prompt_body):
    """Argv-list discipline (T8 inheritance from Spike IX): the prompt
    must dispatch git through `server.git_helpers`, never raw subprocess.
    """
    assert "from server.git_helpers import" in prompt_body, (
        "prompt must import git probes via `from server.git_helpers import ...` "
        "(argv-list discipline, T8 mitigation)"
    )


def test_uses_git_diff_name_only_helper(prompt_body):
    """The new B2 helper must be referenced — it's the post-ship file
    churn probe. Without it the audit_inventory.json git_diff_files
    field would be empty.
    """
    assert "git_diff_name_only" in prompt_body, (
        "prompt must call git_diff_name_only helper for HEAD~..HEAD probe"
    )


def test_emits_single_wrote_line(prompt_body):
    """Spike VII F7: orchestrator parses stdout with `^WROTE: (.+)$`
    last-match. Prompt body must instruct the sub-agent to emit
    `WROTE: ` (the regex anchor — note the space + colon).
    """
    # Body must contain the literal `WROTE: ` token (in the print() and the
    # output-discipline section).
    assert "WROTE: " in prompt_body, (
        "prompt must instruct sub-agent to emit `WROTE: <path>` on stdout"
    )
    # And the canonical print(f"WROTE: {out}") line should be present.
    assert 'print(f"WROTE: {out}")' in prompt_body, (
        "prompt must contain `print(f\"WROTE: {out}\")` invocation"
    )


def test_does_not_import_forbidden_modules(prompt_body):
    """Step 1 is pure deterministic file IO + git probes. It must NOT
    import LLM helpers, harness internals, or scope_parser — those
    belong in later steps (B3 extract_rules with LLM, B5 ledger_update).
    """
    forbidden = [
        "from server.scope_parser",
        "from server.harness",
        "import server.harness",
        "import server.scope_parser",
    ]
    for needle in forbidden:
        assert needle not in prompt_body, (
            f"Step 1 prompt must not contain {needle!r} — keep it minimal"
        )


def test_no_shell_true_in_prompt(prompt_body):
    """Defense in depth: even though the sub-agent runs the embedded
    Python (not shell), the prompt must not normalize `shell=True` as
    an acceptable pattern by referencing it as a code example.
    The 'Forbidden' section may NAME it as forbidden — that's fine
    because we check the exact assignment form `shell=True` only in
    code-style contexts. Here we just require it never appears in a
    way that would lex as a kwarg assignment outside the forbidden
    callout.
    """
    # We allow the literal token in the forbidden-list prose, but the
    # prompt must not show `subprocess.run(..., shell=True)` style usage.
    # A simple proxy: count occurrences and ensure the only ones are
    # within the forbidden-list context (under the "Forbidden" heading).
    occurrences = [m.start() for m in re.finditer(r"shell=True", prompt_body)]
    if not occurrences:
        return  # No mentions at all — best case.
    forbidden_section = re.search(
        r"\*\*Forbidden\*\*.*?(?=\n##|\Z)",
        prompt_body,
        re.DOTALL,
    )
    assert forbidden_section is not None, (
        "shell=True appears but no 'Forbidden' section to scope it"
    )
    f_start, f_end = forbidden_section.span()
    for pos in occurrences:
        assert f_start <= pos < f_end, (
            "shell=True must only appear inside the Forbidden callout"
        )
