"""Process-wide objects, created once and shared by every browser session."""

from __future__ import annotations

import threading

import streamlit as st

from ..config import Settings, load_settings
from ..emergency import EmergencyInfo, load_emergency
from ..llm import LLMGateway
from ..notice_reader import NoticeReader


@st.cache_resource
def get_settings() -> Settings:
    return load_settings()


@st.cache_resource
def get_llm() -> LLMGateway:
    llm = LLMGateway(get_settings().ollama)
    # Load the model in the background so the first photo doesn't pay for it.
    threading.Thread(target=llm.warm_up, name="ollama-warm-up", daemon=True).start()
    return llm


@st.cache_resource
def get_notice_reader() -> NoticeReader:
    s = get_settings()
    return NoticeReader(get_llm(), s.notice, s.ollama)


@st.cache_data(ttl=30, show_spinner=False)
def get_health() -> dict[str, bool]:
    return get_llm().health()


@st.cache_data(ttl=60, show_spinner=False)
def get_emergency() -> EmergencyInfo:
    return load_emergency()
