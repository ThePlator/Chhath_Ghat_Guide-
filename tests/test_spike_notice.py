import json
import sys
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import spike_notice  # noqa: E402

from ghat_guide.config import OllamaSettings  # noqa: E402
from ghat_guide.llm import LLMGateway  # noqa: E402


class FakeClient:
    def __init__(self):
        self.calls = []

    def list(self):
        return SimpleNamespace(models=[SimpleNamespace(model="gemma3:4b")])

    def chat(self, **kw):
        self.calls.append(kw)
        if kw.get("options", {}).get("num_predict") == 1:  # warm-up
            return SimpleNamespace(message=SimpleNamespace(content=""))
        if "images" in kw["messages"][1]:
            body = {"text_read": "घाट 5 पर गहरा पानी है", "script": "devanagari", "clarity": "clear"}
        else:
            body = {"explanation": "घाट 5 पर पानी गहरा है, सावधान रहें।"}
        return SimpleNamespace(message=SimpleNamespace(content=json.dumps(body, ensure_ascii=False)))


def _photo(path: Path):
    buf = BytesIO()
    Image.new("RGB", (1600, 1200), "white").save(buf, format="JPEG")
    path.write_bytes(buf.getvalue())


def test_spike_writes_report(tmp_path):
    photos = tmp_path / "notices"
    photos.mkdir()
    _photo(photos / "n1.jpg")
    (photos / "notes.txt").write_text("ignored")
    out = tmp_path / "log.md"
    client = FakeClient()

    rc = spike_notice.main(
        ["--photos", str(photos), "--out", str(out), "--langs", "hi,bho"],
        llm=LLMGateway(OllamaSettings(), client=client),
    )

    assert rc == 0
    report = out.read_text(encoding="utf-8")
    assert report.startswith("# Notice Reader spike log")
    assert "### n1.jpg" in report
    assert "घाट 5 पर गहरा पानी है" in report
    assert "Explanation — भोजपुरी" in report
    # 1 warm-up + 1 transcribe + 2 explanations
    assert len(client.calls) == 4
    # image sent to the model was resized
    sent = Image.open(BytesIO(client.calls[1]["messages"][1]["images"][0]))
    assert max(sent.size) == 1024


def test_spike_reports_missing_model(tmp_path, capsys):
    photos = tmp_path / "notices"
    photos.mkdir()
    _photo(photos / "n1.jpg")

    class NoModels(FakeClient):
        def list(self):
            return SimpleNamespace(models=[])

    rc = spike_notice.main(["--photos", str(photos), "--out", str(tmp_path / "o.md")],
                           llm=LLMGateway(OllamaSettings(), client=NoModels()))
    assert rc == 2
    assert "ollama pull gemma3:4b" in capsys.readouterr().out
