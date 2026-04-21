"""Locale-aware string loader.

Reads ASSEMBLE_LOCALE env var (default: "en"). Falls back to "en" if the
requested locale file is missing or a key is absent in the localized file.

Usage:
    from server.i18n import t
    t("menu.skip.label")                # -> "skip"
    t("progress.wrap_up", rid="abc", m=1, s=12, done=2, skipped=0,
      manual=0, tools="my-planner")    # formatted string
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

_I18N_DIR = Path(__file__).resolve().parent.parent / "config" / "i18n"
_DEFAULT_LOCALE = "en"


def _locale() -> str:
    return (os.environ.get("ASSEMBLE_LOCALE") or _DEFAULT_LOCALE).strip() or _DEFAULT_LOCALE


@lru_cache(maxsize=None)
def _load(locale: str) -> dict:
    path = _I18N_DIR / f"{locale}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _lookup(table: dict, dotted_key: str):
    node = table
    for part in dotted_key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def t(key: str, /, **kwargs) -> str:
    """Translate `key` using the active locale, with `en` as fallback.

    If a placeholder substitution fails, returns the raw template rather than
    raising (beginner-safe — skill shouldn't crash on formatting errors).
    """
    locale = _locale()
    value = _lookup(_load(locale), key)
    if value is None and locale != _DEFAULT_LOCALE:
        value = _lookup(_load(_DEFAULT_LOCALE), key)
    if value is None:
        return key  # surface missing key so contributors notice
    if not isinstance(value, str):
        return str(value)
    if not kwargs:
        return value
    try:
        return value.format(**kwargs)
    except (KeyError, IndexError):
        return value


def tdict(key: str) -> dict:
    """Return a dict node (e.g. menu.ask → {"label": ..., "description": ...}).

    Falls back to `en`; returns {} if the key is missing in both.
    """
    locale = _locale()
    value = _lookup(_load(locale), key)
    if not isinstance(value, dict) and locale != _DEFAULT_LOCALE:
        value = _lookup(_load(_DEFAULT_LOCALE), key)
    return value if isinstance(value, dict) else {}


def active_locale() -> str:
    """Expose the currently-active locale (for debugging / status output)."""
    return _locale()
