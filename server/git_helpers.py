"""Read-only argv-list git probe wrappers (V4 Spike IX, Task A3).

Thin wrappers over ``subprocess.run`` for the git probes used by shipper ★
Step 1 (pre-flight) and Step 4 (local tag). Every helper invokes git via
an explicit argv list (the shell-disabled default for ``subprocess.run``) —
there is no path through the shell, no string interpolation into the
command, no ``os.system`` use.

This is the canonical T8 mitigation surface from the Spike IX threat table:
a malicious or mistaken caller passing a tag name like
``v1.0.0; rm -rf /`` cannot escape because git receives it as a single argv
element and rejects it (and ``git_create_tag`` additionally fails fast on
unsafe substrings before invoking subprocess at all).

The unit-test grep gate (``test_module_has_no_shell_true_or_os_system``)
asserts that the literal ``shell`` flag never appears in this module's
source — including this docstring — so prose here studiously avoids the
flag name.

Return shape (uniform across all six helpers that touch subprocess):
    {"ok": bool, "stdout": str, "stderr": str, "rc": int}

``git_tag_exists`` returns a bare ``bool`` because callers always want the
yes/no answer rather than the porcelain check itself.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
from pathlib import Path

# 10s is generous for read-only git probes on a local repo. The shipper Step 3
# build surface uses a separate longer-running Popen path (300s) — those
# concerns do not belong here.
_GIT_TIMEOUT_S = 10


def _run_git(args: list[str], cwd: Path) -> dict:
    """Invoke git with an explicit argv list and return the structured result.

    No shell invocation. No string interpolation. ``args`` is appended
    verbatim to ``["git", ...]`` and passed to subprocess as a list — each
    element becomes a separate argv slot, so shell metacharacters embedded
    in any element cannot escape into a new command.

    Uses ``Popen`` + ``start_new_session=True`` so git and any helper
    children it forks (gpg, fsmonitor, credential-helper) live in a fresh
    process group. On ``TimeoutExpired`` the helper sends ``SIGKILL`` to
    the entire group via ``os.killpg`` — closes the F4 residual risk where
    children outlive a plain ``subprocess.run`` timeout. After killing,
    ``communicate()`` is called again to drain the pipes and reap the
    zombie.

    Returns a uniform dict shape regardless of timeout / non-zero rc, so
    callers never see ``TimeoutExpired`` bubble up.
    """
    proc = subprocess.Popen(
        ["git", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(cwd),
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=_GIT_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        # Kill the entire process group — git itself plus any forked
        # helpers (gpg, fsmonitor, etc.) — then drain the pipes so the
        # zombie is reaped.
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            # Process already died or pgid unavailable — fall through to drain.
            pass
        try:
            stdout, stderr = proc.communicate()
        except Exception:
            stdout, stderr = "", ""
        return {
            "ok": False,
            "stdout": stdout or "",
            "stderr": (stderr or "") + f"\n[git_helpers] timeout after {_GIT_TIMEOUT_S}s",
            "rc": 124,
        }
    return {
        "ok": proc.returncode == 0,
        "stdout": stdout,
        "stderr": stderr,
        "rc": proc.returncode,
    }


def git_status_porcelain(cwd: Path) -> dict:
    """Run ``git status --porcelain`` in ``cwd``.

    Empty stdout = clean working tree. Used by shipper ★ Step 1 to gate the
    release on a clean tree — non-empty output → ``preflight.json.clean_tree
    = false`` and the dirty file list is captured for the SHIP_REPORT.
    """
    return _run_git(["status", "--porcelain"], cwd)


def git_head_sha(cwd: Path) -> dict:
    """Run ``git rev-parse HEAD`` in ``cwd``.

    Returns the current HEAD commit SHA via ``stdout`` (40-char hex for
    SHA-1 repos, 64-char for SHA-256 repos). Used by shipper ★ Step 1 to
    record the tag baseline.
    """
    return _run_git(["rev-parse", "HEAD"], cwd)


def git_branch(cwd: Path) -> dict:
    """Run ``git rev-parse --abbrev-ref HEAD`` in ``cwd``.

    Returns the current branch name via ``stdout``. Detached HEAD → ``HEAD``
    (git's default). Used by shipper ★ Step 1 for the SHIP_REPORT branch row.
    """
    return _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)


_RANGE_SPEC_RE = re.compile(r"[A-Za-z0-9_./~^@-]+(\.\.[A-Za-z0-9_./~^@-]+)?")


def git_diff_name_only(cwd: Path, range_spec: str = "HEAD~..HEAD") -> dict:
    """Run ``git diff --name-only <range_spec>`` in ``cwd``.

    Argv-list invocation. ``range_spec`` is validated up-front against a
    conservative ref-name character class (``[A-Za-z0-9_./~^@-]`` plus the
    ``..`` range separator). Argv-list invocation already neutralizes shell
    interpolation (T8); the regex is defense-in-depth ref-name discipline that
    keeps caller-controlled strings shaped like git refs.

    Default ``HEAD~..HEAD`` covers the most common "what changed in the last
    commit" probe used by keeper Step 1 to enumerate post-ship file churn.

    Returns the uniform dict shape ({ok, stdout, stderr, rc}). On invalid
    ``range_spec`` returns ``ok=False, rc=-1`` without touching subprocess.
    """
    if not _RANGE_SPEC_RE.fullmatch(range_spec):
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"invalid range_spec: {range_spec!r}",
            "rc": -1,
        }
    return _run_git(["diff", "--name-only", range_spec], cwd)


def git_tag_exists(cwd: Path, tag_name: str) -> bool:
    """Return True iff a tag exactly matching ``tag_name`` is present in
    ``cwd``.

    Implemented via ``git tag -l <tag_name>`` — git's ``-l`` filter matches
    the literal name (no glob expansion of plain identifiers), and the
    result must equal ``tag_name`` exactly to count as present. Prefix
    matches (e.g. ``v1`` when ``v1.0.0`` exists) return False.

    Used by shipper ★ Step 4 for the tag-collision pre-check (T5).
    """
    result = _run_git(["tag", "-l", tag_name], cwd)
    if not result["ok"]:
        # If the probe itself failed (e.g. not a git repo) treat as "not
        # present" — the downstream `git tag` will emit the canonical error.
        return False
    return result["stdout"].strip() == tag_name


def git_create_tag(cwd: Path, tag_name: str, message: str) -> dict:
    """Run ``git tag -a <tag_name> -m <message>`` in ``cwd``.

    Validation up-front (defense in depth — git itself also rejects most of
    these, but failing fast keeps the dispatch chain auditable):

      * empty / whitespace-only ``tag_name`` → ``ValueError``
      * ``tag_name`` containing any whitespace character → ``ValueError``
      * ``tag_name`` starting with ``-`` (would be parsed as a flag) →
        ``ValueError``
      * ``tag_name`` containing the substring ``..`` (rejected by git's
        ``check-ref-format``) → ``ValueError``

    The validation runs *before* subprocess so a hostile name never reaches
    git's argv. Even though argv-list invocation already neutralizes shell
    injection, treating obviously-bad names as a programming error gives the
    caller a deterministic exception path instead of a non-zero rc.
    """
    if not tag_name or not tag_name.strip():
        raise ValueError("tag_name must not be empty or whitespace-only")
    if any(ch.isspace() for ch in tag_name):
        raise ValueError(f"tag_name must not contain whitespace: {tag_name!r}")
    if tag_name.startswith("-"):
        raise ValueError(f"tag_name must not start with '-': {tag_name!r}")
    if ".." in tag_name:
        raise ValueError(f"tag_name must not contain '..': {tag_name!r}")
    # git check-ref-format forbidden character class — fail-fast preempt
    # (Spike IX Codex retro F3): without this, `~^:?*[\\` reach git itself,
    # leaving the SECURITY.md "validates BEFORE git" claim partially overstated.
    forbidden = frozenset("~^:?*[\\")
    if any(ch in forbidden for ch in tag_name):
        raise ValueError(f"tag_name contains forbidden character: {tag_name!r}")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in tag_name):
        raise ValueError(f"tag_name contains control character: {tag_name!r}")
    if tag_name.endswith(".lock"):
        raise ValueError(f"tag_name must not end with '.lock': {tag_name!r}")
    if tag_name.startswith("/") or tag_name.endswith("/") or "//" in tag_name:
        raise ValueError(f"tag_name has invalid slash placement: {tag_name!r}")
    if tag_name == "@" or "@{" in tag_name:
        raise ValueError(f"tag_name uses reserved git refspec syntax: {tag_name!r}")
    return _run_git(["tag", "-a", tag_name, "-m", message], cwd)


def git_tag_sha(cwd: Path, tag_name: str) -> dict:
    """Run ``git rev-parse <tag_name>`` in ``cwd``.

    Returns the SHA the tag resolves to (the tag object SHA for annotated
    tags, the pointed-to commit SHA for lightweight tags) via ``stdout``.
    Used by shipper ★ Step 4 to capture the tag SHA for the SHIP_REPORT.
    """
    return _run_git(["rev-parse", tag_name], cwd)
