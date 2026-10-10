"""Sidebar (language picker, emergency card) and the model health banner."""

from __future__ import annotations

import streamlit as st

from ..i18n import LANGUAGE_LABELS, t
from . import services


def render_sidebar() -> str:
    """Draws the sidebar and returns the chosen language code."""
    s = services.get_settings()
    codes = list(LANGUAGE_LABELS)
    if "lang" not in st.session_state:
        st.session_state["lang"] = s.ui.default_language

    with st.sidebar:
        lang = st.radio(
            t("language_label", st.session_state["lang"]),
            codes,
            format_func=LANGUAGE_LABELS.get,
            key="lang",
        )
        if lang in s.ui.beta_languages:
            st.caption(t("beta_note", lang))

        st.divider()
        render_emergency(lang)
        st.divider()
        st.caption(t("helper_note", lang))
    return lang


def render_emergency(lang: str) -> None:
    info = services.get_emergency()
    with st.container(border=True):
        st.markdown(f"**{t('emergency_title', lang)}**")
        st.write(info.message_for(lang) or t("emergency_default", lang))
        if info.contacts:
            st.markdown(f"*{t('emergency_contacts', lang)}*")
            for c in info.contacts:
                line = c.label
                if c.phone:
                    line += f" — [{c.phone}](tel:{c.phone.replace(' ', '')})"
                if c.where:
                    line += f"  \n{c.where}"
                st.markdown(line)


def render_health_banner(lang: str) -> bool:
    """Shows setup help when Ollama or a model is missing. Returns True if all good."""
    s = services.get_settings()
    h = services.get_health()
    if not h["server"]:
        st.error(t("health_server_down", lang))
        st.caption(t("health_meeting_ok", lang))
        return False
    missing = sorted(
        {
            m
            for m, ok in (
                (s.ollama.vision_model, h["vision_model"]),
                (s.ollama.text_model, h["text_model"]),
                (s.ollama.embed_model, h["embed_model"]),
            )
            if not ok
        }
    )
    if missing:
        st.warning(t("health_model_missing", lang, cmds=" && ".join(f"`ollama pull {m}`" for m in missing)))
        return False
    return True
