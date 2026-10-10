"""Grounded ritual answers with hard fallbacks (LLD §3.8).

Order of checks:
1. Questions about clock times, this year's dates or ghat logistics never reach
   the model: the notes have no timings by design, and those come from
   official notices.
2. No relevant chunk → "not in my notes".
3. Model says found=false, or cites a chunk it wasn't given → "not in my notes".
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Literal

from .. import prompts
from ..config import OllamaSettings, RitualSettings
from ..llm import LLMBadOutput, LLMGateway
from ..safety import normalise
from .retriever import Hit, Retriever

log = logging.getLogger(__name__)

MAX_QUESTION_CHARS = 300

Outcome = Literal["answered", "not_in_notes", "official_info"]

_OFFICIAL_INFO = re.compile(
    "|".join(
        [
            r"बजे", r"तारीख", r"इस साल", r"इस बार", r"इस वर्ष", r"पार्किंग", r"घाट नंबर", r"कौन सा घाट", r"कौन से घाट",
            r"सूर्योदय कितन", r"सूर्यास्त कितन", r"\b20\d\d\b",
            r"\bparking\b", r"\bdate\b", r"\btime\b", r"\bbaje\b", r"what time",
        ]
    )
)


def asks_for_official_info(question: str) -> bool:
    return bool(_OFFICIAL_INFO.search(normalise(question)))


@dataclass(frozen=True)
class RitualAnswer:
    outcome: Outcome
    answer: str | None  # model answer when outcome == "answered"
    sources: list[Hit] = field(default_factory=list)
    elapsed_s: float = 0.0

    @property
    def found(self) -> bool:
        return self.outcome == "answered"


class RitualHelper:
    def __init__(self, retriever: Retriever, llm: LLMGateway, s: RitualSettings, models: OllamaSettings):
        self.retriever = retriever
        self.llm = llm
        self.s = s
        self.models = models

    @property
    def has_notes(self) -> bool:
        return bool(self.retriever.index.chunks)

    def ask(self, question: str, lang: str) -> RitualAnswer:
        t0 = time.monotonic()
        q = " ".join(question.split())[:MAX_QUESTION_CHARS]
        if not q:
            raise ValueError("empty question")
        if asks_for_official_info(q):
            return RitualAnswer("official_info", None, [], time.monotonic() - t0)

        hits = self.retriever.search(q)
        relevant = [h for h in hits if self.retriever.is_relevant(h)]
        if not relevant:
            return RitualAnswer("not_in_notes", None, [], time.monotonic() - t0)

        context = "\n\n".join(f"[{h.chunk.chunk_id}]\n{h.chunk.section}\n{h.chunk.text}" for h in relevant)
        try:
            out = self.llm.chat_json(
                model=self.models.text_model,
                system=prompts.sys_ritual(lang),
                user=prompts.user_ritual(context, q),
                schema=prompts.RITUAL_SCHEMA,
                temperature=self.s.answer_temperature,
            )
        except LLMBadOutput:
            log.warning("ritual answer output unusable")
            return RitualAnswer("not_in_notes", None, [], time.monotonic() - t0)

        given = {h.chunk.chunk_id: h for h in relevant}
        cited = [str(c) for c in out.get("used_chunk_ids") or []]
        answer = str(out.get("answer") or "").strip()
        if not out.get("found") or not answer or not cited or any(c not in given for c in cited):
            return RitualAnswer("not_in_notes", None, [], time.monotonic() - t0)

        sources = [given[c] for c in dict.fromkeys(cited)]
        return RitualAnswer("answered", answer, sources, time.monotonic() - t0)
