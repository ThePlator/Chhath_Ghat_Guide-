# Field test sheet — data off, at a ghat or riverbank

Plan tasks 5.1–5.5. Print this or keep it open on the laptop and fill it in as you go.

| | |
| --- | --- |
| **Date** | |
| **Place** | _(ghat / riverbank name)_ |
| **Laptop** | _(model, plugged in or battery)_ |
| **Phones** | _(e.g. Android — Chrome; iPhone — Safari)_ |
| **Weather / light** | |

---

## 1. Before leaving home (internet still on)

- [ ] `git pull` and `pip install -r requirements.txt`
- [ ] Models downloaded: `ollama pull gemma3:4b` and `ollama pull nomic-embed-text`
- [ ] Ritual notes checked by an elder, then `python scripts/build_index.py`
- [ ] Turn the hotspot on once to learn its IP, then `scripts/make_cert.sh <hotspot-ip>` and uncomment `sslCertFile` / `sslKeyFile` in `.streamlit/config.toml`
- [ ] `python scripts/check_offline.py --hotspot-ip <hotspot-ip> --deep` says **Ready for the ghat**
- [ ] Open the app once on each phone and accept the certificate warning (saves time at the ghat)
- [ ] Packed: laptop charger, power bank + cables for phones, 3 printed sample notices (one "deep water / barricade" notice), this sheet

## 2. Offline setup at the ghat

- [ ] Laptop: Wi-Fi internet **off** (or no SIM / no uplink), hotspot **on** with internet sharing off
- [ ] Phones: mobile data **off** — film this for the video
- [ ] `ollama serve` running; `streamlit run app.py`
- [ ] Each phone joins the hotspot and opens `https://<hotspot-ip>:8501`
- [ ] Sidebar shows the emergency card; no red "model not running" banner

## 3. Notice Reader — 3 notices

Time each one from tapping the photo to seeing the explanation.

| # | Notice (what it says, roughly) | Light / angle | Clarity shown | Explanation right? (1–5) | Invented anything? | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | _safety notice (deep water / barricade)_ | | | | | |

- [ ] The safety notice showed its **original text first, in the red box**
- [ ] A deliberately blurry photo showed **"साफ़ नहीं पढ़ पाए"**
- [ ] Switching language re-explained without re-reading the photo (faster)

## 4. Ritual Helper — 3 answerable + 2 not answerable

| # | Question | Expected | Got (answer / not in notes / official info) | Right? | Seconds |
| --- | --- | --- | --- | --- | --- |
| 1 | अर्घ्य कब दिया जाता है? | answer | | | |
| 2 | सूप में क्या रखते हैं? | answer | | | |
| 3 | _(an elder's own question)_ | answer | | | |
| 4 | इस साल अर्घ्य कितने बजे है? | official info | | | |
| 5 | _(something not in the notes)_ | not in notes | | | |

- [ ] Sources show who checked the note
- [ ] Elder's reaction (for the DEV post): _______________________________________________

## 5. Meeting Spot — save, walk away, come back

Do this on at least one Android **and** one iPhone if you have both.

| Phone | GPS ± when saved (m) | Walked away (m) | Arrow pointed the right way? | Distance shown when back at spot | GPS ± near the water (m) |
| --- | --- | --- | --- | --- | --- |
| | | | | | |
| | | | | | |

- [ ] iPhone asked for compass ("motion") permission after tapping "मुझे वापस ले चलो"
- [ ] Page reloaded → spot still there
- [ ] **Lid test:** close the laptop lid (or stop Streamlit) with the Meeting Spot page already open → "take me back" still works
- [ ] "मिटाएँ" removed the spot
- [ ] If the arrow was wrong: did figure-8 calibration fix it? Did "पूरी स्क्रीन में खोलें" help?

## 6. Capture for the video and post

Never film or photograph an identifiable vrati or stranger without permission.

- [ ] Wide shot of the ghat / river (no faces)
- [ ] Phone screen with **mobile data off**, then the app working
- [ ] Laptop with hotspot on and no internet
- [ ] Notice Reader on the printed safety notice (original text in red)
- [ ] Ritual Helper answering, then "not in my notes"
- [ ] Walking back with the Meeting Spot arrow
- [ ] A short line from the elder (with permission), or written notes of what they said

## 7. Fix list

Mark each **P0** (blocks the demo: fix tonight) or **P1** (after the challenge).

| # | Tab | What happened | Steps to repeat it | P0 / P1 |
| --- | --- | --- | --- | --- |
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |

Rule from the plan: fix only P0 tonight; everything else goes in the post as an honest limit or a GitHub issue.
