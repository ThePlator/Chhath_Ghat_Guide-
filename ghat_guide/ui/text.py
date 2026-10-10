"""Show model and note text as plain words, never as Markdown formatting or links."""

from __future__ import annotations

import re

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]<>()#+\-.!|~])")


def md_escape(text: str) -> str:
    return _MD_SPECIAL.sub(r"\\\1", text)


def plain(text: str) -> str:
    """Escaped Markdown that keeps the text's own line breaks."""
    return "  \n".join(md_escape(line) for line in text.splitlines())
