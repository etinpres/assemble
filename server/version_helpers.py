"""Pure helpers for shipper ★ Step 2 (semver bump + version-file detection).

The shipper bundle's version-bump step never executes Bash and never writes
to disk through this module — these are *pure* functions that compute the
next version string and locate the file that holds the current one. The
sub-agent prompt does the actual ``Edit`` afterwards.

Responsibilities split across four functions:

  - :func:`bump_semver`            — semver arithmetic.
  - :func:`detect_version_format`  — filesystem-priority format detector.
  - :func:`read_version`           — extract the version string from a known
                                     format file.
  - :func:`compute_next`           — convenience wrapper around ``bump_semver``
                                     (kept as a separate symbol for plan
                                     compliance).

Format priority (highest first) when multiple are present in a repo:

  1. ``VERSION``         — plain-text single-line file (gstack-family default)
  2. ``package.json``    — Node.js (must contain a top-level ``version`` key)
  3. ``pyproject.toml``  — Python; PEP 621 ``[project]`` table wins over the
                           legacy ``[tool.poetry]`` table when both exist.

MVP scope deliberately excludes ``Cargo.toml``, ``Gemfile``, ``go.mod`` and
similar formats — the shipper SECURITY.md / SKILL.md document that those
require a manual edit before invoking shipper. Adding new formats is purely
additive: extend ``_FORMAT_PRIORITY`` + ``read_version`` dispatcher.

Korean characters and other non-ASCII content are tolerated everywhere —
``ensure_ascii=False`` is the project standard.
"""

import json
import re
from pathlib import Path
from typing import Optional

# Try Python 3.11+ stdlib first, fall back to the ``tomli`` backport.
# When neither is available, raise a diagnosable error at import time rather
# than letting a downstream pyproject.toml read fail with an obscure
# ``ModuleNotFoundError``. Spike VIII tests assume 3.10+ with ``tomli``
# transitively available via pytest; declare the requirement explicitly here.
try:  # pragma: no cover - import-path branch, both ends covered by tests
    import tomllib as _toml
except ModuleNotFoundError:  # pragma: no cover
    try:
        import tomli as _toml  # type: ignore[no-redef]
    except ModuleNotFoundError as _exc:  # pragma: no cover
        raise RuntimeError(
            "pyproject.toml support requires Python 3.11+ (stdlib tomllib) "
            "OR the `tomli` backport. Install with `pip install tomli` "
            "or upgrade to Python 3.11+."
        ) from _exc


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Strict semver core: ``MAJOR.MINOR.PATCH`` with optional ``-rc.<N>`` suffix.
# We deliberately *do not* support arbitrary semver prerelease/build metadata
# (``-beta.1+exp.sha.5114f85``) — the spec restricts MVP to the ``-rc.<N>``
# convention. Future expansion is additive (new release_kind values + a
# wider regex).
_SEMVER_CORE_RE = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:-rc\.(?P<rc>\d+))?$"
)

_VALID_KINDS = {"patch", "minor", "major", "prerelease"}

# Filesystem-priority dispatch order. Each entry: (filename, format-tag,
# detector-function-name). Detectors return the version string or ``None``
# if the file is present but does not declare a version in the expected
# location (e.g. ``package.json`` without a ``version`` key, or a
# ``pyproject.toml`` without either a PEP 621 or Poetry table).
_FORMAT_PRIORITY: tuple[tuple[str, str], ...] = (
    ("VERSION", "version-file"),
    ("package.json", "package.json"),
    # ``pyproject.toml`` resolves to one of two format tags
    # (``pyproject-pep621`` or ``pyproject-poetry``) — handled inline in
    # ``detect_version_format`` rather than via this table.
    ("pyproject.toml", "_pyproject"),
)


# ---------------------------------------------------------------------------
# Semver bump
# ---------------------------------------------------------------------------


def bump_semver(current: str, kind: str) -> str:
    """Return ``current`` bumped per ``kind``.

    Args:
        current: A version string in ``MAJOR.MINOR.PATCH`` form, optionally
            suffixed with ``-rc.<N>``. Anything else raises ``ValueError``.
        kind: One of ``patch``/``minor``/``major``/``prerelease``.

    Bump rules:
        * ``patch``       — ``X.Y.Z`` → ``X.Y.(Z+1)``. Any ``-rc.N`` suffix
                            on ``current`` is dropped (standard semver: a
                            patch release is the next *stable* version after
                            the prerelease line).
        * ``minor``       — ``X.Y.Z`` → ``X.(Y+1).0``. Suffix dropped.
        * ``major``       — ``X.Y.Z`` → ``(X+1).0.0``. Suffix dropped.
        * ``prerelease``  — if ``current`` ends in ``-rc.N``, return the
                            same core with ``-rc.(N+1)``. Otherwise append
                            ``-rc.1`` to ``current``.

    Raises:
        ValueError: malformed ``current`` or unknown ``kind``.

    Examples:
        >>> bump_semver("0.16.0", "patch")
        '0.16.1'
        >>> bump_semver("0.16.0", "prerelease")
        '0.16.0-rc.1'
        >>> bump_semver("0.16.0-rc.2", "prerelease")
        '0.16.0-rc.3'
        >>> bump_semver("1.2.3-rc.5", "patch")
        '1.2.4'
    """
    if kind not in _VALID_KINDS:
        raise ValueError(
            f"unknown release_kind: {kind!r} (expected one of {sorted(_VALID_KINDS)})"
        )

    m = _SEMVER_CORE_RE.match(current.strip())
    if not m:
        raise ValueError(
            f"malformed semver: {current!r} "
            "(expected MAJOR.MINOR.PATCH or MAJOR.MINOR.PATCH-rc.N)"
        )

    major = int(m.group("major"))
    minor = int(m.group("minor"))
    patch = int(m.group("patch"))
    rc_raw = m.group("rc")
    rc = int(rc_raw) if rc_raw is not None else None

    if kind == "patch":
        return f"{major}.{minor}.{patch + 1}"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    if kind == "major":
        return f"{major + 1}.0.0"
    # kind == "prerelease"
    if rc is None:
        return f"{major}.{minor}.{patch}-rc.1"
    return f"{major}.{minor}.{patch}-rc.{rc + 1}"


def compute_next(current: str, kind: str) -> str:
    """Convenience alias for :func:`bump_semver`.

    Kept as a separate symbol so call-sites that read more naturally as
    "compute the next version" stay readable, and so the public API matches
    the Spike IX plan literally. Behaviorally identical to ``bump_semver``.

    Note: the Spike IX plan listed a third ``prerelease_counter=0`` argument;
    that parameter proved redundant because the counter is unambiguously
    parsed from ``current``'s ``-rc.<N>`` suffix per spec § Step 2. The
    deviation is intentional — re-introducing the parameter is purely
    additive and backward-compatible if a future override is needed.
    """
    return bump_semver(current, kind)


# ---------------------------------------------------------------------------
# Format detection + read
# ---------------------------------------------------------------------------


def _read_package_json_version(path: Path) -> Optional[str]:
    """Return ``data["version"]`` or ``None`` if the key is missing/non-string.

    A malformed JSON file raises :class:`json.JSONDecodeError` so the caller
    can surface it as a hard error rather than silently picking a different
    format.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    version = data.get("version")
    if isinstance(version, str) and version:
        return version
    return None


def _read_pyproject_version(path: Path) -> tuple[Optional[str], Optional[str]]:
    """Return ``(format_tag, version)`` for a pyproject.toml file.

    ``format_tag`` is ``"pyproject-pep621"`` when the PEP 621 ``[project]``
    table declares a string ``version``, else ``"pyproject-poetry"`` when
    ``[tool.poetry].version`` is set. ``(None, None)`` if neither is present.

    PEP 621 wins when both exist — that is the upstream-blessed metadata
    location and matches modern Poetry 2.x conventions.
    """
    with path.open("rb") as f:
        data = _toml.load(f)

    project = data.get("project")
    if isinstance(project, dict):
        version = project.get("version")
        if isinstance(version, str) and version:
            return "pyproject-pep621", version

    tool = data.get("tool")
    if isinstance(tool, dict):
        poetry = tool.get("poetry")
        if isinstance(poetry, dict):
            version = poetry.get("version")
            if isinstance(version, str) and version:
                return "pyproject-poetry", version

    return None, None


def detect_version_format(
    repo_root: Path,
) -> tuple[Optional[str], Optional[Path], Optional[str]]:
    """Return ``(format, file_path, current_version)`` for the highest-priority
    version source under ``repo_root``.

    Priority order: ``VERSION`` → ``package.json`` → ``pyproject.toml``
    (PEP 621 wins over Poetry inside the same file).

    A *syntactically valid* file that exists but lacks a usable version
    declaration (e.g. ``package.json`` without ``"version"`` or
    ``pyproject.toml`` with neither PEP 621 nor Poetry version) is *skipped*
    so the next format in the priority chain gets a chance — this matches
    user expectation when a repo has both an autogenerated ``package.json``
    for tooling and a ``pyproject.toml`` as the actual version source of
    truth.

    Malformed files propagate the parser exception (``json.JSONDecodeError``
    for ``package.json``; ``tomllib``/``tomli`` decode error for
    ``pyproject.toml``). Silent skipping on syntax errors would mask real
    bugs — the caller is responsible for surfacing the error.

    Returns ``(None, None, None)`` when no recognized format is detected.
    """
    for filename, tag in _FORMAT_PRIORITY:
        candidate = repo_root / filename

        if not candidate.is_file():
            continue

        if tag == "version-file":
            text = candidate.read_text(encoding="utf-8").strip()
            if text:
                return tag, candidate, text
            continue

        if tag == "package.json":
            version = _read_package_json_version(candidate)
            if version is not None:
                return tag, candidate, version
            continue

        if tag == "_pyproject":
            fmt, version = _read_pyproject_version(candidate)
            if fmt is not None and version is not None:
                return fmt, candidate, version
            continue

    return None, None, None


def read_version(format: str, file_path: Path) -> str:
    """Return the current version string from ``file_path`` per ``format``.

    Args:
        format: One of ``"version-file"``, ``"package.json"``,
            ``"pyproject-pep621"``, ``"pyproject-poetry"``.
        file_path: Absolute path to the version-bearing file.

    Raises:
        FileNotFoundError: ``file_path`` does not exist.
        ValueError:        unknown ``format``, or the file exists but does
                           not declare a version in the expected location.
    """
    if format == "version-file":
        text = file_path.read_text(encoding="utf-8").strip()
        if not text:
            raise ValueError(f"VERSION file is empty: {file_path}")
        return text

    if format == "package.json":
        version = _read_package_json_version(file_path)
        if version is None:
            raise ValueError(f"package.json missing 'version' key: {file_path}")
        return version

    if format == "pyproject-pep621":
        with file_path.open("rb") as f:
            data = _toml.load(f)
        project = data.get("project") if isinstance(data, dict) else None
        if not isinstance(project, dict):
            raise ValueError(
                f"pyproject.toml missing [project] table: {file_path}"
            )
        version = project.get("version")
        if not isinstance(version, str) or not version:
            raise ValueError(
                f"pyproject.toml [project].version not a non-empty string: {file_path}"
            )
        return version

    if format == "pyproject-poetry":
        with file_path.open("rb") as f:
            data = _toml.load(f)
        tool = data.get("tool") if isinstance(data, dict) else None
        poetry = tool.get("poetry") if isinstance(tool, dict) else None
        if not isinstance(poetry, dict):
            raise ValueError(
                f"pyproject.toml missing [tool.poetry] table: {file_path}"
            )
        version = poetry.get("version")
        if not isinstance(version, str) or not version:
            raise ValueError(
                f"pyproject.toml [tool.poetry].version not a non-empty string: {file_path}"
            )
        return version

    raise ValueError(
        f"unknown version format: {format!r} "
        "(expected version-file / package.json / pyproject-pep621 / pyproject-poetry)"
    )
