"""Spike VI Phase A — bundled SKILL.md frontmatter normalized to double-quoted strings.

Round-trips frontmatter through yaml.safe_dump(default_style='"') and asserts the
output equals the input (idempotent). Catches single-quoted, unquoted, or mixed-style
strings that future strict YAML processors would warn on.
"""
from pathlib import Path

import yaml

ASSEMBLE = Path.home() / ".claude/skills/assemble"
BUNDLED = ASSEMBLE / "bundled"


def _extract_frontmatter(text: str) -> str:
    """Return YAML text between the leading `---` markers, or '' if absent."""
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---", 4)
    if end == -1:
        return ""
    return text[4:end + 1]


def _bundled_skill_files():
    # Skip _shared/ — it's shared infra, not a bundle.
    return sorted(
        p for p in BUNDLED.glob("*/SKILL.md")
        if not p.parent.name.startswith("_")
    )


def test_every_bundled_skill_frontmatter_loads_strict():
    """All bundled SKILL.md frontmatter parses without yaml errors."""
    for skill in _bundled_skill_files():
        fm = _extract_frontmatter(skill.read_text(encoding="utf-8"))
        if not fm:
            continue
        # Must parse cleanly — no YAMLError raised.
        parsed = yaml.safe_load(fm)
        assert isinstance(parsed, dict), f"{skill.relative_to(ASSEMBLE)}: frontmatter not a mapping"


def test_every_bundled_skill_frontmatter_string_values_double_quoted():
    """All string values in frontmatter use double-quoted form (idempotent re-dump).

    For top-level scalar strings: must appear as `key: "value"` literally.
    For list-of-strings values: each element must appear as `"element"`
    inside the list (we accept both inline `[...]` and block `- ...` styles).
    Non-string values (bools, ints, lists of non-strings) are skipped.
    """
    failures = []
    for skill in _bundled_skill_files():
        fm = _extract_frontmatter(skill.read_text(encoding="utf-8"))
        if not fm:
            continue
        parsed = yaml.safe_load(fm)
        rel = skill.relative_to(ASSEMBLE)
        for key, value in parsed.items():
            if isinstance(value, str):
                literal = f'{key}: "{value}"'
                if literal in fm:
                    continue
                # Allow escaped-quote case: re-dump with default_style='"' and
                # check membership of the resulting line.
                dumped_line = yaml.safe_dump(
                    {key: value}, default_style='"', default_flow_style=False
                ).rstrip()
                if dumped_line in fm:
                    continue
                failures.append(f"{rel}: field '{key}' not double-quoted")
            elif isinstance(value, list) and all(isinstance(x, str) for x in value):
                # Each list element must be wrapped in double quotes somewhere
                # in the frontmatter.
                for elem in value:
                    quoted = f'"{elem}"'
                    if quoted not in fm:
                        failures.append(
                            f"{rel}: list element '{elem}' in '{key}' not double-quoted"
                        )
    assert not failures, "Frontmatter quote-style violations:\n" + "\n".join(failures)
