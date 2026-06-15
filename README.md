---
status: active
category: learning
stack: CSV, YAML, Markdown
---

# anki-english

Version-controlled source of truth for all Anki flashcard decks.

## workflow

Requires [AnkiConnect](https://ankiweb.net/shared/info/2055492159) plugin running locally (port 8765).

```
Edit cards.csv  →  git commit  →  sync script  →  AnkiConnect API  →  Anki
```

AnkiConnect replaces the manual File › Import step — cards are pushed programmatically via HTTP.

For cards with media: files in `media/` are copied to Anki's `collection.media/` as part of the sync.

## structure

```
decks/<deck-name>/
  _meta.yaml    — note type, deck name, fields list
  cards.csv     — one card per row, header matches fields
media/
  audio/        — MP3 files referenced in cards as [sound:file.mp3]
  images/       — images referenced in cards as <img src="file.jpg">
docs/
  note-types.md — all custom Anki note types documented
  word-lists.md — vocabulary reference, curated word sets outside of cards
```

## decks

| deck | note type | description |
|------|-----------|-------------|
| [medical](./decks/medical/) | Basic-UA-EN-Audio | Medical English vocabulary |
| [how-to-win-friends](./decks/how-to-win-friends/) | Sentence-Video | Phrases and sentences from the book |
| [it-vocab](./decks/it-vocab/) | Basic-UA-EN | IT and tech vocabulary |

## next step

Install AnkiConnect in Anki: Tools → Add-ons → Get Add-ons → code `2055492159` → restart Anki.
