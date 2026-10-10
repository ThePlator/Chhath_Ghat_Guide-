"""Load config/settings.toml into typed, read-only settings (LLD §2.1)."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = PROJECT_ROOT / "config" / "settings.toml"
LANGUAGES = ("hi", "bho", "mai")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class OllamaSettings:
    host: str = "http://127.0.0.1:11434"
    vision_model: str = "gemma3:4b"
    text_model: str = "gemma3:4b"
    embed_model: str = "nomic-embed-text"
    keep_alive: str = "30m"
    timeout_s: float = 180
    max_retries: int = 1


@dataclass(frozen=True)
class NoticeSettings:
    max_image_px: int = 1024
    jpeg_quality: int = 85
    transcribe_temperature: float = 0.0
    explain_temperature: float = 0.2
    min_text_chars: int = 8
    max_unknown_ratio: float = 0.30


@dataclass(frozen=True)
class RitualSettings:
    top_k: int = 4
    min_score: float = 0.45
    weight_vector: float = 0.6
    weight_keyword: float = 0.4
    vector_only_min: float = 0.75
    answer_temperature: float = 0.1
    index_path: str = "data/kb_index"
    kb_dir: str = "kb"


@dataclass(frozen=True)
class UISettings:
    default_language: str = "hi"
    beta_languages: tuple[str, ...] = ("bho", "mai")


@dataclass(frozen=True)
class Settings:
    ollama: OllamaSettings = field(default_factory=OllamaSettings)
    notice: NoticeSettings = field(default_factory=NoticeSettings)
    ritual: RitualSettings = field(default_factory=RitualSettings)
    ui: UISettings = field(default_factory=UISettings)


_ENV_OVERRIDES = {
    "GHAT_OLLAMA_HOST": "host",
    "GHAT_VISION_MODEL": "vision_model",
    "GHAT_TEXT_MODEL": "text_model",
    "GHAT_EMBED_MODEL": "embed_model",
}


def _section(cls, raw: dict, name: str):
    data = raw.get(name, {})
    known = set(cls.__dataclass_fields__)
    unknown = set(data) - known
    if unknown:
        raise ConfigError(f"[{name}] unknown keys: {', '.join(sorted(unknown))}")
    if "beta_languages" in data:
        data = {**data, "beta_languages": tuple(data["beta_languages"])}
    return cls(**data)


def load_settings(path: str | os.PathLike | None = None) -> Settings:
    p = Path(path) if path else DEFAULT_PATH
    with open(p, "rb") as f:
        raw = tomllib.load(f)

    ollama_raw = dict(raw.get("ollama", {}))
    for env, key in _ENV_OVERRIDES.items():
        if os.environ.get(env):
            ollama_raw[key] = os.environ[env]
    raw = {**raw, "ollama": ollama_raw}

    settings = Settings(
        ollama=_section(OllamaSettings, raw, "ollama"),
        notice=_section(NoticeSettings, raw, "notice"),
        ritual=_section(RitualSettings, raw, "ritual"),
        ui=_section(UISettings, raw, "ui"),
    )
    if settings.ui.default_language not in LANGUAGES:
        raise ConfigError(f"[ui] default_language must be one of {LANGUAGES}")
    return settings


def project_path(p: str | os.PathLike) -> Path:
    """Resolve a settings path (e.g. kb_dir) against the project root, not the CWD."""
    path = Path(p)
    return path if path.is_absolute() else PROJECT_ROOT / path
