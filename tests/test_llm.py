import json
from types import SimpleNamespace

import httpx
import numpy as np
import pytest

from ghat_guide.config import OllamaSettings
from ghat_guide.llm import LLMBadOutput, LLMGateway, LLMTimeout, LLMUnavailable

SCHEMA = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}


class FakeClient:
    def __init__(self, replies=(), models=(), raise_on_chat=None, embeddings=None):
        self.replies = list(replies)
        self.models = models
        self.raise_on_chat = raise_on_chat
        self.embeddings = embeddings
        self.calls = []

    def chat(self, **kw):
        self.calls.append(kw)
        if self.raise_on_chat:
            raise self.raise_on_chat
        return SimpleNamespace(message=SimpleNamespace(content=self.replies.pop(0)))

    def list(self):
        return SimpleNamespace(models=[SimpleNamespace(model=m) for m in self.models])

    def embed(self, **kw):
        return SimpleNamespace(embeddings=self.embeddings)


def gw(client, **kw):
    return LLMGateway(OllamaSettings(**kw), client=client)


def test_chat_json_returns_dict_and_passes_options():
    c = FakeClient([json.dumps({"a": "x"})])
    out = gw(c).chat_json(model="m", system="s", user="u", schema=SCHEMA, temperature=0.1, images=[b"img"])
    assert out == {"a": "x"}
    call = c.calls[0]
    assert call["format"] == SCHEMA
    assert call["options"] == {"temperature": 0.1}
    assert call["messages"][0] == {"role": "system", "content": "s"}
    assert call["messages"][1]["images"] == [b"img"]


def test_no_images_key_without_images():
    c = FakeClient([json.dumps({"a": "x"})])
    gw(c).chat_json(model="m", system="s", user="u", schema=SCHEMA, temperature=0)
    assert "images" not in c.calls[0]["messages"][1]


def test_retries_bad_json_then_succeeds():
    c = FakeClient(["not json", json.dumps({"a": "ok"})])
    assert gw(c, max_retries=1).chat_json(model="m", system="", user="", schema=SCHEMA, temperature=0) == {"a": "ok"}
    assert len(c.calls) == 2


def test_missing_key_exhausts_retries():
    c = FakeClient([json.dumps({"b": 1}), json.dumps({"b": 2})])
    with pytest.raises(LLMBadOutput, match="missing keys"):
        gw(c, max_retries=1).chat_json(model="m", system="", user="", schema=SCHEMA, temperature=0)


@pytest.mark.parametrize(
    "exc,expected",
    [
        (httpx.ConnectError("refused"), LLMUnavailable),
        (ConnectionError("Failed to connect to Ollama"), LLMUnavailable),
        (httpx.ReadTimeout("slow"), LLMTimeout),
    ],
)
def test_errors_translated(exc, expected):
    with pytest.raises(expected):
        gw(FakeClient(raise_on_chat=exc)).chat_json(model="m", system="", user="", schema=SCHEMA, temperature=0)


def test_model_not_pulled():
    import ollama

    err = ollama.ResponseError("model 'gemma3:4b' not found", status_code=404)
    with pytest.raises(LLMUnavailable, match="ollama pull gemma3:4b"):
        gw(FakeClient(raise_on_chat=err)).chat_json(model="gemma3:4b", system="", user="", schema=SCHEMA, temperature=0)


def test_health_matches_latest_tag():
    h = gw(FakeClient(models=["gemma3:4b", "nomic-embed-text:latest"])).health()
    assert h == {"server": True, "vision_model": True, "text_model": True, "embed_model": True}


def test_health_server_down():
    class Down(FakeClient):
        def list(self):
            raise httpx.ConnectError("refused")

    assert gw(Down()).health()["server"] is False


def test_embed_normalises():
    v = gw(FakeClient(embeddings=[[3.0, 4.0], [0.0, 2.0]])).embed(["a", "b"])
    np.testing.assert_allclose(np.linalg.norm(v, axis=1), [1.0, 1.0], rtol=1e-6)
    np.testing.assert_allclose(v[0], [0.6, 0.8], rtol=1e-6)


def test_embed_shape_mismatch():
    with pytest.raises(LLMBadOutput):
        gw(FakeClient(embeddings=[[1.0, 0.0]])).embed(["a", "b"])
