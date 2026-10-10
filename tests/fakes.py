"""Shared stand-ins for Ollama used by the Ritual Helper tests."""

import json
import zlib
from types import SimpleNamespace

import numpy as np

from ghat_guide.ritual.retriever import tokens


class FakeClient:
    """Bag-of-tokens embeddings + scripted chat replies (dict or callable(kwargs) -> dict)."""

    DIM = 512

    def __init__(self, chat_reply=None, models=("gemma3:4b", "nomic-embed-text:latest")):
        self.chat_reply = chat_reply
        self.models = models
        self.chat_calls = []
        self.embed_calls = 0

    def embed(self, model, input, **kw):
        self.embed_calls += 1
        out = []
        for text in input:
            v = np.zeros(self.DIM, np.float32)
            for tok in tokens(text.split(": ", 1)[-1]):
                v[zlib.crc32(tok.encode()) % self.DIM] += 1.0
            out.append(v.tolist())
        return SimpleNamespace(embeddings=out)

    def chat(self, **kw):
        self.chat_calls.append(kw)
        reply = self.chat_reply(kw) if callable(self.chat_reply) else self.chat_reply
        content = reply if isinstance(reply, str) else json.dumps(reply or {}, ensure_ascii=False)
        return SimpleNamespace(message=SimpleNamespace(content=content))

    def list(self):
        return SimpleNamespace(models=[SimpleNamespace(model=m) for m in self.models])


def note(id_, title_hi, keywords, sections, checked=True):
    kw = ", ".join(keywords)
    body = "\n\n".join(f"## {h}\n\n{t}" for h, t in sections)
    cb = '"Nani"' if checked else '""'
    co = "2026-10-10" if checked else '""'
    return f"---\nid: {id_}\ntitle_hi: {title_hi}\nkeywords: [{kw}]\nchecked_by: {cb}\nchecked_on: {co}\n---\n\n{body}\n"


def write_kb(dir_, notes):
    dir_.mkdir(parents=True, exist_ok=True)
    for i, text in enumerate(notes, 1):
        (dir_ / f"{i:02d}.md").write_text(text, encoding="utf-8")
    return dir_


SAMPLE_NOTES = [
    note("kharna", "खरना", ["खरना", "खीर", "गुड़", "रोटी"], [("क्या होता है", "खरना दूसरा दिन है। शाम को गुड़ की खीर और रोटी बनती है।"), ("इसके बाद", "प्रसाद के बाद निर्जला व्रत शुरू होता है।")]),
    note("soop-daura", "सूप और दउरा", ["सूप", "दउरा", "फल", "केला", "नारियल"], [("सूप में क्या रखते हैं", "सूप में ठेकुआ, केला, नारियल और गन्ना रखते हैं।")]),
    note("sandhya-arghya", "संध्या अर्घ्य", ["अर्घ्य", "संध्या", "डूबते सूर्य"], [("कब", "अर्घ्य सूर्यास्त के समय दिया जाता है।")]),
]
