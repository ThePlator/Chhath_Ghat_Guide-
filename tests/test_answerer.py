import pytest

from ghat_guide.config import OllamaSettings, RitualSettings
from ghat_guide.llm import LLMGateway
from ghat_guide.ritual.answerer import RitualHelper, asks_for_official_info
from ghat_guide.ritual.index import build_index
from ghat_guide.ritual.kb_loader import load_kb
from ghat_guide.ritual.retriever import Retriever
from tests.fakes import SAMPLE_NOTES, FakeClient, write_kb


def helper(tmp_path, reply):
    client = FakeClient(chat_reply=reply)
    models = OllamaSettings(max_retries=0)
    llm = LLMGateway(models, client=client)
    idx = build_index(load_kb(write_kb(tmp_path / "kb", SAMPLE_NOTES)).chunks, llm)
    return RitualHelper(Retriever(idx, llm, RitualSettings()), llm, RitualSettings(), models), client


def cite_first(kw):
    """Model stand-in: cites the first chunk id it was given."""
    user = kw["messages"][1]["content"]
    first = user.split("[", 1)[1].split("]", 1)[0]
    return {"found": True, "answer": "शाम को गुड़ की खीर और रोटी बनती है।", "used_chunk_ids": [first]}


def test_grounded_answer_with_sources(tmp_path):
    h, client = helper(tmp_path, cite_first)
    a = h.ask("खरना में क्या बनता है?", "hi")
    assert a.outcome == "answered" and a.found
    assert a.answer.startswith("शाम को")
    assert [s.chunk.note_id for s in a.sources] == ["kharna"]
    sys_prompt = client.chat_calls[0]["messages"][0]["content"]
    assert "Hindi" in sys_prompt and client.chat_calls[0]["options"]["temperature"] == 0.1
    assert "<notes>" in client.chat_calls[0]["messages"][1]["content"]


def test_language_reaches_prompt(tmp_path):
    h, client = helper(tmp_path, cite_first)
    h.ask("खरना में का बनेला?", "bho")
    assert "Bhojpuri" in client.chat_calls[0]["messages"][0]["content"]


def test_model_says_not_found(tmp_path):
    h, _ = helper(tmp_path, {"found": False, "answer": "", "used_chunk_ids": []})
    assert h.ask("खरना में क्या बनता है?", "hi").outcome == "not_in_notes"


def test_cites_unknown_chunk_falls_back(tmp_path):
    h, _ = helper(tmp_path, {"found": True, "answer": "कुछ", "used_chunk_ids": ["made-up#x"]})
    assert h.ask("खरना में क्या बनता है?", "hi").outcome == "not_in_notes"


def test_found_without_citation_falls_back(tmp_path):
    h, _ = helper(tmp_path, {"found": True, "answer": "कुछ", "used_chunk_ids": []})
    assert h.ask("खरना में क्या बनता है?", "hi").outcome == "not_in_notes"


def test_bad_json_falls_back(tmp_path):
    h, _ = helper(tmp_path, "not json")
    assert h.ask("खरना में क्या बनता है?", "hi").outcome == "not_in_notes"


def test_irrelevant_question_never_reaches_model(tmp_path):
    h, client = helper(tmp_path, cite_first)
    assert h.ask("How do I reach Patna railway station?", "hi").outcome == "not_in_notes"
    assert client.chat_calls == []


@pytest.mark.parametrize(
    "q",
    ["इस साल अर्घ्य कितने बजे है?", "संध्या अर्घ्य कितने बजे होगा", "घाट पर पार्किंग कहाँ है?", "छठ 2026 की तारीख", "What time is arghya?"],
)
def test_timing_and_logistics_questions_guarded(tmp_path, q):
    h, client = helper(tmp_path, cite_first)
    assert h.ask(q, "hi").outcome == "official_info"
    assert client.chat_calls == []


@pytest.mark.parametrize("q", ["अर्घ्य कब दिया जाता है?", "छठ किस महीने में होता है?", "सूप में क्या रखते हैं?"])
def test_ordinary_questions_not_guarded(q):
    assert not asks_for_official_info(q)


def test_empty_question_rejected(tmp_path):
    h, _ = helper(tmp_path, cite_first)
    with pytest.raises(ValueError):
        h.ask("   ", "hi")


def test_long_question_truncated(tmp_path):
    h, client = helper(tmp_path, cite_first)
    h.ask("खरना " * 200, "hi")
    assert len(client.chat_calls[0]["messages"][1]["content"].split("Question: ")[1]) <= 300
