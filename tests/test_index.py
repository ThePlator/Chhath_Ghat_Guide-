import numpy as np

from ghat_guide.config import OllamaSettings
from ghat_guide.llm import LLMGateway
from ghat_guide.ritual.index import load_or_build
from ghat_guide.ritual.kb_loader import load_kb
from tests.fakes import SAMPLE_NOTES, FakeClient, write_kb


def test_build_then_reuse_then_rebuild_on_change(tmp_path):
    d = write_kb(tmp_path / "kb", SAMPLE_NOTES)
    client = FakeClient()
    llm = LLMGateway(OllamaSettings(), client=client)
    path = tmp_path / "data" / "kb_index"

    idx, rebuilt = load_or_build(load_kb(d).chunks, path, llm)
    assert rebuilt and client.embed_calls == 1
    assert idx.vectors.shape[0] == len(idx.chunks) == 4
    np.testing.assert_allclose(np.linalg.norm(idx.vectors, axis=1), 1.0, rtol=1e-5)
    assert (tmp_path / "data" / "kb_index.npz").exists() and (tmp_path / "data" / "kb_index.json").exists()

    idx2, rebuilt = load_or_build(load_kb(d).chunks, path, llm)
    assert not rebuilt and client.embed_calls == 1
    assert idx2.chunks == idx.chunks
    np.testing.assert_allclose(idx2.vectors, idx.vectors)

    (d / "02.md").write_text(SAMPLE_NOTES[1].replace("गन्ना", "सिंघाड़ा"), encoding="utf-8")
    _, rebuilt = load_or_build(load_kb(d).chunks, path, llm)
    assert rebuilt and client.embed_calls == 2

    other = LLMGateway(OllamaSettings(embed_model="bge-m3"), client=client)
    _, rebuilt = load_or_build(load_kb(d).chunks, path, other)
    assert rebuilt  # a different embedding model never reuses old vectors


def test_corrupt_cache_rebuilds(tmp_path):
    d = write_kb(tmp_path / "kb", SAMPLE_NOTES)
    llm = LLMGateway(OllamaSettings(), client=FakeClient())
    path = tmp_path / "kb_index"
    load_or_build(load_kb(d).chunks, path, llm)
    (tmp_path / "kb_index.json").write_text("{broken", encoding="utf-8")
    _, rebuilt = load_or_build(load_kb(d).chunks, path, llm)
    assert rebuilt
