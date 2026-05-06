"""Spike XIV Phase E — enforcement: SKILL.md dispatch_prompt 시그니처 drift
사전 차단.

dispatch_prompt(prompt_file)는 1-arg basename signature (server/harness.py:382).
SKILL.md 안에 stale 2-arg 또는 full-path 호출이 있으면 빈손 사용자가 그대로
복사·실행 시 TypeError / ValueError. 본 enforcement test 는 미래 drift 사전 catch.
"""
import re
from pathlib import Path

ASSEMBLE = Path.home() / ".claude/skills/assemble"
BUNDLED = ASSEMBLE / "bundled"

# Match dispatch_prompt('foo' ...) or dispatch_prompt("foo" ...).
# Captures: group(1) = filename, group(2) = next non-quote char (`,` or `)`).
PROMPT_CALL_RE = re.compile(
    r"""dispatch_prompt\(\s*['"]([^'"]+)['"]\s*([,)])"""
)

# Prose placeholders to skip (e.g. `dispatch_prompt('<file>.md')` in
# explanatory text). Markers `<` / `{` indicate placeholder, not a real
# basename.
PLACEHOLDER_MARKERS = ("<", "{")


def _bundled_skill_files():
    return sorted(
        p for p in BUNDLED.glob("*/SKILL.md")
        if not p.parent.name.startswith("_")
    )


def _iter_dispatch_calls():
    """Yield (skill_path, lineno, match) for every dispatch_prompt call in
    bundled SKILL.md files (excluding prose placeholders)."""
    for skill in _bundled_skill_files():
        text = skill.read_text(encoding="utf-8")
        for m in PROMPT_CALL_RE.finditer(text):
            fname = m.group(1)
            # Skip prose placeholders
            if any(marker in fname for marker in PLACEHOLDER_MARKERS):
                continue
            # Compute line number for actionable error messages
            lineno = text[:m.start()].count("\n") + 1
            yield skill, lineno, m


def test_all_bundled_skillmd_dispatch_prompt_uses_1arg_basename():
    """Every dispatch_prompt(...) call in bundled SKILL.md is 1-arg basename.

    Catches:
      - 2-arg form: dispatch_prompt('foo.md', run_id)
      - full path: dispatch_prompt('bundled/.../foo.md')
    """
    failures = []
    for skill, lineno, m in _iter_dispatch_calls():
        fname = m.group(1)
        next_char = m.group(2)
        rel = skill.relative_to(ASSEMBLE)
        # 2-arg check: next non-quote char after closing quote is `,`
        if next_char == ",":
            failures.append(
                f"{rel}:{lineno}: 2-arg call detected — dispatch_prompt is "
                f"1-arg basename only. Got: dispatch_prompt('{fname}', ...)"
            )
            continue
        # full-path check: must not contain `/` (basename only)
        if "/" in fname:
            failures.append(
                f"{rel}:{lineno}: full-path call detected — dispatch_prompt "
                f"takes basename only (resolver checks subagent/orchestrator "
                f"subdirs). Got: dispatch_prompt('{fname}')"
            )
    assert not failures, (
        "SKILL.md dispatch_prompt signature drift:\n  " + "\n  ".join(failures)
    )


def test_no_skillmd_uses_full_path_in_dispatch_prompt():
    """Negative anchor: 'bundled/' literal must not appear inside any
    dispatch_prompt('...') call site (full-path stale pattern from
    Spike XIII I4 idea-shaper drift)."""
    for skill, lineno, m in _iter_dispatch_calls():
        fname = m.group(1)
        rel = skill.relative_to(ASSEMBLE)
        assert "bundled/" not in fname, (
            f"{rel}:{lineno}: dispatch_prompt('{fname}') contains 'bundled/' — "
            f"use basename only"
        )
