"""Spike I hook v1 — Bash matcher branch test cases.

Tests guard_run_dir.sh exits 2 on main-write bypass and exits 0 on
sub-agent legitimate dispatch (magic marker present) plus unrelated
Bash commands.
"""

import json
import subprocess
from pathlib import Path

HOOK = Path.home() / ".claude/skills/assemble/hooks/guard_run_dir.sh"


def run_hook(tool_name: str, command: str):
    payload = json.dumps({
        "tool_name": tool_name,
        "tool_input": {"command": command},
    })
    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc


def test_a_main_python3_write_blocked():
    """Case A: main Bash + python3 + write_run_artifact + no marker → exit 2"""
    cmd = 'python3 -c "from server import write_run_artifact; write_run_artifact(\\"r\\", \\"PRD.md\\", \\"x\\")"'
    proc = run_hook("Bash", cmd)
    assert proc.returncode == 2, f"expected block (exit 2), got {proc.returncode}\nstderr:\n{proc.stderr}"
    assert (
        "메인" in proc.stderr
        or "차단됨" in proc.stderr
        or "guard" in proc.stderr.lower()
        or "GUARD" in proc.stderr
    ), f"expected guard-related substring in stderr, got:\n{proc.stderr}"


def test_b_subagent_marker_passes():
    """Case B: same as A but with magic marker → exit 0"""
    cmd = ('# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE\n'
           'python3 -c "from server import write_run_artifact; write_run_artifact(\\"r\\", \\"PRD.md\\", \\"x\\")"')
    proc = run_hook("Bash", cmd)
    assert proc.returncode == 0, f"expected pass (exit 0), got {proc.returncode}\nstderr:\n{proc.stderr}"


def test_c_unrelated_bash_passes():
    """Case C: unrelated command (no python3, no runs/) → exit 0"""
    proc = run_hook("Bash", "ls /tmp")
    assert proc.returncode == 0


def test_d_python3_no_runs_passes():
    """Case D: python3 invocation but no runs/ or write_run_artifact → exit 0"""
    proc = run_hook("Bash", 'python3 -c "print(1)"')
    assert proc.returncode == 0


def test_iteration_state_json_passes_hook():
    """Spike II F8: iteration_state.json direct-write must NOT be blocked.

    Hook v1 regex caught all `runs/<rid>/*.json` — false positive on
    orchestrator metadata. v2 regex is whitelist-only (PRD/ARCH/ADR/UI).
    """
    cmd = (
        'python3 -c \'open("/Users/u/.claude/channels/assemble/runs/20260501/iteration_state.json", "w")'
        ".write(\"{}\")'"
    )
    proc = run_hook("Bash", cmd)
    assert proc.returncode == 0, (
        f"iteration_state.json must pass — orchestrator metadata\n"
        f"stderr:\n{proc.stderr}"
    )


def test_dispatches_jsonl_passes_hook():
    cmd = (
        'python3 -c \'open("/Users/u/.claude/channels/assemble/runs/20260501/dispatches.jsonl", "a")'
        ".write(\"{}\")'"
    )
    proc = run_hook("Bash", cmd)
    assert proc.returncode == 0


def test_prd_md_still_blocked_without_marker():
    cmd = (
        'python3 -c \'open("/Users/u/.claude/channels/assemble/runs/20260501/PRD.md", "w")'
        ".write(\"x\")'"
    )
    proc = run_hook("Bash", cmd)
    assert proc.returncode == 2  # main bypass still blocked


def test_arch_adr_ui_md_blocked_without_marker():
    """All four whitelisted artifacts blocked when no marker."""
    for fname in ("ARCHITECTURE.md", "ADR.md", "UI_GUIDE.md"):
        cmd = (
            f'python3 -c \'open("/Users/u/.claude/channels/assemble/runs/r/{fname}", "w")'
            ".write(\"x\")'"
        )
        proc = run_hook("Bash", cmd)
        assert proc.returncode == 2, f"{fname} must be blocked"
