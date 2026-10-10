from ghat_guide.ritual.kb_loader import kb_fingerprint, load_kb
from tests.fakes import SAMPLE_NOTES, note, write_kb


def test_sections_become_chunks(tmp_path):
    kb = load_kb(write_kb(tmp_path / "kb", SAMPLE_NOTES))
    assert kb.notes_loaded == ["01.md", "02.md", "03.md"]
    ids = [c.chunk_id for c in kb.chunks]
    assert len(ids) == len(set(ids)) == 4
    k = [c for c in kb.chunks if c.note_id == "kharna"]
    assert [c.section for c in k] == ["क्या होता है", "इसके बाद"]
    assert k[0].note_title == "खरना" and k[0].checked_by == "Nani" and k[0].checked_on == "2026-10-10"
    assert "खीर" in k[0].keywords


def test_unchecked_notes_skipped_unless_asked(tmp_path):
    d = write_kb(tmp_path / "kb", [SAMPLE_NOTES[0], note("x", "एक्स", ["क"], [("अ", "ब")], checked=False)])
    kb = load_kb(d)
    assert kb.notes_unchecked == ["02.md"]
    assert {c.note_id for c in kb.chunks} == {"kharna"}
    assert {c.note_id for c in load_kb(d, include_unchecked=True).chunks} == {"kharna", "x"}


def test_invalid_notes_skipped(tmp_path):
    d = write_kb(
        tmp_path / "kb",
        [
            SAMPLE_NOTES[0],
            "---\nid: Bad ID\ntitle_hi: x\nkeywords: [a]\nchecked_by: a\nchecked_on: b\n---\n## a\nb\n",
            "---\ntitle_hi: no id\n---\n## a\nb\n",
            SAMPLE_NOTES[0],  # duplicate id
            "---\nid: [unclosed\n---\n",
        ],
    )
    (d / "README.md").write_text("# not a note", encoding="utf-8")
    kb = load_kb(d)
    assert kb.notes_loaded == ["01.md"]
    assert sorted(kb.notes_invalid) == ["02.md", "03.md", "04.md", "05.md"]


def test_fingerprint_changes_with_content(tmp_path):
    d = write_kb(tmp_path / "kb", SAMPLE_NOTES)
    f1 = kb_fingerprint(load_kb(d).chunks)
    assert f1 == kb_fingerprint(load_kb(d).chunks)
    (d / "01.md").write_text(SAMPLE_NOTES[0].replace("रोटी बनती", "पूरी बनती"), encoding="utf-8")
    assert kb_fingerprint(load_kb(d).chunks) != f1


def test_shipped_notes_are_valid_and_unchecked():
    kb = load_kb("kb", include_unchecked=True)
    assert kb.notes_invalid == []
    assert len(kb.notes_loaded) >= 8
    # Drafts must not reach users until an elder checks them.
    assert load_kb("kb").chunks == [] or not kb.notes_unchecked
    for c in kb.chunks:
        assert "बजे" not in c.text, f"clock time in {c.chunk_id}"
    assert any(c.section == "परिवारों में अंतर" for c in kb.chunks)
