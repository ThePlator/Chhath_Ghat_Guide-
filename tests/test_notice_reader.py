import json
from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image

from ghat_guide.config import NoticeSettings, OllamaSettings
from ghat_guide.llm import LLMGateway, LLMUnavailable
from ghat_guide.notice_reader import NoticeReader


class ScriptedClient:
    """Answers transcribe calls (with images) and explain calls (text only) from fixed replies."""

    def __init__(self, transcribe, explain=None):
        self.transcribe = transcribe
        self.explain = explain
        self.calls = []

    def chat(self, **kw):
        self.calls.append(kw)
        reply = self.transcribe if "images" in kw["messages"][1] else self.explain
        content = reply if isinstance(reply, str) else json.dumps(reply, ensure_ascii=False)
        return SimpleNamespace(message=SimpleNamespace(content=content))


def reader(client, **notice_kw):
    models = OllamaSettings(max_retries=0)
    return NoticeReader(LLMGateway(models, client=client), NoticeSettings(**notice_kw), models)


def photo() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (2000, 1500), "white").save(buf, format="JPEG")
    return buf.getvalue()


def T(text, clarity="clear"):
    return {"text_read": text, "script": "devanagari", "clarity": clarity}


def test_clear_notice_two_calls_and_explanation():
    c = ScriptedClient(T("घाट 4 पर प्रसाद वितरण होगा"), {"explanation": "घाट 4 पर प्रसाद मिलेगा।"})
    r = reader(c).read(photo(), "hi")
    assert r.transcription.clarity == "clear"
    assert not r.transcription.is_safety
    assert r.explanation.text == "घाट 4 पर प्रसाद मिलेगा।"
    assert r.explanation.number_warning == frozenset()
    assert len(c.calls) == 2
    assert "Hindi" in c.calls[1]["messages"][0]["content"]
    assert "घाट 4 पर प्रसाद वितरण होगा" in c.calls[1]["messages"][1]["content"]


def test_image_is_prepared_before_sending():
    c = ScriptedClient(T("घाट 4 पर प्रसाद वितरण होगा"), {"explanation": "ठीक"})
    reader(c).read(photo(), "hi")
    sent = Image.open(BytesIO(c.calls[0]["messages"][1]["images"][0]))
    assert max(sent.size) == 1024


def test_unclear_notice_skips_explanation():
    c = ScriptedClient(T("[?] [?] है", "unclear"))
    r = reader(c).read(photo(), "hi")
    assert r.transcription.clarity == "unclear"
    assert r.explanation is None
    assert len(c.calls) == 1


def test_safety_notice_flagged():
    c = ScriptedClient(T("घाट 3 के आगे गहरा पानी है"), {"explanation": "आगे पानी गहरा है।"})
    assert reader(c).read(photo(), "bho").transcription.is_safety


def test_invented_number_flagged():
    c = ScriptedClient(T("घाट 5 पर गहरा पानी है"), {"explanation": "घाट 7 पर पानी गहरा है।"})
    assert reader(c).read(photo(), "hi").explanation.number_warning == {"7"}


def test_bad_transcription_json_becomes_unclear():
    r = reader(ScriptedClient("not json")).read(photo(), "hi")
    assert r.transcription.clarity == "unclear"
    assert r.explanation is None


def test_bad_explanation_json_keeps_text_read():
    c = ScriptedClient(T("घाट 4 पर प्रसाद वितरण होगा"), "not json")
    r = reader(c).read(photo(), "hi")
    assert r.transcription.text_read == "घाट 4 पर प्रसाद वितरण होगा"
    assert r.explanation is not None and r.explanation.text is None


def test_explain_reuses_transcription_for_new_language():
    c = ScriptedClient(T("घाट 4 पर प्रसाद वितरण होगा"), {"explanation": "ठीक"})
    rd = reader(c)
    tr = rd.transcribe(rd.prepare(photo()))
    rd.explain(tr, "hi")
    rd.explain(tr, "mai")
    assert len(c.calls) == 3  # one image call, two text calls
    assert "Maithili" in c.calls[2]["messages"][0]["content"]


def test_highlights_parsed_when_present():
    c = ScriptedClient(
        T("घाट 4 पर शाम 5 बजे"),
        {"explanation": "ठीक", "highlights": {"times": ["शाम 5 बजे"], "ghat_numbers": ["4"]}},
    )
    h = reader(c).read(photo(), "hi").explanation.highlights
    assert h.times == ["शाम 5 बजे"] and h.ghat_numbers == ["4"] and h.dos == []


def test_unavailable_propagates():
    class Down:
        def chat(self, **kw):
            raise ConnectionError("Failed to connect to Ollama")

    with pytest.raises(LLMUnavailable):
        reader(Down()).read(photo(), "hi")
