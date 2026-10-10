"""Ritual Helper tab (LLD §5.4)."""

from __future__ import annotations

import logging

import streamlit as st

from ..i18n import ritual_examples, t
from ..llm import LLMError, LLMTimeout
from ..ritual.answerer import RitualAnswer
from . import services
from .text import plain

log = logging.getLogger(__name__)

MAX_HISTORY = 5


def _pick_example() -> None:
    choice = st.session_state.get("ritual_pill")
    if choice:
        st.session_state["ritual_q"] = choice
        st.session_state["ritual_go"] = True
        st.session_state["ritual_pill"] = None  # don't leave the chip highlighted for the next question


def render(lang: str) -> None:
    st.write(t("ritual_intro", lang))

    try:
        helper = services.get_ritual_helper()
    except LLMError as e:
        log.warning("ritual index unavailable: %s", type(e).__name__)
        st.error(t("ritual_index_error", lang))
        return
    if not helper.has_notes:
        st.info(t("ritual_no_notes", lang))
        return

    with st.form("ritual_form", border=False):
        question = st.text_input(t("ritual_question", lang), key="ritual_q", placeholder=t("ritual_placeholder", lang))
        submitted = st.form_submit_button(t("ritual_ask", lang), type="primary")
    st.pills(t("ritual_examples", lang), ritual_examples(lang), key="ritual_pill", on_change=_pick_example)

    go = submitted or st.session_state.pop("ritual_go", False)
    history: list[tuple[str, RitualAnswer]] = st.session_state.setdefault("ritual_history", [])

    if go:
        if not question.strip():
            st.warning(t("ritual_empty_question", lang))
        else:
            try:
                with st.spinner(t("ritual_thinking", lang)):
                    answer = helper.ask(question, lang)
            except LLMTimeout:
                st.error(t("err_timeout", lang))
                return
            except LLMError as e:
                log.warning("ritual answer failed: %s", type(e).__name__)
                st.error(t("err_unavailable", lang))
                return
            history.insert(0, (question.strip(), answer))
            del history[MAX_HISTORY:]

    if not history:
        return
    q, latest = history[0]
    st.markdown(f"**{plain(q)}**")
    render_answer(latest, lang)

    if len(history) > 1:
        with st.expander(t("ritual_recent", lang)):
            for old_q, old_a in history[1:]:
                st.markdown(f"**{plain(old_q)}**")
                render_answer(old_a, lang, show_sources=False)
                st.divider()


def render_answer(a: RitualAnswer, lang: str, show_sources: bool = True) -> None:
    if a.outcome == "official_info":
        st.info(t("official_info", lang))
        return
    if a.outcome != "answered" or not a.answer:
        st.info(t("not_in_notes", lang))
        return

    with st.container(border=True):
        st.markdown(plain(a.answer))
        st.caption(t("customs_vary", lang))

    if show_sources and a.sources:
        with st.expander(t("sources", lang)):
            for h in a.sources:
                c = h.chunk
                st.markdown(f"**{plain(c.note_title)} — {plain(c.section)}**")
                st.caption(t("checked_by_line", lang, who=c.checked_by, when=c.checked_on))
                st.markdown(plain(c.text))
