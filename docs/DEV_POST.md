<!--
Draft DEV post for the Hacktoberfest Open-Source AI Challenge, Week 1 "Touch Grass".

Before publishing:
1. Copy the official Week 1 submission template from the launch post and keep its
   headings and first line; move the text below under them. (This draft was written
   without access to dev.to, so the headings here are a best guess.)
2. Replace every [FILL: …] with what really happened. Delete anything that didn't.
3. Photos: no identifiable vratis or strangers without permission.
4. Tags: #devchallenge #hf26challenge (+ the template's own tags).
-->

---
title: "Chhath Ghat Guide: an offline helper for the day the network dies at the ghat"
published: false
tags: devchallenge, hf26challenge, ai, opensource
cover_image: "[FILL: wide photo of the ghat / river, no faces]"
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge — Week 1: Touch Grass](https://dev.to/devteam/join-the-hacktoberfest-open-source-ai-challenge-week-1-touch-grass-2450-in-prizes-across-17-4pom).* [FILL: replace with the template's exact first line]

## The ghat, the crowd and the dead network

Every year during Chhath Puja, lakhs of families walk down to the ghats of Bihar to offer arghya to the setting and rising sun. Vratis stand in the river; children hold their parents' hands; elders watch the water. And every year, the same three things happen:

- Families get **separated** in the crowd.
- Notices about **deep water, barricades and timings** are hard to read in the press of people — and many elders read Bhojpuri or Maithili more comfortably than printed Hindi.
- **The mobile network jams.** Calls don't connect, messages don't send, and any app that needs the internet stops working exactly when it's needed.

Chhath Ghat Guide is a small helper built for that moment. It runs on **one laptop at the ghat**. The laptop's Wi-Fi hotspot has **no internet**; family phones join it and open the app in a browser. Nothing leaves the ghat.

## What I built

Three tabs, one per job:

**📜 सूचना पढ़ें — Notice Reader.** Take a photo of a notice or banner. A local **Gemma 3 (4B)** vision model first copies the text exactly, then explains it in simple Hindi, Bhojpuri or Maithili — using *only* the text it read. The original text is always on screen. Safety notices (deep water, barricades, emergency) show the original words **first, in a red box**, never just a summary. If the photo is unclear, it says **"साफ़ नहीं पढ़ पाए"** and asks for a better photo instead of guessing. If the explanation mentions a number that isn't in the notice, it warns you.

**🪔 पूजा सहायक — Ritual Helper.** Ask "अर्घ्य कब दिया जाता है?" or "सूप में क्या रखते हैं?". Answers come **only from short notes written by the family and checked by an elder**, each answer shows which note it came from and who checked it, and every answer reminds you that customs differ between families. If the notes don't cover it, it says "यह मेरे नोट्स में नहीं है — किसी बड़े से पूछें". Questions about clock times, dates or parking never reach the model at all: those come from official notices, not from an AI.

**📍 मिलने की जगह — Meeting Spot.** "Save our spot" stores the GPS position, a photo of a landmark and a note ("blue tent near ghat 5 steps") — **on the phone only**. "Take me back" shows the distance and an arrow that turns with the phone's compass. GPS comes from satellites, so this works when calls don't; once the page is open it keeps working even if the laptop goes away. The spot deletes itself at midnight.

An **emergency card** on every screen sends people to the nearest police or volunteer booth. The app ships with **no** phone numbers — organisers add verified ones on the day.

## Demo

[FILL: video embed — 1–2 min, filmed partly outdoors, mobile data visibly off]

[FILL: 2–4 screenshots from the field test: Notice Reader on a safety notice, a Ritual answer with its source, the Meeting Spot arrow]

## Touching grass: testing it at the river

[FILL: where you tested (ghat / riverbank name), the date, who came along.]

[FILL: what it was like to switch mobile data off and still use it. Numbers from docs/FIELD_TEST.md: seconds per notice, whether the arrow pointed the right way, GPS accuracy near the water.]

[FILL: the elder's reaction to the Ritual Helper — in their words if they agreed to be quoted. What they corrected in the notes.]

[FILL: what didn't work, honestly — this is a strength, not a weakness, in the post.]

The real test is still ahead: I'll take it to the ghat at Chhath Puja [FILL: year/date] and report back.

## How I built it

- **Gemma 3 4B via Ollama** for both reading photos and writing explanations/answers — open-weight, runs on a laptop CPU, no internet.
- **Two-step notice reading** (transcribe → explain) so every claim in the explanation can be checked against the text on screen.
- **Small, checked knowledge base instead of model memory:** 10 short Markdown notes, searched with keywords plus `nomic-embed-text` embeddings. Notes without an elder's `checked_by` are never used. Several hard fallbacks keep the model from answering beyond the notes.
- **Streamlit** app with three tabs; **plain HTML + JavaScript** for the Meeting Spot so it runs entirely on the phone (Geolocation + DeviceOrientation APIs, Haversine distance and bearing).
- **Self-signed HTTPS** on the hotspot, because phone browsers only allow GPS, camera and compass on secure pages.
- **Privacy by design:** photo metadata (including GPS) stripped; notice photos never saved; no analytics; the meeting spot never leaves the phone.
- **Tests:** [FILL: final count] automated tests, including browser tests of the Meeting Spot with emulated GPS and compass, plus evaluation scripts for notice reading and ritual answers.

Code: [FILL: repo link] (MIT)

## Why open innovation matters here

- **It works with no network.** A cloud AI is useless when the network is jammed; an open-weight model on a laptop isn't.
- **Data stays on the device.** Photos, questions and family locations never leave the ghat.
- **It's free.** No API keys, no subscription — a laptop the family already has.
- **Local languages.** Bhojpuri and Maithili rarely get first-class support; open models and open notes let the community improve that.
- **Anyone can swap or tune the model.** Change one line in `config/settings.toml` to try a bigger Gemma, or improve the notes for your own family's customs.

## Limits (honest list)

- **Bhojpuri and Maithili are beta.** [FILL: what you saw — e.g. "Gemma's Bhojpuri often slipped into Hindi"]. Hindi is the default.
- **Speed:** on a laptop CPU a photo takes [FILL: N] seconds; phones take turns.
- **GPS** near water and crowds was off by about [FILL: N] m in my test — so the app always shows the landmark photo and note too, and switches to "look for the landmark" when you're within GPS error.
- **Not a lost-person tracker** and not an authority: official announcements, police, volunteers and elders come first.

## Prize categories

- **Best Use of Gemma** — Gemma 3 4B reads the notices and writes the explanations and answers, fully offline.
- [FILL: ElevenLabs only if spoken answers were added — otherwise delete this line]

---

*छठी मइया सबके मनोकामना पूरा करस।* [FILL: your name / team]
