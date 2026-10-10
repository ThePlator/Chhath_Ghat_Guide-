import pytest

from ghat_guide.config import OllamaSettings, RitualSettings
from ghat_guide.llm import LLMGateway
from ghat_guide.ritual.index import build_index
from ghat_guide.ritual.kb_loader import load_kb
from ghat_guide.ritual.retriever import Retriever, stem, tokens
from tests.fakes import SAMPLE_NOTES, FakeClient, write_kb


@pytest.fixture
def retriever(tmp_path):
    llm = LLMGateway(OllamaSettings(), client=FakeClient())
    idx = build_index(load_kb(write_kb(tmp_path / "kb", SAMPLE_NOTES)).chunks, llm)
    return Retriever(idx, llm, RitualSettings())


def test_tokens_drop_stop_words_and_map_synonyms():
    assert tokens("अरघ कब दिया जाता है?") == ["अर्घ्य"]
    assert tokens("सूपा में का रखल जाला?") == ["सूप"]
    assert tokens("Kharna kya hai") == tokens("खरना")


def test_stem_joins_inflections():
    assert stem("खरने") == stem("खरना")
    assert stem("घाट") == "घाट"


@pytest.mark.parametrize(
    "q,note_id",
    [
        ("सूप में क्या रखते हैं?", "soop-daura"),
        ("सूपा में का रखल जाला?", "soop-daura"),        # Bhojpuri + spelling variant
        ("खरना में क्या बनता है?", "kharna"),
        ("खरने में क्या बनता है?", "kharna"),            # inflected
        ("अरघ कब दिया जाता है", "sandhya-arghya"),        # spelling variant
    ],
)
def test_finds_right_note(retriever, q, note_id):
    top = retriever.search(q)[0]
    assert top.chunk.note_id == note_id
    assert retriever.is_relevant(top)


def test_unrelated_question_not_relevant(retriever):
    top = retriever.search("How do I reach Patna railway station?")[0]
    assert not retriever.is_relevant(top)


def test_vector_only_match_needs_high_score(retriever):
    from ghat_guide.ritual.retriever import Hit

    c = retriever.index.chunks[0]
    assert not retriever.is_relevant(Hit(c, score=0.6, vector_score=0.7, keyword_score=0.0))
    assert retriever.is_relevant(Hit(c, score=0.6, vector_score=0.8, keyword_score=0.0))
    assert not retriever.is_relevant(Hit(c, score=0.3, vector_score=0.3, keyword_score=0.5))


def test_top_k_and_empty_index(retriever):
    assert len(retriever.search("सूप")) <= RitualSettings().top_k
    empty = Retriever(type(retriever.index)([], retriever.index.vectors[:0], "", "x"), retriever.llm, RitualSettings())
    assert empty.search("सूप") == []
