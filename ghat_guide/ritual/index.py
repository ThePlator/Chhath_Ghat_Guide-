"""Embed KB chunks once and cache them on disk (LLD §3.6).

The cache is reused only when the chunks and the embedding model are the same
as when it was built, so editing or checking a note triggers a rebuild.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from ..llm import LLMGateway
from .kb_loader import Chunk, kb_fingerprint

log = logging.getLogger(__name__)

# nomic-embed-text expects these task prefixes.
DOC_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "


@dataclass
class KBIndex:
    chunks: list[Chunk]
    vectors: np.ndarray  # (n_chunks, d) float32, L2-normalised
    fingerprint: str
    embed_model: str


def doc_text(c: Chunk) -> str:
    return f"{DOC_PREFIX}{c.note_title} — {c.section}\n{c.text}"


def build_index(chunks: list[Chunk], llm: LLMGateway) -> KBIndex:
    vectors = llm.embed([doc_text(c) for c in chunks]) if chunks else np.zeros((0, 0), np.float32)
    return KBIndex(chunks, vectors, kb_fingerprint(chunks), llm.s.embed_model)


def _paths(index_path: str | Path) -> tuple[Path, Path]:
    base = Path(index_path)
    return base.with_suffix(".npz"), base.with_suffix(".json")


def save_index(index: KBIndex, index_path: str | Path) -> None:
    npz, meta = _paths(index_path)
    npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez(npz, vectors=index.vectors)
    meta.write_text(
        json.dumps(
            {
                "fingerprint": index.fingerprint,
                "embed_model": index.embed_model,
                "chunks": [asdict(c) for c in index.chunks],
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )


def load_cached(index_path: str | Path, fingerprint: str, embed_model: str) -> KBIndex | None:
    npz, meta = _paths(index_path)
    try:
        m = json.loads(meta.read_text(encoding="utf-8"))
        if m.get("fingerprint") != fingerprint or m.get("embed_model") != embed_model:
            return None
        chunks = [Chunk(**{**c, "keywords": tuple(c["keywords"])}) for c in m["chunks"]]
        with np.load(npz) as data:
            vectors = data["vectors"].astype(np.float32)
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if len(chunks) and vectors.shape[0] != len(chunks):
        return None
    return KBIndex(chunks, vectors, fingerprint, embed_model)


def load_or_build(chunks: list[Chunk], index_path: str | Path, llm: LLMGateway) -> tuple[KBIndex, bool]:
    """Returns (index, rebuilt)."""
    cached = load_cached(index_path, kb_fingerprint(chunks), llm.s.embed_model)
    if cached is not None:
        return cached, False
    log.info("building KB index for %d chunks", len(chunks))
    index = build_index(chunks, llm)
    save_index(index, index_path)
    return index, True
