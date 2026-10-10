"""Runs the real app.py with a fake Ollama client (no model needed)."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import ghat_guide.llm as llm_mod

APP = str(Path(__file__).resolve().parent.parent / "app.py")


class FakeClient:
    def __init__(self, models=("gemma3:4b", "nomic-embed-text:latest"), down=False):
        self.models, self.down = models, down

    def list(self):
        if self.down:
            raise ConnectionError("Failed to connect to Ollama")
        return SimpleNamespace(models=[SimpleNamespace(model=m) for m in self.models])

    def chat(self, **kw):
        if self.down:
            raise ConnectionError("Failed to connect to Ollama")
        return SimpleNamespace(message=SimpleNamespace(content=json.dumps({"explanation": ""})))


@pytest.fixture
def use_client(monkeypatch):
    def _use(client):
        monkeypatch.setattr(llm_mod, "_default_client", lambda s: client)
        st.cache_resource.clear()
        st.cache_data.clear()

    yield _use
    st.cache_resource.clear()
    st.cache_data.clear()


def all_text(at) -> str:
    parts = []
    for kind in ("markdown", "caption", "error", "warning", "info", "title"):
        parts += [e.value for e in getattr(at, kind)]
    return "\n".join(str(p) for p in parts)


def test_app_boots_with_three_tabs_and_emergency_card(use_client):
    use_client(FakeClient())
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert len(at.tabs) == 3
    assert "छठ घाट गाइड" in at.title[0].value
    assert "पुलिस या स्वयंसेवक बूथ" in all_text(at)
    assert not at.error  # healthy: no setup banner


def test_ollama_down_shows_setup_banner_not_crash(use_client):
    use_client(FakeClient(down=True))
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert any("ollama serve" in e.value for e in at.error)


def test_missing_model_shows_pull_command(use_client):
    use_client(FakeClient(models=("nomic-embed-text",)))
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert any("ollama pull gemma3:4b" in w.value for w in at.warning)


def test_language_switch_changes_tab_label(use_client):
    use_client(FakeClient())
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.radio[0].set_value("mai").run()
    assert not at.exception
    assert at.tabs[0].label == "📜 सूचना पढ़ू"
    assert "परीक्षण" in all_text(at)  # beta note


# -- render_result views ------------------------------------------------------

def _page(clarity, is_safety, text, explanation, warn):
    from ghat_guide.notice_reader import Explanation, Transcription
    from ghat_guide.ui.notice_tab import render_result

    tr = Transcription(text, "devanagari", clarity, is_safety, 1.0)
    ex = None if explanation is False else Explanation("hi", explanation, None, frozenset(warn), 1.0)
    render_result(tr, ex, "hi")


def _render(clarity, is_safety, text, explanation, warn=()):
    return AppTest.from_function(
        _page, args=(clarity, is_safety, text, explanation, tuple(warn)), default_timeout=30
    ).run()


def test_view_clear_notice():
    at = _render("clear", False, "घाट 4 पर प्रसाद वितरण होगा", "घाट 4 पर प्रसाद मिलेगा।")
    assert not at.code
    assert not at.exception and not at.error and not at.warning
    assert "घाट 4 पर प्रसाद वितरण होगा" in all_text(at)
    assert "प्रसाद मिलेगा" in all_text(at)


def test_view_unclear_notice():
    at = _render("unclear", False, "[?] [?]", False)
    assert "साफ़ नहीं पढ़ पाए" in at.warning[0].value
    assert "\\[?\\] \\[?\\]" in all_text(at)


def test_view_safety_notice_original_first_in_red():
    at = _render("clear", True, "घाट 3 के आगे गहरा पानी है", "आगे पानी गहरा है।")
    err = at.error[0].value
    assert "सुरक्षा सूचना" in err
    assert "घाट 3 के आगे गहरा पानी है" in err  # original text inside the red box
    # shown once (not repeated in an expander), and before the explanation
    assert all("गहरा पानी है" not in m.value for m in at.markdown)
    blocks = [type(e).__name__ for e in at.main]
    assert blocks.index("Error") < blocks.index("Subheader")


def test_view_number_warning_and_partial():
    at = _render("partial", False, "घाट 5 पर [?] है", "घाट 7 पर कुछ है।", warn={"7"})
    assert any("[?]" in i.value for i in at.info)
    assert any("(7)" in w.value for w in at.warning)


def test_view_explanation_failed():
    at = _render("clear", False, "घाट 4 पर प्रसाद वितरण होगा", None)
    assert any("समझाने में दिक्कत" in w.value for w in at.warning)


def test_model_text_is_not_rendered_as_markdown():
    at = _render("clear", False, "घाट 4", "[click](http://evil.example) **bold**")
    md = [m.value for m in at.markdown]
    assert any("\\[click\\]" in v for v in md)


def test_line_breaks_kept():
    at = _render("clear", False, "पहली पंक्ति\nदूसरी पंक्ति", "ठीक")
    assert any("पहली पंक्ति  \nदूसरी पंक्ति" in m.value for m in at.markdown)


# -- Ritual tab -----------------------------------------------------------------

from dataclasses import replace  # noqa: E402

import ghat_guide.ui.services as services_mod  # noqa: E402
from ghat_guide.config import load_settings  # noqa: E402
from tests.fakes import SAMPLE_NOTES  # noqa: E402
from tests.fakes import FakeClient as RitualClient  # noqa: E402
from tests.fakes import write_kb  # noqa: E402


def _cite_first(kw):
    user = kw["messages"][1]["content"]
    if "<notes>" not in user:  # warm-up or other calls
        return {"explanation": ""}
    first = user.split("[", 1)[1].split("]", 1)[0]
    return {"found": True, "answer": "शाम को गुड़ की खीर और रोटी बनती है।", "used_chunk_ids": [first]}


@pytest.fixture
def ritual_app(use_client, monkeypatch, tmp_path):
    def _setup(notes):
        kb = write_kb(tmp_path / "kb", notes)
        base = load_settings()
        s = replace(base, ritual=replace(base.ritual, kb_dir=str(kb), index_path=str(tmp_path / "idx")))
        monkeypatch.setattr(services_mod, "load_settings", lambda: s)
        use_client(RitualClient(chat_reply=_cite_first))
        return AppTest.from_file(APP, default_timeout=30).run()

    return _setup


def test_ritual_tab_disabled_without_checked_notes(ritual_app):
    from tests.fakes import note

    at = ritual_app([note("x", "एक्स", ["क"], [("अ", "ब")], checked=False)])
    assert not at.exception
    assert any("जाँचा नहीं गया" in i.value for i in at.info)
    assert not at.text_input


def test_ritual_question_answered_with_sources(ritual_app):
    at = ritual_app(SAMPLE_NOTES)
    assert not at.exception
    at.text_input(key="ritual_q").input("खरना में क्या बनता है?")
    at.button[0].click().run()
    assert not at.exception
    text = all_text(at)
    assert "गुड़ की खीर और रोटी" in text
    assert "रिवाज़ थोड़े अलग" in text          # customs-vary line
    assert "जाँचा: Nani, 2026-10-10" in text   # source shows who checked it


def test_ritual_timing_question_gets_official_info(ritual_app):
    at = ritual_app(SAMPLE_NOTES)
    at.text_input(key="ritual_q").input("इस साल अर्घ्य कितने बजे है?")
    at.button[0].click().run()
    assert any("सरकारी सूचना" in i.value for i in at.info)


def test_ritual_unrelated_question_not_in_notes(ritual_app):
    at = ritual_app(SAMPLE_NOTES)
    at.text_input(key="ritual_q").input("How do I reach Patna railway station?")
    at.button[0].click().run()
    assert any("नोट्स में नहीं" in i.value for i in at.info)


def test_ritual_index_error_when_ollama_down(use_client, monkeypatch, tmp_path):
    kb = write_kb(tmp_path / "kb", SAMPLE_NOTES)
    base = load_settings()
    s = replace(base, ritual=replace(base.ritual, kb_dir=str(kb), index_path=str(tmp_path / "idx")))
    monkeypatch.setattr(services_mod, "load_settings", lambda: s)

    class Down(RitualClient):
        def embed(self, **kw):
            raise ConnectionError("Failed to connect to Ollama")

    use_client(Down())
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert any("nomic-embed-text" in e.value for e in at.error)


# -- Meeting Spot tab -----------------------------------------------------------

def test_meeting_tab_embeds_widget_with_strings_inlined(use_client):
    from ghat_guide.ui.meeting_tab import widget_html

    html = widget_html("bho")
    assert 'window.MS_LANG = "bho";' in html
    assert "MEETING_SPOT_STRINGS" in html
    assert 'src="meeting_spot_strings.js"' not in html  # a srcdoc frame can't load relative files

    use_client(FakeClient())
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert "पूरी स्क्रीन" in all_text(at)
