---
title: "Chhath Ghat Guide: an offline AI helper for the day the network dies at the ghat"
published: false
description: "Gemma 3 on one laptop, a Wi-Fi hotspot with no internet, and three small tools for families at crowded Chhath ghats: read notices, answer ritual questions, find your way back."
tags: devchallenge, hf26challenge, ai, opensource
cover_image: https://raw.githubusercontent.com/ThePlator/Chhath_Ghat_Guide-/main/docs/blog/images/cover.png
---

<!--
Before publishing:
1. Match the official Week 1 submission template: keep its first line and headings,
   and move the sections below under them.
2. Replace the two [FILL] blocks (field test + video) with what really happened.
3. Images load from the repo's main branch. If DEV doesn't show them, upload the files
   in docs/blog/images/ through the DEV editor and swap the URLs.
-->

*This is a submission for the [Hacktoberfest Open-Source AI Challenge — Week 1: Touch Grass](https://dev.to/devteam/join-the-hacktoberfest-open-source-ai-challenge-week-1-touch-grass-2450-in-prizes-across-17-4pom).*

## The ghat, the crowd and the dead network

Every year during **Chhath Puja**, lakhs of families walk down to the ghats of Bihar to offer *arghya* to the setting and the rising sun. Vratis stand waist-deep in the river, children hold their parents' hands, elders watch the water, and the songs carry across the steps.

And every year the same three things happen:

- Families get **separated** in the crowd.
- Notices about **deep water, barricades and timings** are hard to read in the press of people — and many elders are more at home in Bhojpuri or Maithili than in printed Hindi.
- **The mobile network jams.** Calls don't connect, messages don't send, and every app that needs the internet stops working — exactly when it's needed.

So I built a small helper for that moment. **Chhath Ghat Guide** runs on **one laptop at the ghat**. The laptop's Wi-Fi hotspot has **no internet at all**; family phones join it and open the app in a browser. The AI model, the notes and every photo stay at the ghat.

The screen is meant to be a few seconds of help, not the experience. The experience is the river, the sun and the family.

## What it does

Three tabs, one job each. (Screens are from the real app on a phone-sized browser; see the note under each image about what's test data.)

### 📜 सूचना पढ़ें — Notice Reader

Take a photo of a notice or banner. A local **Gemma 3 (4B)** vision model:

1. **copies the text exactly** as written, and
2. explains it in **simple Hindi, Bhojpuri or Maithili** — using *only* the text it just read.

The original words are always on screen. **Safety notices** (deep water, barricades, emergency) show the original text **first, inside a red box** — never only a summary. A blurry photo gets **"साफ़ नहीं पढ़ पाए"** ("couldn't read it clearly") and tips for a better photo, instead of a guess. And if the explanation contains a number that isn't in the notice — an invented ghat number or time — the app warns you.

![Notice Reader: a safety notice with the original text in red, an ordinary notice with a simple explanation, and a blurry photo the app refuses to guess at](https://raw.githubusercontent.com/ThePlator/Chhath_Ghat_Guide-/main/docs/blog/images/notice-reader.png)

*Real app screens; the notices are printed samples, and the read text and explanations shown are test data copied from the notices (screens with Gemma's own output will replace these after the field test).*

### 🪔 पूजा सहायक — Ritual Helper

Ask *"सूप में क्या रखते हैं?"* (what goes in the soop?) or *"खरना में क्या बनता है?"*. Answers come **only from ten short notes written by the family and checked by an elder** — not from the model's memory. Each answer:

- shows which note it came from and **who checked it**,
- ends with a reminder that **customs differ between families and regions**, and
- falls back to **"यह मेरे नोट्स में नहीं है — किसी बड़े से पूछें"** ("not in my notes — ask an elder") when the notes don't cover it.

Questions about **clock times, this year's dates or parking never reach the model at all** — they're sent to official notices and the panchang. An AI should not be the one telling a vrati what time to stand in the river.

![Ritual Helper: an answer with its source note, the "not in my notes" fallback, and a timing question sent to official notices](https://raw.githubusercontent.com/ThePlator/Chhath_Ghat_Guide-/main/docs/blog/images/ritual-helper.png)

*Real app screens; the answer text is test data copied from the note it cites. The notes are marked "डेमो — समीक्षा बाकी" (demo — review pending) because the elder review comes before the real demo.*

### 📍 मिलने की जगह — Meeting Spot

"**Save our spot**" stores the GPS position, a photo of a landmark and a note (*"नीला टेंट, घाट 5 की सीढ़ियों के पास"* — blue tent by the ghat 5 steps) **on the phone only**. "**Take me back**" shows the distance and an **arrow that turns with the phone's compass**.

GPS comes from satellites, not the mobile network, so this keeps working when calls don't — and because it runs entirely in the phone's browser, it keeps working even if the phone wanders out of the laptop's Wi-Fi. When you're within GPS error of the spot, the arrow would just be noise, so it switches to *"आप बहुत पास हैं — फोटो वाली निशानी देखें"* (you're very close — look for the landmark in the photo). The spot deletes itself at midnight.

![Meeting Spot: saved spot with landmark photo, the compass arrow showing about 130 m north-east, and the "you're very close" state](https://raw.githubusercontent.com/ThePlator/Chhath_Ghat_Guide-/main/docs/blog/images/meeting-spot.png)

*Real app screens with emulated GPS and compass (the landmark is a drawing).*

An **emergency card** sits on every screen and sends people to the nearest police or volunteer booth. The app ships with **no phone numbers** — organisers add verified ones on the day; a made-up number at a crowded river is worse than none.

## How it works offline

![Architecture: phones join the laptop's hotspot; the Streamlit app talks to Ollama on 127.0.0.1; the Meeting Spot runs on the phone with GPS from satellites](https://raw.githubusercontent.com/ThePlator/Chhath_Ghat_Guide-/main/docs/blog/images/architecture.png)

| Part | Choice | Why |
| --- | --- | --- |
| Model | **Gemma 3 4B** via Ollama, for both reading photos and writing answers | Open weights, runs on a laptop CPU, no internet |
| App | Python + **Streamlit**, three tabs | Fast to build; camera and file inputs built in |
| Ritual answers | 10 Markdown notes, keyword + `nomic-embed-text` search | Answers traceable to checked text |
| Meeting Spot | Plain HTML + JS, Geolocation + DeviceOrientation APIs | Runs on the phone; location never leaves it |
| Phones | Self-signed **HTTPS** on the hotspot | Phone browsers only allow GPS, camera and compass on secure pages |

## The code that keeps the AI honest

The interesting part of this project wasn't getting Gemma to talk — it was making sure it **doesn't say more than it knows**, in a place where a wrong answer can matter.

### 1. Read first, then explain only what was read

The Notice Reader makes two calls on purpose. The first copies the text (temperature 0, unreadable words marked `[?]`); the second explains **only that text**, so every claim on screen can be checked against the original right below it.

```python
# ghat_guide/notice_reader.py (trimmed)
def transcribe(self, image: bytes) -> Transcription:
    out = self.llm.chat_json(
        model=self.models.vision_model,
        system=prompts.SYS_TRANSCRIBE,      # "copy exactly; write [?] for unreadable words"
        user=prompts.USER_TRANSCRIBE,
        schema=prompts.TRANSCRIBE_SCHEMA,   # {text_read, script, clarity}
        temperature=0.0,
        images=[image],
    )
    clarity = clarity_verdict(out["text_read"], out["clarity"], ...)  # model's opinion + our own rules
    return Transcription(out["text_read"], ..., clarity, is_safety_notice(out["text_read"]), ...)

def explain(self, tr: Transcription, lang: str) -> Explanation | None:
    if tr.clarity == "unclear":
        return None                          # nothing reliable to explain: show "साफ़ नहीं पढ़ पाए"
    out = self.llm.chat_json(model=self.models.text_model, system=prompts.sys_explain(lang),
                             user=prompts.user_explain(tr.text_read), ...)
    return Explanation(..., number_warning=unsupported_numbers(out["explanation"], tr.text_read))
```

Splitting the steps had a nice side effect: switching language re-runs only the cheap text step, not the slow image step.

The safety check is plain keyword matching, chosen carefully — *"डूब"* (drown) alone would also match *"डूबते सूर्य"*, the **setting sun** that Sandhya Arghya is offered to, so the list uses *"डूबने"* instead:

```python
# ghat_guide/safety.py (excerpt)
#   "डूब" alone would match "डूबते सूर्य" (the setting sun of Sandhya Arghya),
#   "मना" alone would match "मनाया" (celebrated).
SAFETY_TERMS_DEVANAGARI = ("गहरा", "गहराई", "डूबने", "खतरा", "बैरिकेड", "निषेध", "मना है", ...)
```

### 2. Ritual answers have to earn their way out

```python
# ghat_guide/ritual/answerer.py (trimmed)
def ask(self, question: str, lang: str) -> RitualAnswer:
    if asks_for_official_info(question):       # "बजे", "तारीख", "इस साल", "पार्किंग", ...
        return RitualAnswer("official_info", None)   # never asks the model

    relevant = [h for h in self.retriever.search(question) if self.retriever.is_relevant(h)]
    if not relevant:
        return RitualAnswer("not_in_notes", None)

    out = self.llm.chat_json(..., user=prompts.user_ritual(context, question),
                             schema=prompts.RITUAL_SCHEMA)  # {found, answer, used_chunk_ids}
    given = {h.chunk.chunk_id for h in relevant}
    cited = out.get("used_chunk_ids") or []
    if not out.get("found") or not cited or any(c not in given for c in cited):
        return RitualAnswer("not_in_notes", None)   # no sources, or sources it wasn't given
    return RitualAnswer("answered", out["answer"], sources=[...])
```

Search is a mix of keywords and embeddings, because `nomic-embed-text` is mostly trained on English and Devanagari questions alone can rank poorly. Hand-written keywords plus a small synonym map (*अरघ → अर्घ्य*, *सूपा → सूप*) and a light stemmer (*खरने ↔ खरना*) catch the words families actually use. And a note without an elder's `checked_by` is never loaded at all.

### 3. The arrow is just two lines of trigonometry

The Meeting Spot runs in the phone's browser, so it's plain JavaScript:

```js
// static/meeting_spot.html (excerpt, simplified)
function bearing(lat1, lon1, lat2, lon2) {          // degrees clockwise from north
  var p1 = lat1 * rad, p2 = lat2 * rad, dl = (lon2 - lon1) * rad;
  var x = Math.sin(dl) * Math.cos(p2);
  var y = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl);
  return (Math.atan2(x, y) / rad + 360) % 360;
}
// heading comes from the compass (iOS: webkitCompassHeading, Android: 360 - alpha),
// smoothed with a circular mean so 350° and 10° average to 0°, not 180°.
arrow.style.transform = "rotate(" + mod360(bearing(here, spot) - heading) + "deg)";
```

The same maths lives in Python (`ghat_guide/geo.py`), and a test runs both side by side in a real browser so they can't drift apart.

### 4. A pre-trip check, because you can't download anything at the ghat

![Output of scripts/check_offline.py: models downloaded, phone pages offline-only, warnings for unchecked notes and missing emergency contacts](https://raw.githubusercontent.com/ThePlator/Chhath_Ghat_Guide-/main/docs/blog/images/check-offline.png)

*A real run of `scripts/check_offline.py` — the warnings are true: the notes are still waiting for the elder review.*

It checks that the models are downloaded, the ritual index is built, the phone pages load **nothing** from the internet, the HTTPS certificate matches the hotspot's IP (a classic "it worked at home" failure), and that the model server isn't reachable from the phones.

## Touching grass

[FILL — after the field test. Suggested shape:
- Where: the ghat or riverbank, the date, who came along.
- The moment you switched mobile data off and the app kept working.
- Numbers from docs/FIELD_TEST.md: seconds per notice, whether the arrow pointed the right way, GPS accuracy near the water.
- What the elder said about the Ritual Helper (with permission), and what they corrected in the notes.
- What didn't work — honestly.]

The real test is still ahead: Chhath Puja is in late October / early November, and I'll take it to the ghat then and report back here.

## Demo

[FILL — embed the 1–2 minute video: ghat → network failing with mobile data visibly off → each tab once → "police, volunteers and elders come first".]

## Why open innovation matters here

- **It works with no network.** A cloud AI is useless when the network is jammed; an open-weight model on a laptop isn't.
- **Data stays at the ghat.** Photos, questions and family locations never leave the laptop and phones.
- **It's free.** No API keys, no subscription — a laptop the family already has.
- **Local languages.** Bhojpuri and Maithili rarely get first-class support; open models and open notes let the community improve that.
- **Anyone can swap or tune the model** — one line in `config/settings.toml` — or rewrite the notes for their own family's customs.

## Limits (honest list)

- **Bhojpuri and Maithili are beta.** The model may slip into Hindi; Hindi is the default.
- **Speed:** on a laptop CPU, reading a photo can take tens of seconds, and phones take turns.
- **GPS** near water and crowds is often off by 5–20 m — so the landmark photo and note are always on screen.
- **Not a lost-person tracker, and not an authority.** Official announcements, police, volunteers and elders come first.
- **Not field-tested yet with real Gemma output** — the automated tests use a stand-in model and emulated GPS/compass; the outdoor test is next.

## Prize category

**Best Use of Gemma** — Gemma 3 4B reads the notices and writes the explanations and answers, fully offline, on one laptop.

## Try it / contribute

Code (MIT): **https://github.com/ThePlator/Chhath_Ghat_Guide-** — setup, the design docs (HLD/LLD), and the field-test sheet are in the repo. Checked ritual notes, Bhojpuri/Maithili corrections and sample notice photos (without identifiable people) are especially welcome.

*छठी मइया सबके मनोकामना पूरा करस।* 🌅

— Sameer
