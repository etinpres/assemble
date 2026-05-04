"""Deterministic SCOPE.md parser.

Parses the structured SCOPE.md artifact produced by builder ★ Step 1 into
the JSON shape consumed by reviewer Step 3 + verifier Step 1.

Grammar rules enforced:
  Form 1 (backtick-wrapped):  ``- `<path-token>` — <note>``
  Form 2 (plain-path):        ``- <plain-token> — <note>``
  Form 3 (note-less):         ``- `<path-token>` `` or ``- <plain-token>``
  Em-dash MUST be U+2014 (—). En-dash (–) and double-hyphen (--) are rejected.
  Path tokens: no whitespace, no backticks.

Errors are collected and returned in the ``"errors"`` field; the parser
never raises.

Korean characters are fully supported — ensure_ascii=False is the project
standard.
"""

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Module-level compiled patterns
# ---------------------------------------------------------------------------

# H1 title extraction: ``# SCOPE — <task_summary>`` (em-dash required)
# Falls back to everything after ``# SCOPE`` if no em-dash present.
_H1_RE = re.compile(
    r"""
    ^
    \#\ SCOPE         # literal "# SCOPE"
    (?:
        \s*—\s*  # em-dash (U+2014) with optional surrounding spaces
        (.+)          # group 1: task summary
    )?
    $
    """,
    re.VERBOSE | re.MULTILINE,
)

# Section headers — match ``## Allow list`` and ``## Deny list``
_ALLOW_SECTION_RE = re.compile(r"^##\s+Allow\s+list\s*$", re.MULTILINE | re.IGNORECASE)
_DENY_SECTION_RE = re.compile(r"^##\s+Deny\s+list\s*$", re.MULTILINE | re.IGNORECASE)

# Completion criterion header
_COMPLETION_SECTION_RE = re.compile(
    r"^##\s+Completion\s+criterion\s*$", re.MULTILINE | re.IGNORECASE
)

# Bullet line prefix — ``- `` at column 0
_BULLET_RE = re.compile(r"^-\s+(.+)$")

# Next section start (any ``##`` header)
_NEXT_SECTION_RE = re.compile(r"^##", re.MULTILINE)

# Path token validation: no whitespace, no backticks
_VALID_PATH_RE = re.compile(r"^[^\s`]+$")

# Plain-path token form: dots/slashes/globs/dashes but no spaces/backticks
# (same as _VALID_PATH_RE but explicit for clarity)
_PLAIN_PATH_RE = re.compile(r"^[^\s`]+$")

# Em-dash separator with single space on each side
_EM_DASH_SEP = "—"

# Bullet parsing — three strict forms:
#
#  Form 1: ``- `<path>` — <note>``     (backtick-wrapped, with note)
#  Form 2: ``- <plain> — <note>``      (plain-path, with note)
#  Form 3a: ``- `<path>` ``            (backtick-wrapped, no em-dash)
#  Form 3b: ``- <plain>``              (plain-path, no em-dash)
#
# Em-dash MUST be U+2014. En-dash or double-hyphen → rejected.

_BACKTICK_WITH_NOTE_RE = re.compile(
    r"""
    ^
    `([^`\s]+)`                  # group 1: path inside single-level backticks (no ws, no bt)
    \s+—\s+                 # em-dash with single space on each side
    (.+)                         # group 2: note (anything)
    $
    """,
    re.VERBOSE,
)

_BACKTICK_NOTE_LESS_RE = re.compile(
    r"""
    ^
    `([^`\s]+)`                  # group 1: path inside single-level backticks
    \s*$                         # nothing else (note-less)
    """,
    re.VERBOSE,
)

_PLAIN_WITH_NOTE_RE = re.compile(
    r"""
    ^
    ([^\s`]+)                    # group 1: plain path token (no ws, no bt)
    \s+—\s+                 # em-dash with single space on each side
    (.+)                         # group 2: note
    $
    """,
    re.VERBOSE,
)

_PLAIN_NOTE_LESS_RE = re.compile(
    r"""
    ^
    ([^\s`]+)                    # group 1: plain path token
    \s*$                         # nothing else (note-less)
    """,
    re.VERBOSE,
)

# Detect prohibited separators (en-dash or double-hyphen) to provide explicit
# grammar errors rather than silently treating the bullet as note-less or
# invalid for other reasons.
_EN_DASH_RE = re.compile(r"–")  # en-dash U+2013
_DOUBLE_HYPHEN_RE = re.compile(r"--")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_bullet(
    line: str,
    idx: int,
    section_label: str,
) -> tuple[Optional[dict], Optional[str]]:
    """Parse a single bullet-body string (the ``-`` prefix already stripped).

    Args:
        line:          The text *after* the ``- `` prefix (stripped).
        idx:           0-based bullet index within the section (for error labels).
        section_label: ``"allow"`` or ``"deny"`` (used in error key names).

    Returns:
        (entry_dict, None)  — valid parse
        (None, error_key)   — grammar violation; entry is NOT stored
    """
    error_key = f"{section_label}-entry-{idx}-grammar"

    # Check for prohibited separators first so the error message is unambiguous.
    if _EN_DASH_RE.search(line) and _EM_DASH_SEP not in line:
        return None, error_key
    # double-hyphen as separator (standalone " -- " with spaces around it)
    if re.search(r"\s--\s", line):
        return None, error_key

    # Form 1: backtick-wrapped with note
    m = _BACKTICK_WITH_NOTE_RE.match(line)
    if m:
        path, note = m.group(1), m.group(2).strip()
        if _VALID_PATH_RE.match(path):
            return {"path": path, "note": note}, None
        return None, error_key

    # Form 3a: backtick-wrapped, note-less
    m = _BACKTICK_NOTE_LESS_RE.match(line)
    if m:
        path = m.group(1)
        if _VALID_PATH_RE.match(path):
            return {"path": path, "note": ""}, None
        return None, error_key

    # Form 2: plain-path with note
    m = _PLAIN_WITH_NOTE_RE.match(line)
    if m:
        path, note = m.group(1), m.group(2).strip()
        if _PLAIN_PATH_RE.match(path):
            return {"path": path, "note": note}, None
        return None, error_key

    # Form 3b: plain-path, note-less
    m = _PLAIN_NOTE_LESS_RE.match(line)
    if m:
        path = m.group(1)
        if _PLAIN_PATH_RE.match(path):
            return {"path": path, "note": ""}, None
        return None, error_key

    # Nothing matched — reject
    return None, error_key


def _extract_section_text(text: str, section_match: re.Match) -> str:
    """Return the text from ``section_match.end()`` to the next ``##`` header
    (or end of string), stripped.
    """
    start = section_match.end()
    rest = text[start:]
    next_sec = _NEXT_SECTION_RE.search(rest)
    if next_sec:
        return rest[: next_sec.start()].strip()
    return rest.strip()


def _parse_section_bullets(
    section_text: str,
    section_label: str,
) -> tuple[list[dict], list[str]]:
    """Extract and parse all ``- `` bullets in ``section_text``.

    Args:
        section_text:  The text body between the section header and the next one.
        section_label: ``"allow"`` or ``"deny"``.

    Returns:
        (entries, errors) where entries are dicts with ``path``/``note`` keys
        and errors are ``*-entry-N-grammar`` strings.
    """
    entries: list[dict] = []
    errors: list[str] = []
    idx = 0
    for line in section_text.splitlines():
        bullet_m = _BULLET_RE.match(line.strip())
        if not bullet_m:
            continue  # skip non-bullet lines (blank, prose, sub-headers)
        body = bullet_m.group(1).strip()
        entry, error = _parse_bullet(body, idx, section_label)
        if entry is not None:
            entries.append(entry)
        if error is not None:
            errors.append(error)
        idx += 1
    return entries, errors


def _extract_completion(text: str) -> tuple[str, bool, list[str]]:
    """Extract the bash one-liner from the completion criterion fence.

    Looks for ``## Completion criterion`` header, then a triple-backtick bash
    fence. Returns ``(completion_text, found, fence_errors)`` where:
      - ``found`` is False when the fence is absent or empty.
      - ``fence_errors`` contains ``"completion-fence-unclosed"`` when the
        opening fence has no matching closing fence. In that case the captured
        content is still returned (Option A warning-style): the caller decides
        whether to reject or accept the partial content. The verifier Step 1
        already validates ``len(completion) > 0`` and applies a 500-char cap,
        so surfacing the error label gives downstream layers the signal without
        forcing a destructive truncation here.

    NOTE: section terminator does not respect fence boundaries.
    Completion lines starting with ``##`` at column 0 will truncate the
    captured fence. For B-13 the 500-char single-line completions cannot
    trigger this; future SCOPE authors using heredoc-style multi-line
    completions need to indent ``##`` lines or escape them.
    """
    comp_m = _COMPLETION_SECTION_RE.search(text)
    if not comp_m:
        return "", False, []

    section_text = _extract_section_text(text, comp_m)
    lines = section_text.splitlines()

    in_fence = False
    fence_closed = False
    fence_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not in_fence:
            if stripped.startswith("```"):
                in_fence = True
        else:
            if stripped.startswith("```"):
                fence_closed = True
                break
            fence_lines.append(line)

    result = "\n".join(fence_lines).strip()

    fence_errors: list[str] = []
    if in_fence and not fence_closed:
        fence_errors.append("completion-fence-unclosed")

    return result, bool(result), fence_errors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_scope_md(text: str) -> dict:
    """Parse SCOPE.md text into the JSON shape consumed by reviewer Step 3 +
    verifier Step 1.

    Returns:
        {
          "task_summary": str,      # H1 line stripped of '# SCOPE — ' prefix
          "allow": [{"path": str, "note": str}, ...],
          "deny":  [{"path": str, "note": str}, ...],
          "completion": str,         # bash one-liner from fenced block
          "errors": [str, ...]       # section-level + entry-level errors
        }

    Errors surface as labelled strings:
      - "scope-missing"                — text empty
      - "allow-section-missing"
      - "completion-empty"
      - "completion-fence-unclosed"   — opening ``` fence with no closing ```
                                        (Option A: captured content is kept as a
                                        warning; caller/verifier decides what to do)
      - "deny-entry-N-grammar"        — entry index N violates strict grammar
      - "allow-entry-N-grammar"       — entry index N violates strict grammar
    """
    errors: list[str] = []

    # Guard: empty input
    if not text or not text.strip():
        return {
            "task_summary": "",
            "allow": [],
            "deny": [],
            "completion": "",
            "errors": ["scope-missing"],
        }

    # --- H1 task_summary ---
    task_summary = ""
    h1_m = _H1_RE.search(text)
    if h1_m:
        task_summary = (h1_m.group(1) or "").strip()

    # --- Allow list ---
    allow_entries: list[dict] = []
    allow_m = _ALLOW_SECTION_RE.search(text)
    if allow_m is None:
        errors.append("allow-section-missing")
    else:
        section_text = _extract_section_text(text, allow_m)
        allow_entries, allow_errors = _parse_section_bullets(section_text, "allow")
        errors.extend(allow_errors)

    # --- Deny list (optional) ---
    deny_entries: list[dict] = []
    deny_m = _DENY_SECTION_RE.search(text)
    if deny_m is not None:
        section_text = _extract_section_text(text, deny_m)
        deny_entries, deny_errors = _parse_section_bullets(section_text, "deny")
        errors.extend(deny_errors)
    # If deny section is absent: deny=[], no error (intentional per spec)

    # --- Completion criterion ---
    completion, found, fence_errors = _extract_completion(text)
    errors.extend(fence_errors)
    if not found:
        errors.append("completion-empty")

    return {
        "task_summary": task_summary,
        "allow": allow_entries,
        "deny": deny_entries,
        "completion": completion,
        "errors": errors,
    }
