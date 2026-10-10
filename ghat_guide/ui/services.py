"""Process-wide objects, created once and shared by every browser session."""

from __future__ import annotations

import threading

import numpy as np

import streamlit as st

from ..config import Settings, load_settings, project_path
from ..emergency import EmergencyInfo, load_emergency
from ..llm import LLMGateway
from ..notice_reader import NoticeReader
from ..ritual.answerer import RitualHelper
from ..ritual.index import KBIndex, load_or_build
from ..ritual.kb_loader import load_kb
from ..ritual.retriever import Retriever


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


@st.cache_resource(show_spinner=False)
def get_ritual_helper() -> RitualHelper:
    """Loads checked notes and their embeddings. Raises LLMError if embedding
    fails; nothing is cached then, so the next page load retries."""
    s = get_settings()
    llm = get_llm()
    chunks = load_kb(project_path(s.ritual.kb_dir)).chunks
    if chunks:
        index, _ = load_or_build(chunks, project_path(s.ritual.index_path), llm)
    else:
        index = KBIndex([], np.zeros((0, 0), np.float32), "", s.ollama.embed_model)
    return RitualHelper(Retriever(index, llm, s.ritual), llm, s.ritual, s.ollama)


@st.cache_data(ttl=30, show_spinner=False)
def get_health() -> dict[str, bool]:
    return get_llm().health()


@st.cache_data(ttl=60, show_spinner=False)
def get_emergency() -> EmergencyInfo:
    return load_emergency()
