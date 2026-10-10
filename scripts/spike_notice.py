"""Phase 1 spike: can Gemma read a notice and explain it in hi / bho / mai?

Usage (on the laptop, with Ollama running and models pulled):

    python scripts/spike_notice.py                       # photos in tests/eval/notices/
    python scripts/spike_notice.py --photos ~/notices --langs hi,bho
    python scripts/spike_notice.py --vision-model gemma3:12b

Appends a report to tests/eval/notice_log.md with the text read, each
explanation, timings and empty score columns to fill in by hand.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ghat_guide import prompts  # noqa: E402
from ghat_guide.config import Settings, load_settings  # noqa: E402
from ghat_guide.imaging import ImageError, prepare_image  # noqa: E402
from ghat_guide.llm import LLMError, LLMGateway  # noqa: E402

PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
SLOW_PHOTO_S = 120  # plan.md go/no-go threshold


@dataclass
class PhotoResult:
    name: str
    text_read: str = ""
    script: str = ""
    clarity: str = ""
    transcribe_s: float = 0.0
    explanations: dict[str, str] = field(default_factory=dict)
    explain_s: dict[str, float] = field(default_factory=dict)
    error: str = ""


def find_photos(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in PHOTO_EXTS)


def run_photo(llm: LLMGateway, s: Settings, path: Path, langs: list[str]) -> PhotoResult:
    r = PhotoResult(name=path.name)
    try:
        img = prepare_image(path.read_bytes(), s.notice.max_image_px, s.notice.jpeg_quality)
    except ImageError as e:
        r.error = f"image: {e}"
        return r

    t0 = time.monotonic()
    try:
        t = llm.chat_json(
            model=s.ollama.vision_model,
            system=prompts.SYS_TRANSCRIBE,
            user=prompts.USER_TRANSCRIBE,
            schema=prompts.TRANSCRIBE_SCHEMA,
            temperature=s.notice.transcribe_temperature,
            images=[img],
        )
    except LLMError as e:
        r.error = f"transcribe: {e}"
        return r
    r.transcribe_s = time.monotonic() - t0
    r.text_read, r.script, r.clarity = t["text_read"], t["script"], t["clarity"]

    if not r.text_read.strip():
        return r
    for lang in langs:
        t0 = time.monotonic()
        try:
            e = llm.chat_json(
                model=s.ollama.text_model,
                system=prompts.sys_explain(lang),
                user=prompts.user_explain(r.text_read),
                schema=prompts.EXPLAIN_SCHEMA,
                temperature=s.notice.explain_temperature,
            )
            r.explanations[lang] = e["explanation"]
        except LLMError as err:
            r.explanations[lang] = f"(error: {err})"
        r.explain_s[lang] = time.monotonic() - t0
    return r


def _fence(text: str) -> str:
    return "```text\n" + (text.strip() or "(empty)") + "\n```"


def render_report(results: list[PhotoResult], s: Settings, langs: list[str]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"## Run {now}",
        "",
        f"- Vision model: `{s.ollama.vision_model}` · text model: `{s.ollama.text_model}`",
        f"- Image long side: {s.notice.max_image_px} px · languages: {', '.join(langs)}",
        "",
        "### Summary",
        "",
        "| Photo | Clarity | Read (s) | " + " | ".join(f"{l} (s)" for l in langs) + " | Total (s) |",
        "| --- | --- | --- | " + " | ".join("---" for _ in langs) + " | --- |",
    ]
    totals = []
    for r in results:
        if r.error:
            lines.append(f"| {r.name} | error | | " + " | ".join("" for _ in langs) + " | |")
            continue
        total = r.transcribe_s + sum(r.explain_s.values())
        totals.append(total)
        cells = " | ".join(f"{r.explain_s[l]:.0f}" if l in r.explain_s else "–" for l in langs)
        lines.append(f"| {r.name} | {r.clarity} | {r.transcribe_s:.0f} | {cells} | {total:.0f} |")
    lines.append("")

    if totals:
        avg = sum(totals) / len(totals)
        lines.append(f"Average per photo: **{avg:.0f} s** over {len(totals)} photo(s).")
        if avg > SLOW_PHOTO_S:
            lines.append(
                f"⚠️ Slower than {SLOW_PHOTO_S} s: set `max_image_px = 768` in config/settings.toml and rerun."
            )
        lines.append("")

    for r in results:
        lines += [f"### {r.name}", ""]
        if r.error:
            lines += [f"Error: {r.error}", ""]
            continue
        lines += [f"Clarity (model): **{r.clarity}** · script: {r.script}", "", "**Text read**", "", _fence(r.text_read), ""]
        for lang in langs:
            if lang in r.explanations:
                lines += [f"**Explanation — {prompts.LANGUAGES[lang]['native']}**", "", _fence(r.explanations[lang]), ""]
        lines += [
            "**Scores (fill in, 1–5)**",
            "",
            "| Text accuracy | " + " | ".join(f"{l} quality" for l in langs) + " | Invented facts? | Notes |",
            "| --- | " + " | ".join("---" for _ in langs) + " | --- | --- |",
            "|  | " + " | ".join(" " for _ in langs) + " |  |  |",
            "",
        ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None, llm: LLMGateway | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--photos", type=Path, default=ROOT / "tests" / "eval" / "notices")
    ap.add_argument("--langs", default="hi,bho,mai")
    ap.add_argument("--out", type=Path, default=ROOT / "tests" / "eval" / "notice_log.md")
    ap.add_argument("--vision-model", help="override vision_model from settings")
    ap.add_argument("--max-px", type=int, help="override notice.max_image_px")
    args = ap.parse_args(argv)

    s = load_settings()
    if args.vision_model or args.max_px:
        from dataclasses import replace

        s = replace(
            s,
            ollama=replace(s.ollama, vision_model=args.vision_model or s.ollama.vision_model),
            notice=replace(s.notice, max_image_px=args.max_px or s.notice.max_image_px),
        )
    langs = [l.strip() for l in args.langs.split(",") if l.strip()]
    for l in langs:
        if l not in prompts.LANGUAGES:
            ap.error(f"unknown language {l!r}")

    if not args.photos.is_dir():
        ap.error(f"photo folder not found: {args.photos}")
    photos = find_photos(args.photos)
    if not photos:
        print(f"No photos in {args.photos}. Add .jpg/.png notice photos and rerun.")
        return 1

    llm = llm or LLMGateway(s.ollama)
    health = llm.health()
    if not health["server"]:
        print(f"Ollama is not reachable at {s.ollama.host}. Start it with `ollama serve`.")
        return 2
    missing = set()
    if not health["vision_model"]:
        missing.add(s.ollama.vision_model)
    if not health["text_model"]:
        missing.add(s.ollama.text_model)
    if missing:
        print("Model(s) not pulled: " + ", ".join(sorted(missing)))
        print("Run: " + " && ".join(f"ollama pull {m}" for m in sorted(missing)))
        return 2

    print(f"Warming up {s.ollama.text_model}…")
    llm.warm_up()

    results = []
    for i, p in enumerate(photos, 1):
        print(f"[{i}/{len(photos)}] {p.name} …", flush=True)
        r = run_photo(llm, s, p, langs)
        status = r.error or f"clarity={r.clarity}, read {r.transcribe_s:.0f}s, explain {sum(r.explain_s.values()):.0f}s"
        print(f"    {status}")
        results.append(r)

    report = render_report(results, s, langs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    header = "" if args.out.exists() else "# Notice Reader spike log\n\nOne section per run of `scripts/spike_notice.py`.\n\n"
    with open(args.out, "a", encoding="utf-8") as f:
        f.write(header + report)
    print(f"\nReport appended to {args.out}. Fill in the score tables, then decide the default language (plan.md 1.7).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
