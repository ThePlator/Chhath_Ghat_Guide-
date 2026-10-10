"""Parse kb/*.md into searchable chunks (LLD §3.5).

A note without `checked_by` is skipped: unchecked text never reaches users.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import frontmatter

log = logging.getLogger(__name__)

REQUIRED = ("id", "title_hi", "keywords", "checked_by", "checked_on")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str  # f"{note_id}#{section_slug}"
    note_id: str
    note_title: str  # title_hi
    section: str  # H2 heading text
    text: str
    keywords: tuple[str, ...]
    checked_by: str
    checked_on: str


@dataclass(frozen=True)
class KBLoad:
    chunks: list[Chunk]
    notes_loaded: list[str]
    notes_unchecked: list[str]
    notes_invalid: list[str]


def _slug(heading: str, n: int) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")
    return s or f"s{n}"


def _split_sections(body: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    heading, lines = None, []
    for line in body.splitlines():
        if line.startswith("## "):
            if heading is not None:
                sections.append((heading, "\n".join(lines).strip()))
            heading, lines = line[3:].strip(), []
        elif heading is not None:
            lines.append(line)
    if heading is not None:
        sections.append((heading, "\n".join(lines).strip()))
    return [(h, t) for h, t in sections if t]


def note_files(kb_dir: str | Path) -> list[Path]:
    return sorted(p for p in Path(kb_dir).glob("*.md") if p.name.lower() != "readme.md")


def load_kb(kb_dir: str | Path = "kb", include_unchecked: bool = False) -> KBLoad:
    """`include_unchecked` is for offline tuning (tests/eval) only, never for the app."""
    chunks: list[Chunk] = []
    loaded, unchecked, invalid = [], [], []
    seen_ids: set[str] = set()

    for path in note_files(kb_dir):
        try:
            post = frontmatter.load(path)
        except Exception as e:  # noqa: BLE001 — a broken note must not take the app down
            log.warning("note %s not parsed: %s", path.name, type(e).__name__)
            invalid.append(path.name)
            continue
        meta = post.metadata
        missing = [k for k in REQUIRED if k not in meta]
        note_id = str(meta.get("id") or "")
        keywords = meta.get("keywords")
        if missing or not _ID_RE.match(note_id) or note_id in seen_ids or not isinstance(keywords, list):
            log.warning("note %s invalid (missing=%s, id=%r)", path.name, missing, note_id)
            invalid.append(path.name)
            continue
        seen_ids.add(note_id)

        checked_by = str(meta.get("checked_by") or "").strip()
        checked_on = str(meta.get("checked_on") or "").strip()
        if not (checked_by and checked_on):
            unchecked.append(path.name)
            if not include_unchecked:
                continue

        sections = _split_sections(post.content)
        if not sections:
            invalid.append(path.name)
            continue
        loaded.append(path.name)
        kw = tuple(str(k) for k in keywords)
        used_slugs: set[str] = set()
        for n, (heading, text) in enumerate(sections, 1):
            slug = _slug(heading, n)
            if slug in used_slugs:
                slug = f"{slug}-{n}"
            used_slugs.add(slug)
            chunks.append(
                Chunk(
                    chunk_id=f"{note_id}#{slug}",
                    note_id=note_id,
                    note_title=str(meta["title_hi"]),
                    section=heading,
                    text=text,
                    keywords=kw,
                    checked_by=checked_by,
                    checked_on=checked_on,
                )
            )
    return KBLoad(chunks, loaded, unchecked, invalid)


def kb_fingerprint(chunks: list[Chunk]) -> str:
    """Changes whenever any loaded chunk's content or metadata changes."""
    h = hashlib.sha256()
    for c in chunks:
        for part in (c.chunk_id, c.note_title, c.section, c.text, "|".join(c.keywords), c.checked_by, c.checked_on):
            h.update(part.encode("utf-8"))
            h.update(b"\x00")
    return h.hexdigest()
