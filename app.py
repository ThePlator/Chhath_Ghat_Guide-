"""Chhath Ghat Guide — Streamlit entry point.

    streamlit run app.py
"""

import logging

import streamlit as st

st.set_page_config(page_title="Chhath Ghat Guide", page_icon="🌅", layout="centered")

from ghat_guide.i18n import t  # noqa: E402
from ghat_guide.ui import notice_tab  # noqa: E402
from ghat_guide.ui.sidebar import render_health_banner, render_sidebar  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

lang = render_sidebar()

st.title(t("app_title", lang))
st.caption(t("app_tagline", lang))
render_health_banner(lang)

tab_notice, tab_ritual, tab_meeting = st.tabs([t("tab_notice", lang), t("tab_ritual", lang), t("tab_meeting", lang)])

with tab_notice:
    notice_tab.render(lang)

with tab_ritual:
    st.info(t("coming_soon_ritual", lang))  # Phase 3

with tab_meeting:
    st.info(t("coming_soon_meeting", lang))  # Phase 4
