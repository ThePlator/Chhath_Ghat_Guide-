"""Meeting Spot tab (LLD §5.5).

The widget in static/meeting_spot.html does everything in the browser: GPS,
compass and the saved spot never reach this server. Here we only embed it,
with its strings inlined, and offer the same page full-screen as a fallback
for browsers that block sensors inside the embedded frame.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from ..config import PROJECT_ROOT
from ..i18n import t

STATIC = PROJECT_ROOT / "static"
WIDGET = STATIC / "meeting_spot.html"
STRINGS_TAG = '<script src="meeting_spot_strings.js"></script>'
FULL_PAGE_URL = "app/static/meeting_spot.html?lang={lang}"


@lru_cache(maxsize=8)
def widget_html(lang: str) -> str:
    """The widget with its strings file inlined (an embedded srcdoc frame can't
    load relative files) and the language preset."""
    html = Path(WIDGET).read_text(encoding="utf-8")
    strings = Path(STATIC / "meeting_spot_strings.js").read_text(encoding="utf-8")
    if STRINGS_TAG not in html:
        raise RuntimeError("meeting_spot.html no longer loads meeting_spot_strings.js")
    inline = f"<script>window.MS_LANG = {json.dumps(lang)};</script>\n<script>\n{strings}\n</script>"
    return html.replace(STRINGS_TAG, inline)


def render(lang: str) -> None:
    # The fallback link goes first: the frame has a fixed height, so anything
    # below it can sit far down the page on a phone.
    st.link_button(t("open_full_screen", lang), FULL_PAGE_URL.format(lang=lang))
    st.caption(t("full_screen_hint", lang))
    components.html(widget_html(lang), height=780, scrolling=True)
