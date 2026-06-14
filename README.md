---
status: active
category: learning
stack: CSV, YAML, Markdown
---

# anki-english

Version-controlled source of truth for all Anki flashcard decks.

## workflow

```
Edit cards.csv  →  git commit  →  File › Import in Anki
```

When importing: File → Import → select `cards.csv` → map columns to Anki fields by header name.

For cards with media: copy files from `media/` to Anki's `collection.media/` folder first, then import the CSV.

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

Export existing cards from Anki (File → Export → Cards in Plain Text) and paste them into the matching `cards.csv` files.
