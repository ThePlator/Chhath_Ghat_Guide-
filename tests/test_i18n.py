import pytest

from ghat_guide.i18n import LANGUAGE_LABELS, STRINGS, t


def test_fallback_to_hindi():
    assert t("reading", "bho") == t("reading", "hi")


def test_own_language_used_when_present():
    assert t("unclear_title", "hi") == "साफ़ नहीं पढ़ पाए"
    assert t("tab_notice", "mai") != t("tab_notice", "hi")


def test_formatting():
    assert "ollama pull x" in t("health_model_missing", "hi", cmds="ollama pull x")


def test_missing_key_raises():
    with pytest.raises(KeyError):
        t("no_such_key")


def test_other_languages_only_use_known_keys():
    for lang in ("bho", "mai"):
        assert set(STRINGS[lang]) <= set(STRINGS["hi"]), lang


def test_labels_cover_languages():
    assert set(LANGUAGE_LABELS) == set(STRINGS)
