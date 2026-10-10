"""LLM gateway: the only module that talks to Ollama (LLD §3.1).

Everything else depends on LLMGateway, so the model can be swapped by config
and faked in tests by passing a stand-in `client`.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

import numpy as np

from .config import OllamaSettings

log = logging.getLogger(__name__)

# Streamlit runs each browser session in its own thread; one model call at a
# time keeps a laptop CPU from thrashing when several phones ask at once.
_LOCK = threading.Lock()


class LLMError(Exception):
    pass


class LLMUnavailable(LLMError):
    """Ollama is not running, or a model has not been pulled."""


class LLMTimeout(LLMError):
    pass


class LLMBadOutput(LLMError):
    """The model did not return valid JSON for the schema, even after retries."""


def _default_client(s: OllamaSettings):
    import ollama

    return ollama.Client(host=s.host, timeout=s.timeout_s)


def _model_names(list_response: Any) -> set[str]:
    models = getattr(list_response, "models", None)
    if models is None and isinstance(list_response, dict):
        models = list_response.get("models", [])
    names = set()
    for m in models or []:
        name = getattr(m, "model", None) or (m.get("model") if isinstance(m, dict) else None)
        if name:
            names.add(name)
            if name.endswith(":latest"):
                names.add(name[: -len(":latest")])
    return names


class LLMGateway:
    def __init__(self, s: OllamaSettings, client: Any | None = None):
        self.s = s
        self.client = client if client is not None else _default_client(s)

    # -- errors ---------------------------------------------------------------

    def _translate(self, e: Exception, model: str) -> LLMError:
        import httpx

        if isinstance(e, LLMError):
            return e
        if isinstance(e, httpx.TimeoutException):
            return LLMTimeout(f"{model} took longer than {self.s.timeout_s}s")
        if isinstance(e, (httpx.ConnectError, ConnectionError)):
            return LLMUnavailable(f"cannot reach Ollama at {self.s.host}")
        status = getattr(e, "status_code", None)
        if status == 404:
            return LLMUnavailable(f"model not found: run `ollama pull {model}`")
        return LLMError(f"{type(e).__name__}: {e}")

    # -- health ---------------------------------------------------------------

    def health(self) -> dict[str, bool]:
        try:
            names = _model_names(self.client.list())
        except Exception as e:  # noqa: BLE001 — any failure means "not healthy"
            log.warning("ollama health check failed: %s", type(e).__name__)
            return {"server": False, "vision_model": False, "text_model": False, "embed_model": False}
        return {
            "server": True,
            "vision_model": self.s.vision_model in names,
            "text_model": self.s.text_model in names,
            "embed_model": self.s.embed_model in names,
        }

    def warm_up(self) -> None:
        """Load the text model into memory so the first real request is fast."""
        try:
            with _LOCK:
                self.client.chat(
                    model=self.s.text_model,
                    messages=[{"role": "user", "content": "ok"}],
                    options={"num_predict": 1},
                    keep_alive=self.s.keep_alive,
                )
        except Exception as e:  # noqa: BLE001
            log.warning("warm-up failed: %s", self._translate(e, self.s.text_model))

    # -- calls ----------------------------------------------------------------

    def chat_json(
        self,
        *,
        model: str,
        system: str,
        user: str,
        schema: dict,
        temperature: float,
        images: list[bytes] | None = None,
    ) -> dict:
        user_msg: dict[str, Any] = {"role": "user", "content": user}
        if images:
            user_msg["images"] = images
        messages = [{"role": "system", "content": system}, user_msg]
        required = schema.get("required", [])

        attempts = 1 + max(0, self.s.max_retries)
        last_error = "no attempt"
        for attempt in range(1, attempts + 1):
            t0 = time.monotonic()
            try:
                with _LOCK:
                    resp = self.client.chat(
                        model=model,
                        messages=messages,
                        format=schema,
                        options={"temperature": temperature},
                        keep_alive=self.s.keep_alive,
                    )
            except Exception as e:  # noqa: BLE001
                raise self._translate(e, model) from e
            log.info("chat model=%s attempt=%d took=%.1fs", model, attempt, time.monotonic() - t0)

            content = _message_content(resp)
            try:
                data = json.loads(content)
            except (json.JSONDecodeError, TypeError) as e:
                last_error = f"invalid JSON: {e}"
                continue
            if not isinstance(data, dict):
                last_error = "JSON is not an object"
                continue
            missing = [k for k in required if k not in data]
            if missing:
                last_error = f"missing keys: {missing}"
                continue
            return data

        raise LLMBadOutput(f"{model}: {last_error}")

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        try:
            with _LOCK:
                resp = self.client.embed(model=self.s.embed_model, input=texts, keep_alive=self.s.keep_alive)
        except Exception as e:  # noqa: BLE001
            raise self._translate(e, self.s.embed_model) from e
        vectors = getattr(resp, "embeddings", None)
        if vectors is None and isinstance(resp, dict):
            vectors = resp.get("embeddings")
        arr = np.asarray(vectors, dtype=np.float32)
        if arr.ndim != 2 or arr.shape[0] != len(texts):
            raise LLMBadOutput(f"unexpected embedding shape {arr.shape}")
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        return arr / np.maximum(norms, 1e-12)


def _message_content(resp: Any) -> str:
    msg = getattr(resp, "message", None)
    if msg is None and isinstance(resp, dict):
        msg = resp.get("message")
    if msg is None:
        return ""
    content = getattr(msg, "content", None)
    if content is None and isinstance(msg, dict):
        content = msg.get("content")
    return content or ""
