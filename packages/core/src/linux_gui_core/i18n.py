"""Lightweight localisation framework shared by every Linux System GUIs app.

Each app ships a ``strings.py`` module that defines its user-facing text as plain
Python dictionaries, keyed first by locale code and then by a stable string key::

    EN: dict[str, str] = {
        "window_title": "fstab Editor",
        "msg_saved": "Saved {path} successfully.",
    }

    STRINGS: dict[str, dict[str, str]] = {
        "en": EN,
        # "de": DE,   # <- future translations are registered here
    }

    tr = StringTable(STRINGS)

UI code then looks strings up by key::

    self.setWindowTitle(tr("window_title"))
    QMessageBox.information(self, tr("title_success"), tr("msg_saved", path=path))

Locale resolution
-----------------
The active locale is detected once from the environment, checking (in order)
``LINUX_SYSTEM_GUIS_LANG``, ``LC_ALL``, ``LC_MESSAGES``, ``LANGUAGE`` and ``LANG``.
It can be overridden programmatically with :func:`set_locale` (call this before
any windows are constructed).

Lookups fall back progressively, e.g. ``pt_BR`` -> ``pt`` -> ``en``, so a partial
translation never breaks the UI: any key missing from the active language is
served from English.

Formatting rules
----------------
* Placeholders use ``str.format`` syntax: ``"Deleted {path}"``.
* Formatting is only applied when keyword arguments are passed, so strings without
  placeholders may contain literal braces freely. Strings that *do* take arguments
  must escape literal braces as ``{{`` / ``}}``.
* Qt mnemonics/escapes are kept verbatim in the string (``"Validate && Save"``).
"""

from __future__ import annotations

import os
import warnings
from collections.abc import Iterable, Mapping

DEFAULT_LOCALE = "en"
LOCALE_ENV_OVERRIDE = "LINUX_SYSTEM_GUIS_LANG"
_LOCALE_ENV_VARS = (LOCALE_ENV_OVERRIDE, "LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG")

_active_locale: str | None = None


def normalise_locale(value: str) -> str:
    """Normalise a POSIX-style locale value (``en_GB.UTF-8@euro``) to ``en_GB``."""
    code = value.split(":")[0]  # LANGUAGE may be a colon-separated priority list
    code = code.split(".")[0].split("@")[0].strip()
    return code.replace("-", "_")


def detect_locale(environ: Mapping[str, str] | None = None) -> str:
    """Detect the preferred UI locale from environment variables."""
    env = os.environ if environ is None else environ
    for var in _LOCALE_ENV_VARS:
        raw = env.get(var, "")
        if not raw:
            continue
        code = normalise_locale(raw)
        if code and code.upper() not in ("C", "POSIX"):
            return code
    return DEFAULT_LOCALE


def get_locale() -> str:
    """Return the active locale code, detecting it from the environment on first use."""
    global _active_locale
    if _active_locale is None:
        _active_locale = detect_locale()
    return _active_locale


def set_locale(code: str | None) -> None:
    """Override the active locale (``None`` re-enables environment detection).

    Call before constructing any windows; already-rendered widgets are not re-translated.
    """
    global _active_locale
    _active_locale = normalise_locale(code) if code else None


def locale_fallback_chain(code: str, default: str = DEFAULT_LOCALE) -> list[str]:
    """Return lookup order for a locale, e.g. ``pt_BR`` -> ``["pt_BR", "pt", "en"]``."""
    chain: list[str] = []
    for candidate in (code, code.split("_")[0], default):
        if candidate and candidate not in chain:
            chain.append(candidate)
    return chain


class StringTable:
    """Locale-aware lookup over a ``{locale: {key: text}}`` dictionary."""

    def __init__(self, translations: Mapping[str, Mapping[str, str]], default_locale: str = DEFAULT_LOCALE):
        if default_locale not in translations:
            raise ValueError(f"String table is missing the default locale {default_locale!r}")
        self._translations = translations
        self._default_locale = default_locale

    @property
    def default_locale(self) -> str:
        return self._default_locale

    @property
    def available_locales(self) -> list[str]:
        return sorted(self._translations)

    def keys(self) -> set[str]:
        """All keys defined for the default locale (the canonical key set)."""
        return set(self._translations[self._default_locale])

    def missing_keys(self, locale_code: str) -> set[str]:
        """Keys present in the default locale but not yet translated for ``locale_code``."""
        return self.keys() - set(self._translations.get(locale_code, {}))

    def __contains__(self, key: object) -> bool:
        return key in self._translations[self._default_locale]

    def lookup(self, key: str, locale_code: str | None = None) -> str:
        """Return the raw (unformatted) string for ``key`` with locale fallback."""
        for code in locale_fallback_chain(locale_code or get_locale(), self._default_locale):
            table = self._translations.get(code)
            if table is not None and key in table:
                return table[key]
        warnings.warn(f"Missing localisation string for key {key!r}", stacklevel=3)
        return key

    def __call__(self, key: str, /, **kwargs: object) -> str:
        """Look up ``key`` and apply ``str.format(**kwargs)`` when arguments are given."""
        text = self.lookup(key)
        return text.format(**kwargs) if kwargs else text

    def __getitem__(self, key: str) -> str:
        return self.lookup(key)

    def many(self, keys: Iterable[str]) -> list[str]:
        """Convenience for translating lists such as table headers."""
        return [self.lookup(k) for k in keys]
