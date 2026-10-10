"""Build (or refresh) the ritual knowledge-base index before going offline.

    python scripts/build_index.py

Only notes with `checked_by` and `checked_on` filled in are indexed.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ghat_guide.config import load_settings, project_path  # noqa: E402
from ghat_guide.llm import LLMError, LLMGateway  # noqa: E402
from ghat_guide.ritual.index import load_or_build  # noqa: E402
from ghat_guide.ritual.kb_loader import load_kb  # noqa: E402


def main(llm: LLMGateway | None = None) -> int:
    s = load_settings()
    kb = load_kb(project_path(s.ritual.kb_dir))
    print(f"Notes checked and loaded: {len(kb.notes_loaded)}  ({len(kb.chunks)} sections)")
    if kb.notes_unchecked:
        print(f"Skipped, not checked yet ({len(kb.notes_unchecked)}): {', '.join(kb.notes_unchecked)}")
    if kb.notes_invalid:
        print(f"Skipped, invalid front matter ({len(kb.notes_invalid)}): {', '.join(kb.notes_invalid)}")
    if not kb.chunks:
        print("Nothing to index. Have an elder check the notes and fill `checked_by` / `checked_on` (see kb/README.md).")
        return 1

    llm = llm or LLMGateway(s.ollama)
    try:
        index, rebuilt = load_or_build(kb.chunks, project_path(s.ritual.index_path), llm)
    except LLMError as e:
        print(f"Could not build the index: {e}")
        return 2
    state = "built" if rebuilt else "already up to date"
    print(f"Index {state}: {len(index.chunks)} sections, model {index.embed_model}, saved to {s.ritual.index_path}.*")
    return 0


if __name__ == "__main__":
    sys.exit(main())
