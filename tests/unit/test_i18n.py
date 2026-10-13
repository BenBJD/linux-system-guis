"""Tests for the localisation framework and consistency of every app's string table."""

import importlib.util
import re
import string
import warnings
from pathlib import Path

import pytest

from linux_gui_core import i18n
from linux_gui_core.i18n import StringTable, detect_locale, locale_fallback_chain, normalise_locale

ROOT = Path(__file__).resolve().parents[2]
STRING_MODULES = sorted(
    [*ROOT.glob("apps/*/src/*/strings.py"), ROOT / "packages/core/src/linux_gui_core/strings.py"]
)
# Matches tr("key") / tr('key', ...) with a literal key.
TR_CALL = re.compile(r"""\btr\(\s*["']([A-Za-z0-9_.]+)["']""")


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(f"_strings_{path.parent.name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _placeholders(text: str) -> set[str]:
    return {field for _, field, _, _ in string.Formatter().parse(text) if field}


# ---------------------------------------------------------------- framework ---

@pytest.fixture(autouse=True)
def _reset_locale():
    i18n.set_locale(None)
    yield
    i18n.set_locale(None)


def test_normalise_locale():
    assert normalise_locale("en_GB.UTF-8") == "en_GB"
    assert normalise_locale("de_DE@euro") == "de_DE"
    assert normalise_locale("pt-BR") == "pt_BR"
    assert normalise_locale("fr_FR:en_GB") == "fr_FR"


def test_detect_locale_priority_and_posix():
    assert detect_locale({"LANG": "de_DE.UTF-8"}) == "de_DE"
    assert detect_locale({"LINUX_SYSTEM_GUIS_LANG": "fr", "LANG": "de_DE.UTF-8"}) == "fr"
    assert detect_locale({"LC_ALL": "C", "LANG": "es_ES.UTF-8"}) == "es_ES"
    assert detect_locale({}) == "en"


def test_fallback_chain():
    assert locale_fallback_chain("pt_BR") == ["pt_BR", "pt", "en"]
    assert locale_fallback_chain("en") == ["en"]


def test_string_table_fallback_and_format():
    table = StringTable({
        "en": {"hello": "Hello {name}", "bye": "Goodbye", "braces": "{literal}"},
        "de": {"hello": "Hallo {name}"},
    })
    i18n.set_locale("de_AT")
    assert table("hello", name="Ben") == "Hallo Ben"   # de_AT -> de
    assert table("bye") == "Goodbye"                   # missing -> en
    assert table("braces") == "{literal}"              # no kwargs -> no formatting
    assert table.missing_keys("de") == {"bye", "braces"}
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        assert table("nope") == "nope"


def test_string_table_requires_default_locale():
    with pytest.raises(ValueError):
        StringTable({"de": {}})


# ----------------------------------------------------- per-app string tables ---

@pytest.mark.parametrize("path", STRING_MODULES, ids=lambda p: p.parent.name)
def test_string_module_structure(path):
    module = _load(path)
    assert "en" in module.STRINGS
    assert isinstance(module.tr, StringTable)
    en = module.STRINGS["en"]
    assert en and all(isinstance(k, str) and isinstance(v, str) for k, v in en.items())

    # Translations must not invent keys or change format placeholders.
    for code, table in module.STRINGS.items():
        if code == "en":
            continue
        assert set(table) <= set(en), f"{code} defines keys not present in en"
        for key, text in table.items():
            assert _placeholders(text) == _placeholders(en[key]), f"{code}:{key} placeholders differ"


@pytest.mark.parametrize("path", STRING_MODULES, ids=lambda p: p.parent.name)
def test_all_used_keys_are_defined(path):
    """Every literal tr("key") call in the package must exist in its English table."""
    en = _load(path).STRINGS["en"]
    missing = {}
    for source in path.parent.rglob("*.py"):
        if source.name in ("strings.py", "i18n.py"):
            continue
        for key in TR_CALL.findall(source.read_text(encoding="utf-8")):
            if key not in en:
                missing.setdefault(source.name, set()).add(key)
    assert not missing, f"Undefined string keys: {missing}"
