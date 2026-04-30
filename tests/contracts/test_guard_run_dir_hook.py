"""Phase A guard — hook v2 end-to-end integration tests.

Drives `hooks/guard_run_dir.sh` via subprocess to verify the
context-aware Bash matcher (§1.3 C1 of Spike IV) blocks the
B-8 carryforward C reproducer (marker in a Bash comment, not in
a python3 body).
"""

import json
import subprocess
from pathlib import Path


def test_hook_v2_rejects_bash_comment_prefix_marker(tmp_path):
    """Drive the shell hook with the B-8 carryforward C reproducer payload.
    Expect exit code 2 (block) — hook v1 would have exited 0 (passthrough).
    """
    hook = Path.home() / ".claude/skills/assemble/hooks/guard_run_dir.sh"
    payload = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "bash -c '# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE\n"
                f"cat > {tmp_path}/runs/x/ADR.md <<EOF\n"
                "## Decision 1\n...\nEOF\n'"
            )
        },
    }
    proc = subprocess.run(
        ["bash", str(hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2, (
        f"hook should block (exit 2); got {proc.returncode}\n"
        f"stderr: {proc.stderr!r}"
    )
    assert "Spike IV" in proc.stderr or "v2" in proc.stderr
