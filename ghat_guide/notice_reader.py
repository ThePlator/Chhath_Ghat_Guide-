"""Notice Reader: photo → verbatim text → simple explanation (LLD §3.4).

Two model calls on purpose: the explanation is made only from the text the
model says it read, so every claim can be checked against what the user sees.
The steps are exposed separately so the UI can reuse one transcription when
the user switches language (the image call is the slow one on a laptop CPU).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from . import prompts
from .config import NoticeSettings, OllamaSettings
from .imaging import prepare_image
from .llm import LLMBadOutput, LLMGateway
from .safety import Clarity, clarity_verdict, is_safety_notice, unsupported_numbers

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Transcription:
    text_read: str
    script: str
    clarity: Clarity
    is_safety: bool
    elapsed_s: float


@dataclass(frozen=True)
class Highlights:  # P1 — parsed when the model gives them, not shown yet
    times: list[str] = field(default_factory=list)
    ghat_numbers: list[str] = field(default_factory=list)
    dos: list[str] = field(default_factory=list)
    donts: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Explanation:
    lang: str
    text: str | None  # None when the model failed to give a usable answer
    highlights: Highlights | None
    number_warning: frozenset[str]
    elapsed_s: float


@dataclass(frozen=True)
class NoticeResult:
    transcription: Transcription
    explanation: Explanation | None  # None when the notice is unclear


class NoticeReader:
    def __init__(self, llm: LLMGateway, notice: NoticeSettings, models: OllamaSettings):
        self.llm = llm
        self.s = notice
        self.models = models

    def prepare(self, raw_image: bytes) -> bytes:
        return prepare_image(raw_image, self.s.max_image_px, self.s.jpeg_quality)

    def transcribe(self, image: bytes) -> Transcription:
        """`image` must already be prepared (see prepare())."""
        t0 = time.monotonic()
        try:
            out = self.llm.chat_json(
                model=self.models.vision_model,
                system=prompts.SYS_TRANSCRIBE,
                user=prompts.USER_TRANSCRIBE,
                schema=prompts.TRANSCRIBE_SCHEMA,
                temperature=self.s.transcribe_temperature,
                images=[image],
            )
            text, script, model_clarity = str(out["text_read"]), str(out["script"]), str(out["clarity"])
        except LLMBadOutput:
            log.warning("transcription output unusable; treating as unclear")
            text, script, model_clarity = "", "other", "unclear"

        clarity = clarity_verdict(text, model_clarity, self.s.min_text_chars, self.s.max_unknown_ratio)
        return Transcription(
            text_read=text.strip(),
            script=script,
            clarity=clarity,
            is_safety=is_safety_notice(text),
            elapsed_s=time.monotonic() - t0,
        )

    def explain(self, tr: Transcription, lang: str) -> Explanation | None:
        """Returns None for unclear notices: nothing reliable to explain."""
        if tr.clarity == "unclear":
            return None
        t0 = time.monotonic()
        try:
            out = self.llm.chat_json(
                model=self.models.text_model,
                system=prompts.sys_explain(lang),
                user=prompts.user_explain(tr.text_read),
                schema=prompts.EXPLAIN_SCHEMA,
                temperature=self.s.explain_temperature,
            )
        except LLMBadOutput:
            log.warning("explanation output unusable")
            return Explanation(lang, None, None, frozenset(), time.monotonic() - t0)

        text = str(out["explanation"]).strip() or None
        return Explanation(
            lang=lang,
            text=text,
            highlights=_highlights(out.get("highlights")),
            number_warning=frozenset(unsupported_numbers(text or "", tr.text_read)),
            elapsed_s=time.monotonic() - t0,
        )

    def read(self, raw_image: bytes, lang: str) -> NoticeResult:
        tr = self.transcribe(self.prepare(raw_image))
        return NoticeResult(tr, self.explain(tr, lang))


def _highlights(raw) -> Highlights | None:
    if not isinstance(raw, dict):
        return None

    def strs(key):
        v = raw.get(key) or []
        return [str(x) for x in v] if isinstance(v, list) else []

    h = Highlights(strs("times"), strs("ghat_numbers"), strs("dos"), strs("donts"))
    return h if any((h.times, h.ghat_numbers, h.dos, h.donts)) else None
