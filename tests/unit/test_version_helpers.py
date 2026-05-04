"""Tests for `server.version_helpers`.

Covers two pure-function surfaces:

  1. ``bump_semver`` — semver bump rules (patch/minor/major/prerelease).
  2. ``detect_version_format`` + ``read_version`` — filesystem-priority
     version-file detection + read.

Format-detection tests use real files inside ``tempfile.TemporaryDirectory``
(no mocks) per the V4 ★ bundle convention (see ``feedback_no_mocks_for_db_or_git``).
"""

import json
import tempfile
from pathlib import Path

import pytest

from server.version_helpers import (
    bump_semver,
    compute_next,
    detect_version_format,
    read_version,
)


# ---------------------------------------------------------------------------
# bump_semver
# ---------------------------------------------------------------------------


def test_bump_semver_patch():
    assert bump_semver("0.16.0", "patch") == "0.16.1"


def test_bump_semver_minor():
    assert bump_semver("0.16.0", "minor") == "0.17.0"


def test_bump_semver_major():
    assert bump_semver("0.16.0", "major") == "1.0.0"


def test_bump_semver_prerelease_fresh():
    """No prior `-rc` suffix → append `-rc.1`."""
    assert bump_semver("0.16.0", "prerelease") == "0.16.0-rc.1"


def test_bump_semver_prerelease_increment():
    """Existing `-rc.<N>` suffix → increment N."""
    assert bump_semver("0.16.0-rc.2", "prerelease") == "0.16.0-rc.3"


def test_bump_semver_prerelease_increment_high_n():
    """Multi-digit rc counter increments correctly."""
    assert bump_semver("1.2.3-rc.10", "prerelease") == "1.2.3-rc.11"


def test_bump_semver_unknown_kind_raises():
    with pytest.raises(ValueError):
        bump_semver("0.16.0", "rocket")


def test_bump_semver_malformed_input_raises():
    with pytest.raises(ValueError):
        bump_semver("not.a.version", "patch")


def test_bump_semver_patch_resets_when_prerelease_present():
    """Patch bump on an `-rc.N` version drops the prerelease and bumps patch.

    Standard semver rule: ``1.2.3-rc.5`` → patch → ``1.2.4``.
    """
    assert bump_semver("1.2.3-rc.5", "patch") == "1.2.4"


def test_bump_semver_minor_zeroes_patch():
    assert bump_semver("1.2.3", "minor") == "1.3.0"


def test_bump_semver_major_zeroes_minor_and_patch():
    assert bump_semver("1.2.3", "major") == "2.0.0"


def test_compute_next_is_bump_semver_alias():
    """`compute_next` is documented as a convenience wrapper — verify parity."""
    assert compute_next("0.16.0", "patch") == bump_semver("0.16.0", "patch")
    assert compute_next("0.16.0", "prerelease") == bump_semver("0.16.0", "prerelease")


# ---------------------------------------------------------------------------
# detect_version_format + read_version
# ---------------------------------------------------------------------------


def test_detect_version_format_version_file_wins():
    """Plain VERSION takes priority over package.json + pyproject.toml."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "VERSION").write_text("0.16.0\n", encoding="utf-8")
        (root / "package.json").write_text(
            json.dumps({"name": "x", "version": "9.9.9"}),
            encoding="utf-8",
        )
        (root / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "8.8.8"\n',
            encoding="utf-8",
        )
        fmt, fp, current = detect_version_format(root)
        assert fmt == "version-file"
        assert fp == root / "VERSION"
        assert current == "0.16.0"


def test_detect_version_format_package_json_fallback():
    """package.json wins over pyproject.toml when no VERSION."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "package.json").write_text(
            json.dumps({"name": "x", "version": "1.2.3"}),
            encoding="utf-8",
        )
        (root / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "8.8.8"\n',
            encoding="utf-8",
        )
        fmt, fp, current = detect_version_format(root)
        assert fmt == "package.json"
        assert fp == root / "package.json"
        assert current == "1.2.3"


def test_detect_version_format_pyproject_pep621():
    """PEP 621 [project] table is recognized."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "2.5.0"\n',
            encoding="utf-8",
        )
        fmt, fp, current = detect_version_format(root)
        assert fmt == "pyproject-pep621"
        assert fp == root / "pyproject.toml"
        assert current == "2.5.0"


def test_detect_version_format_pyproject_poetry():
    """[tool.poetry] table is recognized when no [project] table is present."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "demo"\nversion = "0.4.2"\n',
            encoding="utf-8",
        )
        fmt, fp, current = detect_version_format(root)
        assert fmt == "pyproject-poetry"
        assert fp == root / "pyproject.toml"
        assert current == "0.4.2"


def test_detect_version_format_pep621_wins_over_poetry():
    """If both [project] and [tool.poetry] declared, PEP 621 wins (modern default)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "1.0.0"\n'
            '[tool.poetry]\nname = "x"\nversion = "9.9.9"\n',
            encoding="utf-8",
        )
        fmt, fp, current = detect_version_format(root)
        assert fmt == "pyproject-pep621"
        assert current == "1.0.0"


def test_detect_version_format_none_detected():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "README.md").write_text("# nothing\n", encoding="utf-8")
        fmt, fp, current = detect_version_format(root)
        assert fmt is None
        assert fp is None
        assert current is None


def test_read_version_version_file():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "VERSION"
        target.write_text("3.14.15\n", encoding="utf-8")
        assert read_version("version-file", target) == "3.14.15"


def test_read_version_package_json():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "package.json"
        target.write_text(
            json.dumps({"name": "demo", "version": "7.8.9"}),
            encoding="utf-8",
        )
        assert read_version("package.json", target) == "7.8.9"


def test_read_version_pyproject_pep621():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "pyproject.toml"
        target.write_text(
            '[project]\nname = "demo"\nversion = "5.5.5"\n',
            encoding="utf-8",
        )
        assert read_version("pyproject-pep621", target) == "5.5.5"


def test_read_version_pyproject_poetry():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "pyproject.toml"
        target.write_text(
            '[tool.poetry]\nname = "demo"\nversion = "0.0.1"\n',
            encoding="utf-8",
        )
        assert read_version("pyproject-poetry", target) == "0.0.1"


def test_read_version_missing_file_raises():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        with pytest.raises((FileNotFoundError, OSError)):
            read_version("version-file", root / "VERSION")


def test_read_version_unknown_format_raises():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "VERSION"
        target.write_text("1.0.0\n", encoding="utf-8")
        with pytest.raises(ValueError):
            read_version("klingon-manifest", target)


def test_read_version_package_json_missing_version_raises():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "package.json"
        target.write_text(json.dumps({"name": "no-version"}), encoding="utf-8")
        with pytest.raises((KeyError, ValueError)):
            read_version("package.json", target)


def test_detect_version_format_skips_package_json_without_version():
    """A package.json that lacks `version` should not be picked as the source.

    Falls through to pyproject.toml in priority order.
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "package.json").write_text(
            json.dumps({"name": "no-version"}),
            encoding="utf-8",
        )
        (root / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "4.4.4"\n',
            encoding="utf-8",
        )
        fmt, _, current = detect_version_format(root)
        assert fmt == "pyproject-pep621"
        assert current == "4.4.4"
