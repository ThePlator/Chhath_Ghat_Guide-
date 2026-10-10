from ghat_guide.emergency import load_emergency


def test_shipped_file_has_messages_and_no_numbers():
    info = load_emergency()
    assert set(info.message) >= {"hi", "bho", "mai"}
    assert info.contacts == ()


def test_contacts_parsed_and_invalid_skipped(tmp_path):
    p = tmp_path / "e.yaml"
    p.write_text(
        "message: {hi: 'पास के बूथ पर जाएँ'}\n"
        "contacts:\n"
        "  - {label: 'Ghat 5 police booth', phone: '100', where: 'main steps'}\n"
        "  - {phone: '123'}\n"
        "  - 'junk'\n",
        encoding="utf-8",
    )
    info = load_emergency(p)
    assert [c.label for c in info.contacts] == ["Ghat 5 police booth"]
    assert info.message_for("bho") == "पास के बूथ पर जाएँ"  # falls back to Hindi


def test_missing_or_broken_file_is_safe(tmp_path):
    assert load_emergency(tmp_path / "nope.yaml").contacts == ()
    bad = tmp_path / "bad.yaml"
    bad.write_text("message: [unclosed", encoding="utf-8")
    assert load_emergency(bad).message == {}
