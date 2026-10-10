import pytest

from ghat_guide.safety import (
    clarity_verdict,
    is_safety_notice,
    normalise,
    numbers_in,
    unsupported_numbers,
)


def test_normalise_digits_nukta_case_space():
    assert normalise("घाट  ५\nपर") == "घाट 5 पर"
    assert normalise("ज़रूरी") == normalise("जरूरी")
    assert normalise("Deep WATER") == "deep water"


@pytest.mark.parametrize(
    "text",
    [
        "घाट 3 के आगे गहरा पानी है",              # hi: deep water
        "बैरिकेड के पार न जाएं",                 # barricade
        "आगे जाना मना है",                        # prohibited
        "डूबने का खतरा, बच्चों को पास रखें",       # drowning risk
        "खोया-पाया केंद्र घाट 2 पर",                # lost and found
        "ई पानी गहिर बा, खतरा बा",                 # bho: खतरा
        "आपातकाल में पुलिस बूथ पर संपर्क करू",     # mai: emergency / police
        "DANGER: Deep water beyond this point",
        "No entry after barricade",
        "NDRF team on duty",
    ],
)
def test_safety_notices_detected(text):
    assert is_safety_notice(text)


@pytest.mark.parametrize(
    "text",
    [
        "डूबते सूर्य को अर्घ्य शाम को दिया जाएगा",   # setting sun is not "drowning"
        "छठ पर्व धूमधाम से मनाया जाएगा",            # "मनाया" is not "मना है"
        "प्रसाद वितरण घाट 4 पर",
        "Welcome to Chhath Ghat",
        "",
    ],
)
def test_ordinary_notices_not_flagged(text):
    assert not is_safety_notice(text)


@pytest.mark.parametrize(
    "text,model,expected",
    [
        ("घाट 5 पर अर्घ्य की व्यवस्था है", "clear", "clear"),
        ("घाट 5 पर अर्घ्य की व्यवस्था है", "partial", "partial"),
        ("घाट 5 पर [?] की व्यवस्था है", "clear", "partial"),
        ("घाट 5 पर अर्घ्य की व्यवस्था है", "unclear", "unclear"),
        ("घाट", "clear", "unclear"),                              # too short
        ("[?] [?] पर [?] है", "partial", "unclear"),               # mostly unreadable
        ("", "clear", "unclear"),
    ],
)
def test_clarity_verdict(text, model, expected):
    assert clarity_verdict(text, model, min_chars=8, max_unknown_ratio=0.30) == expected


def test_numbers_in_handles_devanagari_and_leading_zeros():
    assert numbers_in("घाट ५, समय 05:30") == {"5", "30"}


def test_unsupported_numbers_catches_invented_ghat():
    text = "घाट 5 पर गहरा पानी है"
    assert unsupported_numbers("घाट 5 पर पानी गहरा है।", text) == set()
    assert unsupported_numbers("घाट 7 पर पानी गहरा है।", text) == {"7"}


def test_unsupported_numbers_devanagari_digits_match_ascii():
    assert unsupported_numbers("घाट 5 पर जाएँ", "घाट ५ पर") == set()
