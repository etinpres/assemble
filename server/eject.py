"""Pure-copy bundle-to-user-skill module — `/assemble eject` command.

Spike XII — V4 #9 IO exception (main-direct copy, no sub-agent dispatch).
See docs/specs/2026-05-05-v4-spike-xii-design.md.

This module copies a bundled skill (e.g., ``bundled/builder/``) to a user
skill directory at ``~/.claude/skills/<name>/`` so it becomes self-evolvable
outside the assemble bundle. The eject is byte-faithful: no frontmatter
rewriting, no SKILL.md mutation, no inventory state mutation.

Architectural identity:
    - Pure functions only; ``apply_eject`` is the lone side-effect function.
    - shutil/pathlib only; **no subprocess, no shell escape**.
    - Atomic temp+rename contract — partial failures leave no half-copied
      state, mirroring ``server/run_dir.write_run_artifact`` semantics.
    - Backup-on-overwrite (``.bak.<ts>`` survivor, no auto-cleanup).
    - Destination always under ``<home>/.claude/skills/<name>/`` so the
      ejected skill is automatically discovered by
      ``inventory.enumerate_skill_paths``.

Public surface (9 symbols):
    EjectError, EjectPlan,
    assemble_root, available_bundles, resolve_source,
    validate_dest_name, resolve_dest, dry_run_plan, apply_eject.
"""

import os
import re
import secrets
import shutil
import time
from pathlib import Path
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Public exceptions / value types
# ---------------------------------------------------------------------------


class EjectError(Exception):
    """Base exception for eject failures with a human-readable reason."""


class EjectPlan(NamedTuple):
    """Result of dry_run_plan — files that would be copied + warnings."""
    src: Path
    dest: Path
    bundle_name: str
    files: list[Path]              # absolute paths under src
    total_bytes: int
    dest_exists: bool              # True iff dest dir already exists pre-apply
    warnings: list[str]            # e.g., "destination already contains a SKILL.md"


# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------


_RESERVED_NAMES = frozenset({"assemble", "_shared"})
_NAME_PATTERN = r"^[a-z][a-z0-9_-]{0,63}$"
_NAME_RE = re.compile(_NAME_PATTERN)


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def assemble_root(home: Path | None = None) -> Path:
    """Return ``<home>/.claude/skills/assemble`` (or $ASSEMBLE_HOME-rooted).

    Resolution order:
        1. Explicit ``home`` argument wins (tests pass tmp_path here).
        2. ``$ASSEMBLE_HOME`` env var (mirrors
           ``server/inventory._home_for_scan`` and
           ``server/run_dir._runs_dir`` conventions).
        3. ``Path.home()`` fallback.
    """
    if home is not None:
        base = Path(home)
    else:
        env = os.environ.get("ASSEMBLE_HOME")
        base = Path(env) if env else Path.home()
    return base / ".claude/skills/assemble"


def available_bundles(home: Path | None = None) -> list[str]:
    """Sorted list of bundle directory names under ``assemble/bundled/``.

    Excludes ``_shared`` and any directory whose name starts with ``_`` or
    ``.`` (hidden / private). Returns an empty list if ``bundled/`` is
    missing.
    """
    bundled_root = assemble_root(home) / "bundled"
    if not bundled_root.is_dir():
        return []
    return sorted(
        p.name for p in bundled_root.iterdir()
        if p.is_dir()
        and not p.name.startswith("_")
        and not p.name.startswith(".")
    )


def resolve_source(bundle_name: str, home: Path | None = None) -> Path:
    """Return the absolute path to ``bundled/<bundle_name>/``.

    Raises ``EjectError`` if the bundle does not exist; the error message
    includes the available bundle list so callers can render a
    user-friendly hint.
    """
    src = assemble_root(home) / "bundled" / bundle_name
    if not src.is_dir():
        available = available_bundles(home)
        raise EjectError(
            f"bundle not found: {bundle_name!r}; "
            f"available={available}"
        )
    return src


def validate_dest_name(name: str) -> str:
    """Validate destination skill name. Returns ``name`` verbatim on success.

    Three guards (deny-by-default), checked in order so the error message
    is the most specific available:
        1. Reserved name (``assemble``, ``_shared``).
        2. Path-traversal / separator (``/``, ``\\``, ``..``).
        3. Regex ``^[a-z][a-z0-9_-]{0,63}$`` — lowercase start, then
           lowercase alphanumerics / dash / underscore, length ≤ 64.

    No silent normalization. If callers want auto-lowercasing, they must
    do it explicitly before calling.
    """
    if name in _RESERVED_NAMES:
        raise EjectError(
            f"reserved destination name not allowed: {name!r}"
        )
    if "/" in name or "\\" in name or ".." in name:
        raise EjectError(
            f"destination name contains path separator or traversal: {name!r}"
        )
    if not _NAME_RE.match(name):
        raise EjectError(
            f"destination name does not match {_NAME_PATTERN}: {name!r}"
        )
    return name


def resolve_dest(name: str, home: Path | None = None) -> Path:
    """Return ``<home>/.claude/skills/<name>/`` after validating ``name``.

    Does NOT create the directory. The destination is always under the
    user skills root so the ejected skill is discoverable by
    ``inventory.enumerate_skill_paths`` post-apply.
    """
    validated = validate_dest_name(name)
    if home is not None:
        base = Path(home)
    else:
        env = os.environ.get("ASSEMBLE_HOME")
        base = Path(env) if env else Path.home()
    return base / ".claude/skills" / validated


# ---------------------------------------------------------------------------
# Read-only planning
# ---------------------------------------------------------------------------


def dry_run_plan(
    bundle_name: str,
    dest_name: str,
    home: Path | None = None,
) -> EjectPlan:
    """Build an :class:`EjectPlan` describing the copy that ``apply_eject``
    would perform. Pure read-only — does not mutate anything on disk.

    Walks ``src.rglob("*")`` and filters to files only (directories are
    accumulated implicitly by ``shutil.copytree`` later). ``total_bytes``
    sums each file's ``stat().st_size``. Warnings include a notice when
    the destination already contains a ``SKILL.md`` (overwrite would clobber
    the user's prior edits unless they used the backup branch).
    """
    src = resolve_source(bundle_name, home=home)
    dest = resolve_dest(dest_name, home=home)
    files: list[Path] = []
    total_bytes = 0
    for p in sorted(src.rglob("*")):
        if p.is_file():
            files.append(p)
            try:
                total_bytes += p.stat().st_size
            except OSError:
                # Unreadable file → surface via warning rather than crash.
                # apply_eject will fail loudly via shutil.copytree if the
                # condition persists.
                pass
    dest_exists = dest.is_dir()
    warnings: list[str] = []
    if dest_exists and (dest / "SKILL.md").is_file():
        warnings.append("destination already contains a SKILL.md")
    return EjectPlan(
        src=src,
        dest=dest,
        bundle_name=bundle_name,
        files=files,
        total_bytes=total_bytes,
        dest_exists=dest_exists,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Side-effect: atomic apply
# ---------------------------------------------------------------------------


def apply_eject(plan: EjectPlan, *, overwrite: bool = False) -> EjectPlan:
    """Copy ``plan.src`` to ``plan.dest`` atomically. Return the same plan.

    7-step atomicity contract (invariant; see spec § "Atomic apply"):

    1. Create temp dir under same parent as dest:
       ``<dest>.tmp.<pid>.<rand>`` (rand = ``secrets.token_hex(4)``).
    2. ``shutil.copytree(src, temp_dir/<dest.name>)`` with
       ``copy_function=shutil.copy2`` (preserves mtime/permissions, not
       ACL/xattr — Linux/macOS scope).
    3. If dest exists and ``overwrite=False`` → ``EjectError``. Caller is
       expected to have asked the user via ``AskUserQuestion`` first.
    4. If dest exists and ``overwrite=True`` → atomic rename of dest to
       ``<dest>.bak.<int(time.time())>`` first. The ``.bak.<ts>`` survivor
       is intentionally NOT auto-cleaned; user removes manually.
    5. ``os.rename(temp_dir/<dest.name>, dest)`` — single inode swap on the
       same filesystem.
    6. Cleanup temp dir via ``shutil.rmtree(..., ignore_errors=True)``.
    7. On any exception during steps 1-5: cleanup the temp dir then re-raise.

    The ``inner`` directory inside the temp dir is named ``dest.name`` so
    step 5 can rename it directly to ``dest`` without an intermediate
    move. This keeps step 5 a single ``os.rename`` (atomic on a single
    filesystem).
    """
    src = plan.src
    dest = plan.dest
    parent = dest.parent
    parent.mkdir(parents=True, exist_ok=True)

    inner_name = dest.name
    temp_dir = parent / f"{dest.name}.tmp.{os.getpid()}.{secrets.token_hex(4)}"

    try:
        # Step 1: create temp dir under same parent (same filesystem → atomic rename).
        temp_dir.mkdir(parents=True, exist_ok=False)

        # Step 2: full-tree copy, byte-faithful, preserves mtime/permissions.
        shutil.copytree(
            src,
            temp_dir / inner_name,
            copy_function=shutil.copy2,
        )

        # Step 3: dest exists + overwrite=False → refuse (caller must confirm).
        dest_currently_exists = dest.exists()
        if dest_currently_exists and not overwrite:
            raise EjectError(
                f"destination already exists: {dest} "
                "(pass overwrite=True after user confirmation)"
            )

        # Step 4: dest exists + overwrite=True → backup then proceed.
        if dest_currently_exists and overwrite:
            backup = parent / f"{dest.name}.bak.{int(time.time())}"
            os.rename(dest, backup)

        # Step 5: single-inode swap, atomic on same filesystem.
        os.rename(temp_dir / inner_name, dest)

    except BaseException:
        # Step 7: any failure during 1-5 → wipe temp tree and re-raise.
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    # Step 6: success path cleanup of the now-empty wrapper temp dir.
    shutil.rmtree(temp_dir, ignore_errors=True)
    return plan
