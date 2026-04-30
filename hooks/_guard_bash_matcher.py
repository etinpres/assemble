"""Hook v2 helper — context-aware magic-marker matcher.

The hook delegates Bash command matching to this module so we can
unit-test the matcher independently of the shell wrapper. The matcher
returns True only when the canonical magic marker
(`ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE`) appears inside the body of a
`python3 -c '...'` invocation or a `python3 << <delim>` heredoc.

Carryforward C from B-8 dogfood: a Bash-comment prefix
(`bash -c '# MARKER\\n<bash code>'`) must NOT count as a canonical
save — the marker outside a python3 body is unauthorized.
"""

from __future__ import annotations

import re
import sys
from typing import List

MARKER = "ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE"


def _extract_python_dash_c_bodies(cmd: str) -> List[str]:
    """Return the raw bodies of every `python3 -c '<body>'` (or `"<body>"`)
    invocation inside `cmd`. Single- or double-quoted; first matching pair
    only — escaped quotes inside the body are honored as part of the body.
    """
    bodies: List[str] = []
    pattern = re.compile(
        r"python3?\s+-c\s+(['\"])((?:\\.|(?!\1).)*)\1",
        re.DOTALL,
    )
    for match in pattern.finditer(cmd):
        bodies.append(match.group(2))
    return bodies


def _extract_python_heredoc_bodies(cmd: str) -> List[str]:
    """Return the raw bodies of every `python3 << <DELIM>` heredoc inside
    `cmd`. <DELIM> is one or more word chars (allow optional surrounding
    quotes — common shell idiom, e.g. `<< "EOF"`). Body extends from the
    line after `<< DELIM` to the line containing only DELIM.
    """
    bodies: List[str] = []
    opener_re = re.compile(
        r"python3?\s+<<-?\s*[\"']?(\w+)[\"']?\s*\n",
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


def marker_present_in_python_body(cmd: str) -> bool:
    """Return True iff the canonical magic marker appears inside the
    body of a python3 -c invocation or python3 heredoc within `cmd`.

    Matches anywhere in the body (not just first line) because
    canonical save blocks may carry a leading docstring or shebang
    above the marker comment line. The narrow guarantee is that the
    marker is *inside* python3 code, not in a Bash comment or echo.
    """
    if MARKER not in cmd:
        return False
    bodies = (
        _extract_python_dash_c_bodies(cmd)
        + _extract_python_heredoc_bodies(cmd)
    )
    return any(MARKER in body for body in bodies)


def main(argv: List[str]) -> int:
    """CLI entry — read Bash command from stdin (one argument: nothing).

    Exit code:
        0 — marker present in python3 body (canonical save, hook passes)
        1 — marker absent or out-of-body (reject)
    """
    cmd = sys.stdin.read()
    return 0 if marker_present_in_python_body(cmd) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
