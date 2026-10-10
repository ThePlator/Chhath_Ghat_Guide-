"""Hybrid keyword + vector search over KB chunks (LLD §3.7).

nomic-embed-text is trained mostly on English, so Devanagari questions can rank
poorly on vectors alone; hand-written note keywords make up for it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from ..config import RitualSettings
from ..llm import LLMGateway
from ..safety import normalise
from .index import QUERY_PREFIX, KBIndex
from .kb_loader import Chunk

_SPLIT = re.compile(r"[\s,.;:!?।॥'\"“”‘’()\[\]{}\-–—/]+")
_TRAILING_MATRAS = "ािीुूेैोौंँः"

STOP_WORDS = {
    normalise(w)
    for w in (
        "क्या", "कब", "कैसे", "क्यों", "कौन", "कौनसा", "किस", "किसकी", "किसका", "किसके", "कहाँ", "कितना", "कितने",
        "है", "हैं", "था", "थे", "हो", "होता", "होती", "होते", "जाता", "जाती", "जाते", "दिया", "देते", "करते", "करें",
        "में", "मे", "पर", "से", "को", "का", "की", "के", "और", "या", "भी", "तो", "ही", "एक", "यह", "वह", "इस", "उस",
        "हम", "मैं", "आप", "हमें", "मुझे", "बताइए", "बताओ", "बताईं", "बताउ", "चाहिए",
        # generic verbs that say nothing about the topic
        "रखते", "रखें", "रखी", "बनता", "बनती", "बनते", "करना", "सकते", "सकती",
        # bho / mai function words and helper verbs
        "बा", "बाटे", "ह", "हवे", "छै", "अछि", "कइसे", "केना", "कहिया", "का", "के", "में", "मे",
        "जाला", "जाले", "जाई", "होला", "होखे", "होइत", "रखल", "रखाला", "बनेला", "बनैत", "कइल", "गइल", "छथि", "छैक",
        # latin
        "what", "when", "how", "why", "is", "the", "a", "of", "in", "do", "we", "kya", "kab", "ka", "ki", "ke", "hai",
    )
}

# Spellings families use → the word the notes use.
SYNONYMS = {
    normalise(k): normalise(v)
    for k, v in {
        "अरघ": "अर्घ्य", "अर्घ": "अर्घ्य", "अरग": "अर्घ्य", "arghya": "अर्घ्य", "argh": "अर्घ्य", "arag": "अर्घ्य",
        "सूपा": "सूप", "soop": "सूप", "sup": "सूप", "दौरा": "दउरा", "डाला": "दउरा", "daura": "दउरा",
        "kharna": "खरना", "लोहंडा": "खरना", "खरने": "खरना",
        "nahay": "नहाय", "नहाए": "नहाय", "khay": "खाय",
        "thekua": "ठेकुआ", "ठेकुवा": "ठेकुआ", "खजूर": "ठेकुआ",
        "सूरज": "सूर्य", "सुरुज": "सूर्य", "suraj": "सूर्य", "surya": "सूर्य",
        "मैया": "मइया", "माई": "मइया", "maiya": "मइया",
        "chhath": "छठ", "छठि": "छठ",
        "सुबह": "उषा", "भोर": "उषा", "सवेरे": "उषा", "शाम": "संध्या", "सांझ": "संध्या", "साँझ": "संध्या",
        "उपवास": "व्रत", "vrat": "व्रत", "बरत": "व्रत",
    }.items()
}


def stem(tok: str) -> str:
    """Drop up to two trailing vowel signs so खरने / खरना / खरनी meet."""
    for _ in range(2):
        if len(tok) > 3 and tok[-1] in _TRAILING_MATRAS:
            tok = tok[:-1]
    return tok


def tokens(text: str) -> list[str]:
    out = []
    for raw in _SPLIT.split(normalise(text)):
        if not raw or raw in STOP_WORDS:
            continue
        tok = SYNONYMS.get(raw, raw)
        out.append(stem(tok))
    return out


def chunk_terms(c: Chunk) -> set[str]:
    words = list(c.keywords) + [c.section, c.note_title]
    return {t for w in words for t in tokens(w)}


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float
    vector_score: float
    keyword_score: float


class Retriever:
    def __init__(self, index: KBIndex, llm: LLMGateway, s: RitualSettings):
        self.index = index
        self.llm = llm
        self.s = s
        self._terms = [chunk_terms(c) for c in index.chunks]

    def keyword_scores(self, question: str) -> np.ndarray:
        q = set(tokens(question))
        if not q:
            return np.zeros(len(self._terms), np.float32)
        return np.array([len(q & terms) / len(q) for terms in self._terms], np.float32)

    def search(self, question: str) -> list[Hit]:
        if not self.index.chunks:
            return []
        qv = self.llm.embed([f"{QUERY_PREFIX}{question}"])[0]
        vec = np.clip(self.index.vectors @ qv, 0.0, 1.0)
        kw = self.keyword_scores(question)
        score = self.s.weight_vector * vec + self.s.weight_keyword * kw
        order = np.argsort(-score, kind="stable")[: self.s.top_k]
        return [Hit(self.index.chunks[i], float(score[i]), float(vec[i]), float(kw[i])) for i in order]

    def is_relevant(self, hit: Hit) -> bool:
        if hit.score < self.s.min_score:
            return False
        return hit.keyword_score > 0 or hit.vector_score >= self.s.vector_only_min
