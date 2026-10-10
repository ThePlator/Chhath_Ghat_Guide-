# Notice photos for the Phase 1 spike

Put 3–10 notice photos here (`.jpg`, `.png`, `.webp`), then run:

```bash
python scripts/spike_notice.py
```

Good test set:

- 2–3 **clear** printed notices in Hindi (Devanagari)
- 1 notice with **times or ghat numbers** (checks that numbers are not invented)
- 1 **safety** notice (deep water, barricade, "प्रवेश निषेध")
- 1 **blurry or angled** photo (should come back `partial` / `unclear`)
- 1 banner with **mixed Hindi + English**

If you have no real notices yet, print a few sample ones and photograph them on a phone.

**Privacy:** photos in this folder are git-ignored. Only commit a photo with
`git add -f` after checking it shows no identifiable people and no personal phone numbers.
