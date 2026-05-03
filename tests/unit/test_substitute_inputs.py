"""Spike V.1 §3 — substitute_inputs() helper guard.

The helper substitutes `{{KEY}}` placeholders within the `## Inputs` section
only — the save block (typically under `## Final step`) MUST be left intact
so the sub-agent's `.replace("{{KEY}}", var)` template instructions still work.
"""

import server


_SAMPLE_PROMPT = """[HARNESS RULES]
1. test rule

[TASK]
# builder Step X — example
You are dispatched as builder Step X sub-agent. Print `WROTE: <absolute path>` on stdout.

## Inputs

- run_id: `{{RUN_ID}}`
- task_summary: `{{TASK_SUMMARY}}`
- ac_cmd: `{{AC_CMD}}`

## Goal

Write something using `{{RUN_ID}}` interpolated above. Step 4 owns implementation.

## Final step (canonical save block)

```python
rid = "{{RUN_ID}}"  # sub-agent var assign — caller-substituted is also OK
template_str = open(path).read()
result = template_str.replace("{{RUN_ID}}", rid).replace("{{TASK_SUMMARY}}", ts)
print(f"WROTE: {result}")
```
"""


def test_substitute_inputs_replaces_only_in_inputs_section():
    out = server.substitute_inputs(_SAMPLE_PROMPT, {
        "RUN_ID": "abc123",
        "TASK_SUMMARY": "build foo",
        "AC_CMD": "pytest tests/",
    })
    # Inputs section should be substituted
    assert "- run_id: `abc123`" in out
    assert "- task_summary: `build foo`" in out
    assert "- ac_cmd: `pytest tests/`" in out


def test_substitute_inputs_preserves_save_block_replace_args():
    """The save block's `.replace("{{KEY}}", var)` calls MUST survive intact —
    if global replace happened, those .replace calls would become
    .replace("abc123", rid) and break sub-agent execution."""
    out = server.substitute_inputs(_SAMPLE_PROMPT, {
        "RUN_ID": "abc123",
        "TASK_SUMMARY": "build foo",
    })
    # save block .replace literal arguments must NOT be substituted
    assert '.replace("{{RUN_ID}}", rid)' in out
    assert '.replace("{{TASK_SUMMARY}}", ts)' in out


def test_substitute_inputs_preserves_goal_section_placeholders():
    """## Goal section is outside ## Inputs — placeholder there stays.
    (Some prompts reference `{{RUN_ID}}` in narrative for the sub-agent
    to substitute itself when constructing artifact paths.)"""
    out = server.substitute_inputs(_SAMPLE_PROMPT, {"RUN_ID": "abc123"})
    # Goal section (between '## Goal' and '## Final step') stays intact
    goal_section = out.split("## Goal")[1].split("## Final step")[0]
    assert "{{RUN_ID}}" in goal_section


def test_substitute_inputs_no_inputs_header_returns_unchanged():
    """If `## Inputs` is absent, helper returns the prompt as-is."""
    text = "[TASK]\n# Some prompt without Inputs section\n\nBody {{RUN_ID}}.\n"
    out = server.substitute_inputs(text, {"RUN_ID": "abc"})
    assert out == text


def test_substitute_inputs_empty_dict_returns_unchanged():
    out = server.substitute_inputs(_SAMPLE_PROMPT, {})
    assert out == _SAMPLE_PROMPT


def test_substitute_inputs_missing_keys_silently_ignored():
    """Keys not present in the section are no-ops (some prompts list optional
    inputs the orchestrator may not always provide)."""
    out = server.substitute_inputs(_SAMPLE_PROMPT, {
        "RUN_ID": "abc",
        "NONEXISTENT_KEY": "ignored",
    })
    assert "- run_id: `abc`" in out
    assert "{{TASK_SUMMARY}}" in out  # still untouched


def test_substitute_inputs_coerces_non_string_values():
    """str() coercion lets caller pass int/Path/etc. without manual conversion."""
    out = server.substitute_inputs(
        "[TASK]\n## Inputs\n\n- count: `{{COUNT}}`\n\n## Goal\n",
        {"COUNT": 42},
    )
    assert "- count: `42`" in out
