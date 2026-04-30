"""Hook v2 helper — context-aware magic-marker matcher.

The hook delegates Bash command matching to this module so we can
unit-test the matcher independently of the shell wrapper. The matcher
returns True only when the canonical magic marker
(`ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE`) appears as the first non-empty
line of a `python3 -c '...'` invocation or `python3 << <delim>` heredoc
body, formatted as a Python comment.

Carryforward C from B-8 dogfood: a Bash-comment prefix
(`bash -c '# MARKER\\n<bash code>'`) must NOT count as a canonical
save — the marker outside a python3 body is unauthorized.

Spike IV §1.3 C1.3: the marker is treated as a comment-context signal,
not a substring toggle. Marker inside a string literal, marker on a
non-first line, or marker without a `#` prefix → False.
"""

from __future__ import annotations

import re
import sys

MARKER = "ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE"


def _extract_python_dash_c_bodies(cmd: str) -> list[str]:
    """Return the raw bodies of every `python3 -c '<body>'` (or `"<body>"`)
    invocation inside `cmd`. Single- or double-quoted; first matching pair
    only — escaped quotes inside the body are honored as part of the body.
    Accepts `python3`, `python`, `python3.10`, `python3.11`, etc.
    """
    bodies: list[str] = []
    pattern = re.compile(
        r"python3?(?:\.\d+)?\s+-c\s+(['\"])((?:\\.|(?!\1).)*)\1",
        re.DOTALL,
    )
    for match in pattern.finditer(cmd):
        bodies.append(match.group(2))
    return bodies


def _extract_python_heredoc_bodies(cmd: str) -> list[str]:
    """Return the raw bodies of every `python3 << <DELIM>` heredoc inside
    `cmd`. <DELIM> is one or more word chars (allow optional surrounding
    quotes — common shell idiom, e.g. `<< "EOF"`). Body extends from the
    line after `<< DELIM` to the line containing only DELIM.
    Accepts `python3`, `python`, `python3.10`, `python3.11`, etc.
    """
    bodies: list[str] = []
    opener_re = re.compile(
        r"python3?(?:\.\d+)?\s+<<-?\s*[\"']?(\w+)[\"']?\s*\n",
    )
    for match in opener_re.finditer(cmd):
        delim = match.group(1)
        start = match.end()
        end_re = re.compile(
            rf"^\s*{re.escape(delim)}\s*$",
            re.MULTILINE,
        )
        end_match = end_re.search(cmd, pos=start)
        if end_match is None:
            bodies.append(cmd[start:])
        else:
            bodies.append(cmd[start:end_match.start()])
    return bodies


def _is_canonical_first_line(body: str) -> bool:
    """Return True iff the first non-empty source line of `body`
    starts with `# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE`. Only the
    leading whitespace is stripped. Anything else (string literal,
    non-comment line, marker as substring of a non-marker comment) → False.
    """
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        return stripped.startswith("# " + MARKER) or stripped.startswith("#" + MARKER)
    return False


def marker_present_in_python_body(cmd: str) -> bool:
    """Return True iff a python3 invocation in `cmd` carries the
    canonical marker as the first non-empty line of its body, in
    Python comment form.

    Spike IV §1.3 C1.3: the marker is treated as a comment-context
    signal, not a substring toggle. Marker inside a string literal,
    marker on a non-first line, or marker without a `#` prefix → False.
    Match permits a leading shebang only if the shebang is followed
    immediately by the marker comment (still considered "first non-empty
    line" for canonical save blocks).
    """
    if MARKER not in cmd:
        return False
    bodies = (
        _extract_python_dash_c_bodies(cmd)
        + _extract_python_heredoc_bodies(cmd)
    )
    return any(_is_canonical_first_line(body) for body in bodies)


def main() -> int:
    """CLI entry — read Bash command from stdin (one argument: nothing).

    Exit code:
        0 — marker present in python3 body (canonical save, hook passes)
        1 — marker absent or out-of-body (reject)
    """
    cmd = sys.stdin.read()
    return 0 if marker_present_in_python_body(cmd) else 1


if __name__ == "__main__":
    sys.exit(main())
