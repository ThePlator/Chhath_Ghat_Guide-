"""Notice Reader tab (LLD §5.3)."""

from __future__ import annotations

import hashlib
import logging

import streamlit as st

from ..i18n import t
from ..imaging import ImageError
from ..llm import LLMError, LLMTimeout, LLMUnavailable
from ..notice_reader import Explanation, Transcription
from . import services
from .text import plain

log = logging.getLogger(__name__)

def render(lang: str) -> None:
    st.write(t("notice_intro", lang))
    # On phones the picker itself offers "take photo"; the in-app camera is
    # opt-in so it doesn't fill the screen or ask for permission on page load.
    upload = st.file_uploader(t("upload_photo", lang), type=["jpg", "jpeg", "png", "webp"], key="notice_upload")
    cam = None
    if st.toggle(t("use_camera", lang), key="notice_use_camera"):
        cam = st.camera_input(t("take_photo", lang), key="notice_camera", label_visibility="collapsed")
    src = cam or upload
    if src is None:
        return

    raw = src.getvalue()
    digest = hashlib.sha1(raw).hexdigest()
    # One cache per browser session: the photo is never written to disk, and a
    # language switch re-runs only the cheap text step, not the image step.
    cache = st.session_state.setdefault("notice_cache", {})
    if cache.get("hash") != digest:
        cache.clear()
        cache["hash"] = digest
        cache["explanations"] = {}

    reader = services.get_notice_reader()
    try:
        if "prepared" not in cache:
            cache["prepared"] = reader.prepare(raw)
        if "transcription" not in cache:
            with st.spinner(t("reading", lang)):
                cache["transcription"] = reader.transcribe(cache["prepared"])
        tr: Transcription = cache["transcription"]
        if lang not in cache["explanations"] and tr.clarity != "unclear":
            with st.spinner(t("explaining", lang)):
                cache["explanations"][lang] = reader.explain(tr, lang)
    except ImageError:
        st.error(t("err_image", lang))
        return
    except LLMTimeout:
        st.error(t("err_timeout", lang))
        return
    except LLMUnavailable as e:
        st.error(t("err_unavailable", lang))
        st.caption(str(e))
        return
    except LLMError as e:
        log.warning("notice read failed: %s", type(e).__name__)
        st.error(t("err_generic", lang))
        return

    render_result(tr, cache["explanations"].get(lang), lang)
    st.image(cache["prepared"], caption=t("photo_shown", lang), width=240)


def _original(text: str) -> None:
    with st.container(border=True):
        st.markdown(plain(text))


def render_result(tr: Transcription, ex: Explanation | None, lang: str) -> None:
    if tr.clarity == "unclear":
        st.warning(f"**{t('unclear_title', lang)}**\n\n{t('unclear_tips', lang)}")
        if tr.text_read:
            st.caption(t("unclear_partial_text", lang))
            _original(tr.text_read)
        st.caption(t("notice_disclaimer", lang))
        return

    if tr.is_safety:
        # Safety notices: the original words come first, never only a summary.
        st.error(f"**{t('safety_title', lang)}**\n\n{plain(tr.text_read)}")

    if tr.clarity == "partial":
        st.info(t("partial_note", lang))

    st.subheader(t("explanation_title", lang))
    if ex is None or ex.text is None:
        st.warning(t("explain_failed", lang))
    else:
        with st.container(border=True):
            st.markdown(plain(ex.text))
        if ex.number_warning:
            st.warning(t("check_numbers", lang, nums=", ".join(sorted(ex.number_warning, key=int))))

    if not tr.is_safety:
        with st.expander(t("original_text", lang), expanded=True):
            _original(tr.text_read)

    st.caption(t("notice_disclaimer", lang))
