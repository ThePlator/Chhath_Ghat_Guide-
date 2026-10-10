"""Pre-trip check: is this laptop ready to run the app at the ghat with no internet?

    python scripts/check_offline.py                         # laptop-only demo
    python scripts/check_offline.py --hotspot-ip 192.168.137.1
    python scripts/check_offline.py --hotspot-ip 192.168.137.1 --deep   # also time the models

Run it at home, with internet still on, so anything missing can be downloaded.
Exit code 0 = ready (warnings allowed), 1 = something must be fixed first.
"""

from __future__ import annotations

import argparse
import logging
import re
import socket
import ssl
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

OK, WARN, FAIL = "ok", "warn", "fail"
ICON = {OK: "✅", WARN: "⚠️ ", FAIL: "❌"}
SLOW_CHAT_S = 60
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}
_URL_RE = re.compile(r"""(?:https?:)?//([a-z0-9.-]+\.[a-z]{2,})""", re.I)


@dataclass
class Check:
    name: str
    status: str
    detail: str = ""
    fix: str = ""


# --------------------------------------------------------------------- checks

def check_python_packages() -> list[Check]:
    out = []
    for mod, pip_name in [("streamlit", "streamlit"), ("ollama", "ollama"), ("PIL", "pillow"),
                          ("numpy", "numpy"), ("yaml", "pyyaml"), ("frontmatter", "python-frontmatter")]:
        try:
            m = __import__(mod)
        except ImportError:
            out.append(Check(f"Python package {pip_name}", FAIL, "not installed", "pip install -r requirements.txt"))
            continue
        if mod == "streamlit":
            version = tuple(int(x) for x in re.findall(r"\d+", m.__version__)[:2])
            if version < (1, 65):
                out.append(Check("Streamlit version", FAIL, m.__version__, "pip install -U 'streamlit>=1.65'"))
                continue
    if not out:
        out.append(Check("Python packages", OK, "all installed"))
    return out


def check_models(llm, s, deep: bool) -> list[Check]:
    from ghat_guide.llm import LLMError

    h = llm.health()
    if not h["server"]:
        return [Check("Ollama running", FAIL, f"not reachable at {s.ollama.host}", "start it: ollama serve")]
    out = [Check("Ollama running", OK, s.ollama.host)]
    seen = set()
    for key, model in [("vision_model", s.ollama.vision_model), ("text_model", s.ollama.text_model),
                       ("embed_model", s.ollama.embed_model)]:
        if model in seen:  # vision and text are often the same model
            continue
        seen.add(model)
        if h[key]:
            out.append(Check(f"Model {model}", OK, "downloaded"))
        else:
            out.append(Check(f"Model {model}", FAIL, "not downloaded", f"ollama pull {model}   (needs internet: do it now)"))
    if not deep or any(c.status == FAIL for c in out):
        return out

    t0 = time.monotonic()
    try:
        llm.chat_json(model=s.ollama.text_model, system="Reply with JSON.", user='Return {"ok": true}.',
                      schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
                      temperature=0)
        took = time.monotonic() - t0
        status = WARN if took > SLOW_CHAT_S else OK
        out.append(Check("Text model answers", status, f"{took:.0f} s for a tiny request",
                         "" if status == OK else "slow: close other apps; keep the laptop plugged in"))
    except LLMError as e:
        out.append(Check("Text model answers", FAIL, str(e), "check `ollama run " + s.ollama.text_model + "`"))
    try:
        llm.embed(["search_query: test"])
        out.append(Check("Embedding model answers", OK))
    except LLMError as e:
        out.append(Check("Embedding model answers", FAIL, str(e), f"check `ollama pull {s.ollama.embed_model}`"))
    return out


def check_knowledge_base(s) -> list[Check]:
    from ghat_guide.config import project_path
    from ghat_guide.ritual.index import load_cached
    from ghat_guide.ritual.kb_loader import kb_fingerprint, load_kb

    kb = load_kb(project_path(s.ritual.kb_dir))
    out = []
    if kb.notes_invalid:
        out.append(Check("Ritual notes valid", FAIL, ", ".join(kb.notes_invalid), "fix the front matter (see kb/README.md)"))
    if not kb.chunks:
        out.append(Check("Ritual notes checked", WARN, f"0 checked, {len(kb.notes_unchecked)} unchecked — Ritual tab will be off",
                         "read the notes to an elder and fill checked_by / checked_on"))
        return out
    detail = f"{len(kb.notes_loaded)} checked"
    if kb.notes_unchecked:
        detail += f", {len(kb.notes_unchecked)} still unchecked (skipped)"
    out.append(Check("Ritual notes checked", OK, detail))
    cached = load_cached(project_path(s.ritual.index_path), kb_fingerprint(kb.chunks), s.ollama.embed_model)
    if cached is None:
        out.append(Check("Ritual index built", WARN, "missing or out of date",
                         "python scripts/build_index.py   (otherwise the app builds it on first use)"))
    else:
        out.append(Check("Ritual index built", OK, f"{len(cached.chunks)} sections"))
    return out


def check_phone_pages() -> list[Check]:
    """The pages phones load must not reach out to the internet."""
    static = ROOT / "static"
    needed = ["meeting_spot.html", "meeting_spot_strings.js"]
    missing = [n for n in needed if not (static / n).exists()]
    if missing:
        return [Check("Meeting Spot files", FAIL, "missing: " + ", ".join(missing), "restore them from git")]
    external = set()
    for p in static.glob("*"):
        if p.suffix in {".html", ".js", ".css"}:
            for host in _URL_RE.findall(p.read_text(encoding="utf-8")):
                if host.lower() not in LOCAL_HOSTS:
                    external.add(f"{p.name}: {host}")
    if external:
        return [Check("Phone pages are offline-only", FAIL, "; ".join(sorted(external)), "remove external links/assets")]
    return [Check("Phone pages are offline-only", OK, "no external URLs in static/")]


def _streamlit_config() -> dict:
    p = ROOT / ".streamlit" / "config.toml"
    with open(p, "rb") as f:
        return tomllib.load(f)


def check_streamlit_config(hotspot_ip: str | None) -> list[Check]:
    cfg = _streamlit_config()
    out = []
    if cfg.get("browser", {}).get("gatherUsageStats", True):
        out.append(Check("Streamlit usage stats off", FAIL, "gatherUsageStats is on", "set [browser] gatherUsageStats = false"))
    else:
        out.append(Check("Streamlit usage stats off", OK))
    if not cfg.get("server", {}).get("enableStaticServing", False):
        out.append(Check("Static serving on", FAIL, "needed for the full-screen Meeting Spot page",
                         "set [server] enableStaticServing = true"))
    if hotspot_ip is None:
        return out

    server = cfg.get("server", {})
    cert, key = server.get("sslCertFile"), server.get("sslKeyFile")
    if not (cert and key):
        out.append(Check("HTTPS enabled", FAIL, "sslCertFile / sslKeyFile not set — phones will block GPS and compass",
                         f"scripts/make_cert.sh {hotspot_ip}, then uncomment them in .streamlit/config.toml"))
        return out
    out.append(check_certificate(ROOT / cert, ROOT / key, hotspot_ip))
    return out


def _decode_cert(path: Path) -> dict:
    # CPython helper that parses a PEM certificate without third-party packages.
    return ssl._ssl._test_decode_cert(str(path))  # type: ignore[attr-defined]


def check_certificate(cert: Path, key: Path, ip: str) -> Check:
    if not cert.exists() or not key.exists():
        return Check("HTTPS certificate", FAIL, "certificate or key file missing", f"scripts/make_cert.sh {ip}")
    try:
        info = _decode_cert(cert)
    except (ssl.SSLError, OSError, AttributeError) as e:
        return Check("HTTPS certificate", WARN, f"could not read it ({type(e).__name__})", "check it opens on a phone")
    sans = {v for k, v in info.get("subjectAltName", ()) if k in ("IP Address", "DNS")}
    if ip not in sans:
        return Check("HTTPS certificate", FAIL, f"made for {', '.join(sorted(sans)) or 'unknown'}, not {ip}",
                     f"scripts/make_cert.sh {ip}   (the hotspot IP changed?)")
    not_after = datetime.fromtimestamp(ssl.cert_time_to_seconds(info["notAfter"]), timezone.utc)
    days = (not_after - datetime.now(timezone.utc)).days
    if days < 0:
        return Check("HTTPS certificate", FAIL, "expired", f"scripts/make_cert.sh {ip}")
    if days < 3:
        return Check("HTTPS certificate", WARN, f"expires in {days} day(s)", f"scripts/make_cert.sh {ip}")
    return Check("HTTPS certificate", OK, f"valid for {ip}, {days} days left")


def check_ollama_not_exposed(ip: str, port: int = 11434, timeout: float = 1.0) -> Check:
    """Phones should reach the app only, never the model server directly."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return Check("Ollama hidden from phones", WARN, f"port {port} is open on {ip}",
                         "unset OLLAMA_HOST (or set it to 127.0.0.1) and restart Ollama")
    except OSError:
        return Check("Ollama hidden from phones", OK, f"not reachable on {ip}:{port}")


def check_emergency_card() -> Check:
    from ghat_guide.emergency import load_emergency

    info = load_emergency()
    if not info.message:
        return Check("Emergency card", FAIL, "config/emergency.yaml has no message", "restore it from git")
    if not info.contacts:
        return Check("Emergency card", WARN, "no local contacts (the general message still shows)",
                     "on the day, add VERIFIED booth details to config/emergency.yaml — never guess numbers")
    return Check("Emergency card", OK, f"{len(info.contacts)} local contact(s)")


# ----------------------------------------------------------------------- main

def run_checks(hotspot_ip: str | None, deep: bool, llm=None) -> list[Check]:
    from ghat_guide.config import load_settings
    from ghat_guide.llm import LLMGateway

    s = load_settings()
    checks = check_python_packages()
    llm = llm or LLMGateway(s.ollama)
    checks += check_models(llm, s, deep)
    checks += check_knowledge_base(s)
    checks += check_phone_pages()
    checks += check_streamlit_config(hotspot_ip)
    if hotspot_ip:
        checks.append(check_ollama_not_exposed(hotspot_ip))
    checks.append(check_emergency_card())
    return checks


def report(checks: list[Check]) -> int:
    for c in checks:
        line = f"{ICON[c.status]} {c.name}"
        if c.detail:
            line += f" — {c.detail}"
        print(line)
        if c.fix and c.status != OK:
            print(f"      → {c.fix}")
    fails = sum(c.status == FAIL for c in checks)
    warns = sum(c.status == WARN for c in checks)
    print()
    if fails:
        print(f"Not ready: {fails} problem(s) to fix, {warns} warning(s).")
        return 1
    print(f"Ready for the ghat ({warns} warning(s)). Now turn internet off and try all three tabs once.")
    return 0


def main(argv: list[str] | None = None, llm=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hotspot-ip", help="the laptop's hotspot IP; also checks HTTPS for phones")
    ap.add_argument("--deep", action="store_true", help="also send a tiny request to each model and time it")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.ERROR)  # the report below says everything; keep library warnings out
    if args.hotspot_ip and not re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", args.hotspot_ip):
        ap.error("--hotspot-ip must look like 192.168.137.1")
    return report(run_checks(args.hotspot_ip, args.deep, llm))


if __name__ == "__main__":
    sys.exit(main())
