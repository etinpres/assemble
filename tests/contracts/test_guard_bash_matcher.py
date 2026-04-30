"""Phase A guard — hook v2 Bash matcher.

The B-8 carryforward C reproducer placed the canonical magic marker
(`ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE`) as a Bash-comment prefix of a
non-Python invocation. Hook v1 substring grep accepted that. Hook v2
must reject it: the marker only counts when it appears inside the
*body* of a `python3 -c '...'` invocation or a `python3 << <EOF>`
heredoc.
"""

from pathlib import Path
import sys

import pytest

ASSEMBLE = Path.home() / ".claude/skills/assemble"
sys.path.insert(0, str(ASSEMBLE / "hooks"))

from _guard_bash_matcher import marker_present_in_python_body  # noqa: E402

MARKER = "ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE"


def test_b8_carryforward_c_bash_comment_prefix_rejected():
    """B-8 ADR iter1 reproducer — bash -c '# MARKER\\ncat > ...' must be rejected."""
    cmd = (
        f"bash -c '# {MARKER}\n"
        "cat > /tmp/runs/x/ADR.md <<EOF\n"
        "## Decision 1\n"
        "...\n"
        "EOF\n"
        "'"
    )
    assert marker_present_in_python_body(cmd) is False


def test_python3_dash_c_canonical_accepted():
    """python3 -c '# MARKER\\n<py>' is the canonical save block — accept."""
    cmd = (
        f"python3 -c '# {MARKER} -- sub-agent legitimate dispatch\n"
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path.home() / \".claude/skills/assemble\"))\n"
        "from server import write_run_artifact\n"
        "path = write_run_artifact(\"x\", \"PRD.md\", \"body\")\n"
        "print(f\"WROTE: {path}\")\n"
        "'"
    )
    assert marker_present_in_python_body(cmd) is True


def test_python3_heredoc_canonical_accepted():
    """python3 << EOF\\n# MARKER\\n<py>\\nEOF must accept."""
    cmd = (
        "python3 << PYEOF\n"
        f"# {MARKER}\n"
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path.home() / \".claude/skills/assemble\"))\n"
        "from server import write_run_artifact\n"
        "path = write_run_artifact(\"x\", \"PRD.md\", \"body\")\n"
        "print(f\"WROTE: {path}\")\n"
        "PYEOF"
    )
    assert marker_present_in_python_body(cmd) is True


def test_python3_dash_c_without_marker_rejected():
    """python3 -c '<py without marker>' is not a canonical save — reject."""
    cmd = "python3 -c 'import sys; print(\"hello\")'"
    assert marker_present_in_python_body(cmd) is False


def test_marker_outside_python_body_rejected():
    """echo MARKER ; python3 -c '<no marker>' — marker outside body — reject."""
    cmd = (
        f"echo {MARKER}; python3 -c 'import sys; print(\"hi\")'"
    )
    assert marker_present_in_python_body(cmd) is False
