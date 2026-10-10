"""Prompt templates and JSON output schemas (LLD §4).

Instructions are in English (Gemma follows them most reliably); the output
language is stated explicitly. Style examples steer Bhojpuri / Maithili away
from drifting into Hindi.

NOTE: the Bhojpuri and Maithili example sentences are drafts and must be
checked by a native speaker before the demo.
"""

from __future__ import annotations

LANGUAGES: dict[str, dict[str, str]] = {
    "hi": {"name": "Hindi", "native": "हिन्दी"},
    "bho": {"name": "Bhojpuri", "native": "भोजपुरी"},
    "mai": {"name": "Maithili", "native": "मैथिली"},
}

STYLE_EXAMPLES: dict[str, str] = {
    "hi": (
        "Example of the style to use:\n"
        "घाट पर बहुत भीड़ है। बच्चों का हाथ पकड़कर रखें।"
    ),
    "bho": (
        "Write in Bhojpuri, not Hindi. Example of the style to use:\n"
        "घाट पर बहुत भीड़ बा। लइकन के हाथ पकड़ के राखीं।"
    ),
    "mai": (
        "Write in Maithili, not Hindi. Example of the style to use:\n"
        "घाट पर बहुत भीड़ अछि। बच्चा सभक हाथ पकड़ने रहू।"
    ),
}


def _lang(lang: str) -> dict[str, str]:
    if lang not in LANGUAGES:
        raise ValueError(f"unknown language {lang!r}; expected one of {list(LANGUAGES)}")
    return LANGUAGES[lang]


# -- 4.1 Transcribe (vision) --------------------------------------------------

SYS_TRANSCRIBE = """\
You read photos of public notices, banners and signs at a river ghat in Bihar, India.
Copy the text exactly as written, in its original script and language.
- Do not translate, summarise or correct spelling.
- Keep line breaks.
- Write [?] for any word you cannot read with confidence.
- Do not guess numbers, times or ghat numbers; if unsure, write [?].
- If there is no readable text, return an empty text_read.
Rate clarity: "clear" (all text readable), "partial" (some words unreadable),
"unclear" (most text unreadable or no notice in the photo)."""

USER_TRANSCRIBE = "Read all text in this photo."

TRANSCRIBE_SCHEMA = {
    "type": "object",
    "properties": {
        "text_read": {"type": "string"},
        "script": {"type": "string", "enum": ["devanagari", "latin", "mixed", "other"]},
        "clarity": {"type": "string", "enum": ["clear", "partial", "unclear"]},
    },
    "required": ["text_read", "script", "clarity"],
}


# -- 4.2 Explain (text) -------------------------------------------------------

_SYS_EXPLAIN = """\
You explain public notices to a family at a Chhath ghat, in simple {name} ({native}).
Use short sentences an elder can follow when read aloud.
Rules:
- Use ONLY the notice text given. Do not add any time, date, ghat number,
  place, phone number or instruction that is not in it.
- If a part is marked [?], say that part could not be read.
- Keep any warning about water, barricades, crowding or emergencies first.
- Respectful tone. No jokes.
{style}"""

USER_EXPLAIN = '''\
Notice text:
"""
{text}
"""
Explain what this notice says and what the family should do.'''

EXPLAIN_SCHEMA = {
    "type": "object",
    "properties": {
        "explanation": {"type": "string"},
        "highlights": {
            "type": "object",
            "properties": {
                "times": {"type": "array", "items": {"type": "string"}},
                "ghat_numbers": {"type": "array", "items": {"type": "string"}},
                "dos": {"type": "array", "items": {"type": "string"}},
                "donts": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    "required": ["explanation"],
}


def sys_explain(lang: str) -> str:
    info = _lang(lang)
    return _SYS_EXPLAIN.format(name=info["name"], native=info["native"], style=STYLE_EXAMPLES[lang])


def user_explain(text: str) -> str:
    return USER_EXPLAIN.format(text=text)


# -- 4.3 Ritual answer (text) -------------------------------------------------

_SYS_RITUAL = """\
You help a family with questions about Chhath Puja. Answer in simple {name} ({native}).
Use ONLY the notes given between <notes> tags. Each note starts with its id in [brackets].
- If the notes do not answer the question, set found=false and leave answer empty.
- Do not add facts, dates, clock times or rules that are not in the notes.
- Customs differ between families and regions; never call one way the only correct way.
- List the ids of the notes you used in used_chunk_ids.
- Respectful tone. 2-5 short sentences.
{style}"""

USER_RITUAL = """\
<notes>
{context}
</notes>
Question: {question}"""

RITUAL_SCHEMA = {
    "type": "object",
    "properties": {
        "found": {"type": "boolean"},
        "answer": {"type": "string"},
        "used_chunk_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["found", "answer", "used_chunk_ids"],
}


def sys_ritual(lang: str) -> str:
    info = _lang(lang)
    return _SYS_RITUAL.format(name=info["name"], native=info["native"], style=STYLE_EXAMPLES[lang])


def user_ritual(context: str, question: str) -> str:
    return USER_RITUAL.format(context=context, question=question)
