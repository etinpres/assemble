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
