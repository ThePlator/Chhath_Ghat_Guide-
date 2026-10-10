"""Safety checks on what the model read and wrote (LLD §3.3).

- is_safety_notice(): water / barricade / emergency notices get their original
  text shown first, never only a summary.
- clarity_verdict(): "unclear" is a first-class result, not an error.
- unsupported_numbers(): catches times or ghat numbers the explanation
  invented (numbers that are not in the text that was read).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

Clarity = Literal["clear", "partial", "unclear"]

UNKNOWN_MARK = "[?]"
_NUKTA = "़"
_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

# Devanagari terms are matched as substrings of the normalised text, so each
# term is chosen not to sit inside a common harmless word. In particular:
#   "डूब" alone would match "डूबते सूर्य" (the setting sun of Sandhya Arghya),
#   "मना" alone would match "मनाया" (celebrated).
SAFETY_TERMS_DEVANAGARI = (
    # deep water / drowning
    "गहरा", "गहरे", "गहराई", "डूबने", "डूबना", "बहाव", "तेज धारा",
    # danger / warning
    "खतरा", "खतरे", "खतरनाक", "सावधान", "चेतावनी",
    # barricades / restricted
    "बैरिकेड", "बेरिकेड", "घेराबंदी", "प्रतिबंधित", "वर्जित", "निषेध", "मना है", "न जाएं", "न जायें",
    # emergency / help
    "आपात", "आपातकाल", "पुलिस", "गोताखोर", "एंबुलेंस", "एम्बुलेंस", "खोया", "खोई", "भगदड़",
)
SAFETY_TERMS_LATIN = (
    "danger", "dangerous", "deep", "drown", "warning", "caution", "barricade", "prohibited",
    "restricted", "no entry", "do not", "emergency", "police", "lost", "ambulance", "ndrf", "sdrf",
)

_LATIN_RE = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in SAFETY_TERMS_LATIN) + r")\b")
_NUMBER_RE = re.compile(r"\d+")


def normalise(text: str) -> str:
    """NFC, nukta removed, Devanagari digits → ASCII, Latin lower-cased, spaces collapsed."""
    text = unicodedata.normalize("NFD", text or "").replace(_NUKTA, "")
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_DEVANAGARI_DIGITS).lower()
    return " ".join(text.split())


_TERMS_NORMALISED = tuple(normalise(t) for t in SAFETY_TERMS_DEVANAGARI)


def is_safety_notice(text_read: str) -> bool:
    t = normalise(text_read)
    if not t:
        return False
    return any(term in t for term in _TERMS_NORMALISED) or bool(_LATIN_RE.search(t))


def clarity_verdict(
    text_read: str,
    model_clarity: str,
    min_chars: int = 8,
    max_unknown_ratio: float = 0.30,
) -> Clarity:
    text = (text_read or "").strip()
    unknown = text.count(UNKNOWN_MARK)
    words = max(1, len(text.split()))
    if model_clarity == "unclear" or len(text) < min_chars or unknown / words > max_unknown_ratio:
        return "unclear"
    if model_clarity == "partial" or unknown:
        return "partial"
    return "clear"


def numbers_in(text: str) -> set[str]:
    return {n.lstrip("0") or "0" for n in _NUMBER_RE.findall(normalise(text))}


def unsupported_numbers(explanation: str, text_read: str) -> set[str]:
    """Numbers in the explanation that never appear in the text that was read."""
    return numbers_in(explanation) - numbers_in(text_read)
