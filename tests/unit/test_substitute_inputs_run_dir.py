# tests/unit/test_substitute_inputs_run_dir.py
import pytest
from server.harness import substitute_inputs


_PROMPT = """\
# Task

## Inputs
- RUN_ID: `{{RUN_ID}}`
- RUN_DIR: `{{RUN_DIR}}`
- artifact_path: `{{RUN_DIR}}/SCOPE.md`

## Body
Do the work.
"""


def test_run_dir_auto_derived_from_run_id(monkeypatch, tmp_path):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    out = substitute_inputs(_PROMPT, {"RUN_ID": "20260504-test"})
    expected_dir = (
        f"{tmp_path}/.claude/channels/assemble/runs/20260504-test"
    )
    assert "{{RUN_DIR}}" not in out
    assert "{{RUN_ID}}" not in out
    assert "RUN_ID: `20260504-test`" in out
    assert f"RUN_DIR: `{expected_dir}`" in out
    assert f"artifact_path: `{expected_dir}/SCOPE.md`" in out


def test_explicit_run_dir_overrides_auto_derivation(monkeypatch, tmp_path):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    out = substitute_inputs(_PROMPT, {
        "RUN_ID": "20260504-test",
        "RUN_DIR": "/custom/override",
    })
    assert "RUN_DIR: `/custom/override`" in out
    assert "RUN_ID: `20260504-test`" in out


def test_no_run_id_no_auto_derivation(monkeypatch, tmp_path):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    out = substitute_inputs(_PROMPT, {"RUN_DIR": "/manual/dir"})
    # No RUN_ID provided → not substituted
    assert "RUN_ID: `{{RUN_ID}}`" in out
    assert "RUN_DIR: `/manual/dir`" in out


def test_save_block_replace_calls_unchanged():
    """Spec §1.2 B2: replace() inside python save blocks must NOT be touched."""
    prompt = """\
## Inputs
- RUN_ID: `{{RUN_ID}}`

## Final step

```python
text.replace("{{RUN_ID}}", run_id)
text.replace("{{RUN_DIR}}", run_dir)
```
"""
    out = substitute_inputs(prompt, {"RUN_ID": "abc"})
    # Inputs section RUN_ID substituted
    assert "RUN_ID: `abc`" in out
    # Final step block intact (placeholders preserved for sub-agent)
    assert 'text.replace("{{RUN_ID}}", run_id)' in out
    assert 'text.replace("{{RUN_DIR}}", run_dir)' in out


def test_unsafe_run_id_raises_when_run_dir_absent(monkeypatch, tmp_path):
    """Auto-derive path triggers run_dir_path basename validation."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    with pytest.raises(ValueError, match="unsafe run_id"):
        substitute_inputs(_PROMPT, {"RUN_ID": "../escape"})


def test_unsafe_run_id_skipped_when_run_dir_explicit(monkeypatch, tmp_path):
    """Explicit RUN_DIR bypasses validation — caller takes responsibility."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    out = substitute_inputs(_PROMPT, {
        "RUN_ID": "../escape",  # would normally raise
        "RUN_DIR": "/safe/manual",
    })
    assert "RUN_ID: `../escape`" in out
    assert "RUN_DIR: `/safe/manual`" in out


# Spike VII follow-up: explicit regression for the `(?:^|\n)` regex extension
# made in B1 (commit 3ffbf96). The original `\n## Inputs` form would miss
# prompts whose first line is the Inputs header — now matched by the SOF
# alternation. Production prompts have a title line above `## Inputs`, so
# both shapes must work.

def test_inputs_at_char_zero_matched(monkeypatch, tmp_path):
    """Regex `(?:^|\\n)## Inputs` matches when prompt starts with the header."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    prompt = "## Inputs\n- RUN_ID: `{{RUN_ID}}`\n\n## End\n"
    out = substitute_inputs(prompt, {"RUN_ID": "abc"})
    assert "RUN_ID: `abc`" in out


def test_inputs_after_preamble_still_matched(monkeypatch, tmp_path):
    """Standard production-shape prompt (title + body before Inputs) preserved."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    prompt = (
        "# reviewer Step X\n"
        "Some preamble paragraph.\n\n"
        "## Inputs\n"
        "- RUN_ID: `{{RUN_ID}}`\n\n"
        "## Body\n"
    )
    out = substitute_inputs(prompt, {"RUN_ID": "abc"})
    assert "RUN_ID: `abc`" in out


# Spike VII follow-up: the body-level placeholder contract. `substitute_inputs`
# scopes substitution to the `## Inputs` section so save-block `.replace(...)`
# patterns survive (test_save_block_replace_calls_unchanged above). This means
# body references like `Read {{RUN_DIR}}/SCOPE.md` outside the Inputs section
# are intentionally NOT substituted — sub-agents resolve them by reading the
# Inputs section. Pin that intent so a future "fix the leftover placeholders"
# refactor doesn't break the design.

def test_body_run_dir_placeholder_left_for_subagent(monkeypatch, tmp_path):
    """Body references to {{RUN_DIR}} outside ## Inputs are NOT substituted.

    Sub-agents read the Inputs section and resolve body placeholders mentally.
    This is the documented contract; substituting the body would corrupt
    save-block `.replace("{{RUN_DIR}}", ...)` patterns.
    """
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    prompt = (
        "## Inputs\n"
        "- RUN_DIR: `{{RUN_DIR}}`\n\n"
        "## Goal\n"
        "Read `{{RUN_DIR}}/SCOPE.md` and write `{{RUN_DIR}}/parsed.json`.\n"
    )
    out = substitute_inputs(prompt, {"RUN_ID": "abc"})
    # Inputs: substituted to absolute path
    assert "RUN_DIR: `" in out
    assert "{{RUN_DIR}}`" not in out.split("## Goal")[0]
    # Body: placeholder preserved (sub-agent resolves via Inputs)
    body = out.split("## Goal")[1]
    assert "{{RUN_DIR}}/SCOPE.md" in body
    assert "{{RUN_DIR}}/parsed.json" in body
