"""Organiser-editable emergency card (config/emergency.yaml, HLD §8.1)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config" / "emergency.yaml"


@dataclass(frozen=True)
class Contact:
    label: str
    phone: str = ""
    where: str = ""


@dataclass(frozen=True)
class EmergencyInfo:
    message: dict[str, str] = field(default_factory=dict)
    contacts: tuple[Contact, ...] = ()

    def message_for(self, lang: str) -> str | None:
        return self.message.get(lang) or self.message.get("hi")


def load_emergency(path: str | Path | None = None) -> EmergencyInfo:
    """A missing or broken file must never take the app down: fall back to empty."""
    p = Path(path) if path else DEFAULT_PATH
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        log.warning("emergency card not loaded: %s", type(e).__name__)
        return EmergencyInfo()
    if not isinstance(raw, dict):
        return EmergencyInfo()

    message = raw.get("message") or {}
    message = {str(k): str(v).strip() for k, v in message.items() if v} if isinstance(message, dict) else {}

    contacts = []
    for c in raw.get("contacts") or []:
        if isinstance(c, dict) and str(c.get("label") or "").strip():
            contacts.append(
                Contact(
                    label=str(c["label"]).strip(),
                    phone=str(c.get("phone") or "").strip(),
                    where=str(c.get("where") or "").strip(),
                )
            )
    return EmergencyInfo(message=message, contacts=tuple(contacts))
