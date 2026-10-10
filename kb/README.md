# Ritual knowledge base

The Ritual Helper answers **only** from the notes in this folder.

## Status: drafts, not yet checked

All notes are **drafts**. `checked_by` is empty, so the app ignores every note
until a family elder has checked it. This is on purpose: unchecked text never
reaches users.

## How to check a note (plan.md task 3.2)

1. Read the note aloud to a family elder.
2. Fix anything they correct. Keep the "परिवारों में अंतर" section.
3. Fill in the front matter, for example:
   ```yaml
   checked_by: "Nani (family elder)"
   checked_on: 2026-10-10
   ```
4. Run `python scripts/build_index.py` (or restart the app).

## Rules for notes

- Write in your own words; don't copy from websites or books.
- **No fixed clock times or dates.** Describe timings relative to sunrise / sunset; real timings come from official notices.
- Customs vary by family and region: describe variations, never declare one "correct" way.
- One topic per `## ` section; the app searches section by section.
- `keywords` should include the words families actually use, including common spellings (e.g. अर्घ्य / अरघ / arghya).

## Front matter

| Key | Required | Meaning |
| --- | --- | --- |
| `id` | yes | Unique, lowercase, used in citations |
| `title_hi` | yes | Shown to users as the source title |
| `keywords` | yes | Words for keyword search |
| `checked_by` | yes | Who checked it; empty = note is skipped |
| `checked_on` | yes | Date checked |
| `title`, `day` | no | English title; Chhath day (0 = general) |
