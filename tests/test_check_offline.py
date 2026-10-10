import shutil
import socket
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_offline as co  # noqa: E402

from ghat_guide.config import OllamaSettings, load_settings  # noqa: E402
from ghat_guide.llm import LLMGateway  # noqa: E402
from tests.fakes import SAMPLE_NOTES, FakeClient, write_kb  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def statuses(checks):
    return {c.name: c.status for c in checks}


def test_models_ok_and_missing():
    s = load_settings()
    ok = co.check_models(LLMGateway(OllamaSettings(), client=FakeClient()), s, deep=False)
    assert all(c.status == co.OK for c in ok)
    assert [c.name for c in ok].count("Model gemma3:4b") == 1  # same vision and text model listed once
    missing = co.check_models(LLMGateway(OllamaSettings(), client=FakeClient(models=("gemma3:4b",))), s, deep=False)
    bad = [c for c in missing if c.status == co.FAIL]
    assert [c.name for c in bad] == ["Model nomic-embed-text"]
    assert "ollama pull nomic-embed-text" in bad[0].fix


def test_models_deep_times_requests():
    s = load_settings()
    client = FakeClient(chat_reply={"ok": True})
    checks = co.check_models(LLMGateway(OllamaSettings(), client=client), s, deep=True)
    st = statuses(checks)
    assert st["Text model answers"] == co.OK and st["Embedding model answers"] == co.OK


def test_ollama_down_is_a_failure():
    class Down(FakeClient):
        def list(self):
            raise ConnectionError("down")

    checks = co.check_models(LLMGateway(OllamaSettings(), client=Down()), load_settings(), deep=True)
    assert checks == [co.Check("Ollama running", co.FAIL, "not reachable at http://127.0.0.1:11434", "start it: ollama serve")]


def test_knowledge_base_states(tmp_path):
    base = load_settings()
    s = replace(base, ritual=replace(base.ritual, kb_dir=str(tmp_path / "kb"), index_path=str(tmp_path / "idx")))
    (tmp_path / "kb").mkdir()
    assert statuses(co.check_knowledge_base(s))["Ritual notes checked"] == co.WARN

    write_kb(tmp_path / "kb", SAMPLE_NOTES)
    st = statuses(co.check_knowledge_base(s))
    assert st["Ritual notes checked"] == co.OK and st["Ritual index built"] == co.WARN

    from ghat_guide.ritual.index import load_or_build
    from ghat_guide.ritual.kb_loader import load_kb

    load_or_build(load_kb(tmp_path / "kb").chunks, tmp_path / "idx", LLMGateway(OllamaSettings(), client=FakeClient()))
    assert statuses(co.check_knowledge_base(s))["Ritual index built"] == co.OK


def test_shipped_phone_pages_are_offline_only():
    assert co.check_phone_pages()[0].status == co.OK


def test_external_url_detected(tmp_path, monkeypatch):
    (tmp_path / "static").mkdir()
    for name in ("meeting_spot.html", "meeting_spot_strings.js"):
        shutil.copy(ROOT / "static" / name, tmp_path / "static" / name)
    (tmp_path / "static" / "extra.html").write_text('<script src="https://cdn.example.com/x.js"></script>', encoding="utf-8")
    monkeypatch.setattr(co, "ROOT", tmp_path)
    c = co.check_phone_pages()[0]
    assert c.status == co.FAIL and "cdn.example.com" in c.detail


def test_shipped_streamlit_config_without_https():
    st = statuses(co.check_streamlit_config(None))
    assert st == {"Streamlit usage stats off": co.OK}
    st = statuses(co.check_streamlit_config("192.168.137.1"))
    assert st["HTTPS enabled"] == co.FAIL


@pytest.mark.skipif(not shutil.which("openssl"), reason="openssl not installed")
def test_certificate_matches_ip(tmp_path):
    cert, key = tmp_path / "cert.pem", tmp_path / "key.pem"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "30", "-keyout", str(key),
         "-out", str(cert), "-subj", "/CN=t", "-addext", "subjectAltName=IP:192.168.137.1,DNS:localhost"],
        check=True, capture_output=True,
    )
    assert co.check_certificate(cert, key, "192.168.137.1").status == co.OK
    wrong = co.check_certificate(cert, key, "10.42.0.1")
    assert wrong.status == co.FAIL and "10.42.0.1" in wrong.fix
    assert co.check_certificate(tmp_path / "nope.pem", key, "192.168.137.1").status == co.FAIL


def test_ollama_exposure_detected():
    with socket.socket() as srv:
        srv.bind(("127.0.0.1", 0))
        srv.listen()
        port = srv.getsockname()[1]
        assert co.check_ollama_not_exposed("127.0.0.1", port).status == co.WARN
    assert co.check_ollama_not_exposed("127.0.0.1", port).status == co.OK


def test_emergency_card_warns_without_contacts():
    c = co.check_emergency_card()
    assert c.status == co.WARN and "never guess" in c.fix


def test_main_exit_codes(capsys):
    healthy = LLMGateway(OllamaSettings(), client=FakeClient())
    assert co.main([], llm=healthy) == 0  # warnings only (unchecked notes, no contacts)
    assert "Ready for the ghat" in capsys.readouterr().out
    assert co.main(["--hotspot-ip", "192.168.137.1"], llm=healthy) == 1  # HTTPS not set up
    with pytest.raises(SystemExit):
        co.main(["--hotspot-ip", "not-an-ip"], llm=healthy)
