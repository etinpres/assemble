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

    On `subprocess.TimeoutExpired` the helper synthesizes a non-zero result
    rather than letting the exception bubble up, so callers always observe
    the same dict shape.
    """
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "stdout": exc.stdout or "",
            "stderr": (exc.stderr or "") + f"\n[git_helpers] timeout after {_GIT_TIMEOUT_S}s",
            "rc": -1,
        }
    return {
        "ok": proc.returncode == 0,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
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
    return _run_git(["tag", "-a", tag_name, "-m", message], cwd)


def git_tag_sha(cwd: Path, tag_name: str) -> dict:
    """Run ``git rev-parse <tag_name>`` in ``cwd``.

    Returns the SHA the tag resolves to (the tag object SHA for annotated
    tags, the pointed-to commit SHA for lightweight tags) via ``stdout``.
    Used by shipper ★ Step 4 to capture the tag SHA for the SHIP_REPORT.
    """
    return _run_git(["rev-parse", tag_name], cwd)
