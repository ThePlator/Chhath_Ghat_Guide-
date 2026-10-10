import pytest

from ghat_guide.config import ConfigError, load_settings


def test_default_settings_file_loads():
    s = load_settings()
    assert s.ollama.vision_model == "gemma3:4b"
    assert s.notice.max_image_px == 1024
    assert s.ui.default_language == "hi"
    assert s.ui.beta_languages == ("bho", "mai")


def test_env_override(monkeypatch):
    monkeypatch.setenv("GHAT_VISION_MODEL", "gemma3:12b")
    assert load_settings().ollama.vision_model == "gemma3:12b"


def test_unknown_key_rejected(tmp_path):
    p = tmp_path / "s.toml"
    p.write_text('[notice]\nmax_image_pxx = 10\n', encoding="utf-8")
    with pytest.raises(ConfigError, match="max_image_pxx"):
        load_settings(p)


def test_bad_language_rejected(tmp_path):
    p = tmp_path / "s.toml"
    p.write_text('[ui]\ndefault_language = "en"\n', encoding="utf-8")
    with pytest.raises(ConfigError):
        load_settings(p)
