"""Evaluate Ritual Helper retrieval (and optionally answers) on ritual_questions.yaml.

    python tests/eval/run_ritual_eval.py                      # retrieval only, checked notes
    python tests/eval/run_ritual_eval.py --include-unchecked  # before the elder review (tuning only)
    python tests/eval/run_ritual_eval.py --answer --langs hi,bho

Use the printed score ranges to set ritual.min_score in config/settings.toml.
--fake-embed swaps in a tiny bag-of-words embedder so the keyword side can be
checked without Ollama; its vector scores mean nothing for tuning.
"""

from __future__ import annotations

import argparse
import sys
import zlib
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ghat_guide.config import load_settings, project_path  # noqa: E402
from ghat_guide.llm import LLMGateway  # noqa: E402
from ghat_guide.ritual.answerer import RitualHelper, asks_for_official_info  # noqa: E402
from ghat_guide.ritual.index import build_index  # noqa: E402
from ghat_guide.ritual.kb_loader import load_kb  # noqa: E402
from ghat_guide.ritual.retriever import Retriever, tokens  # noqa: E402


class FakeEmbedClient:
    """Bag-of-tokens hashing embedder: lets the pipeline run without Ollama."""

    DIM = 512

    def embed(self, model, input, **kw):
        out = []
        for text in input:
            v = np.zeros(self.DIM, np.float32)
            for tok in tokens(text.split(": ", 1)[-1]):
                v[zlib.crc32(tok.encode()) % self.DIM] += 1.0
            out.append(v.tolist())
        return SimpleNamespace(embeddings=out)

    def list(self):
        return SimpleNamespace(models=[])


def main(argv=None, llm=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--questions", type=Path, default=Path(__file__).with_name("ritual_questions.yaml"))
    ap.add_argument("--include-unchecked", action="store_true", help="also use unchecked draft notes (tuning only)")
    ap.add_argument("--answer", action="store_true", help="also ask the model and check found / not found")
    ap.add_argument("--langs", default="hi")
    ap.add_argument("--fake-embed", action="store_true")
    ap.add_argument("--min-score", type=float, help="override ritual.min_score for this run")
    args = ap.parse_args(argv)

    s = load_settings()
    rs = replace(s.ritual, min_score=args.min_score) if args.min_score is not None else s.ritual
    kb = load_kb(project_path(rs.kb_dir), include_unchecked=args.include_unchecked)
    if not kb.chunks:
        print("No notes loaded. Check notes (kb/README.md) or pass --include-unchecked for tuning.")
        return 1
    if args.include_unchecked:
        print(f"⚠️  Using {len(kb.notes_unchecked)} UNCHECKED draft note(s): tuning only, not what users see.\n")

    if llm is None:
        llm = LLMGateway(s.ollama, client=FakeEmbedClient() if args.fake_embed else None)
    index = build_index(kb.chunks, llm)
    retriever = Retriever(index, llm, rs)
    data = yaml.safe_load(args.questions.read_text(encoding="utf-8"))

    print(f"{'result':<8} {'top note':<20} {'score':>5} {'vec':>5} {'kw':>5}  question")
    hits_ok, ans_scores, leaks, neg_scores = 0, [], [], []
    for item in data["answerable"]:
        top = retriever.search(item["q"])[0]
        ok = retriever.is_relevant(top) and top.chunk.note_id in item["expect"]
        hits_ok += ok
        ans_scores.append(top.score)
        print(f"{'ok' if ok else 'MISS':<8} {top.chunk.note_id:<20} {top.score:5.2f} {top.vector_score:5.2f} {top.keyword_score:5.2f}  {item['q']}")
    print()
    for item in data["not_answerable"]:
        if asks_for_official_info(item["q"]):
            ok = item["expect"] == "official"
            print(f"{'guard' if ok else 'GUARD?':<8} {'(official info)':<20} {'':>5} {'':>5} {'':>5}  {item['q']}")
            continue
        top = retriever.search(item["q"])[0]
        relevant = retriever.is_relevant(top)
        neg_scores.append(top.score)
        if relevant:
            leaks.append(item["q"])
        print(f"{'passes' if relevant else 'blocked':<8} {top.chunk.note_id:<20} {top.score:5.2f} {top.vector_score:5.2f} {top.keyword_score:5.2f}  {item['q']}")

    n = len(data["answerable"])
    print(f"\nRetrieval hit rate: {hits_ok}/{n}")
    print(f"Answerable top scores: min {min(ans_scores):.2f}, median {float(np.median(ans_scores)):.2f}")
    if neg_scores:
        print(f"Not-answerable top scores: max {max(neg_scores):.2f}   (min_score now {rs.min_score:.2f})")
    print(f"Not-answerable questions that reach the model: {len(leaks)} (the model's found=false must catch these)")

    if not args.answer:
        return 0

    helper = RitualHelper(retriever, llm, rs, s.ollama)
    false_answers = 0
    for lang in [l.strip() for l in args.langs.split(",") if l.strip()]:
        print(f"\n=== Answers ({lang}) ===")
        for group in ("answerable", "not_answerable"):
            for item in data[group]:
                a = helper.ask(item["q"], lang)
                if group == "not_answerable" and a.found:
                    false_answers += 1
                cited = ", ".join(h.chunk.chunk_id for h in a.sources)
                print(f"\n[{a.outcome}] {item['q']}  ({a.elapsed_s:.0f}s)")
                if a.answer:
                    print(f"  {a.answer}\n  sources: {cited}")
    print(f"\nConfident answers to not-answerable questions: {false_answers}  (target: 0)")
    return 0 if false_answers == 0 else 3


if __name__ == "__main__":
    sys.exit(main())
