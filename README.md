---
status: active
category: learning
stack: Python, YAML, AnkiConnect
---

# anki-english

Version-controlled source of truth for all Anki flashcard decks. Cards and note types are stored as YAML; AnkiConnect bridges local files and Anki over HTTP.

## workflow

Requires Anki running with [AnkiConnect](https://ankiweb.net/shared/info/2055492159) plugin (port 8765).

**Bootstrap (one-time pull from Anki):**
```
python scripts/bootstrap_models.py   # note types → models/
python scripts/bootstrap_decks.py    # cards      → decks/
python scripts/bootstrap_media.py    # media files → media/
```

**Ongoing:**
```
Edit decks/*/cards.yaml  →  git commit  →  (sync script, TBD)  →  Anki
```

## structure

```
decks/<deck-name>/
  _meta.yaml          — deckName, noteType
  cards.yaml          — list of {id, fields, tags}

models/<model-name>/
  _meta.yaml          — noteType, fields, templates, mediaFields
  style.css
  templates/<card-name>/
    front.html
    back.html

media/                — flat directory, all media files (.webm, .mp3, ...)
scripts/
  bootstrap_decks.py  — pull card data from Anki
  bootstrap_models.py — pull note types (fields, templates, CSS) from Anki
  bootstrap_media.py  — pull media files from Anki
docs/
  note-types.md       — human-readable summary of models
  word-lists.md       — vocabulary staging area, not yet turned into cards
backups/              — .colpkg snapshots (gitignored)
```

## decks

| dir | Anki deck name | note type |
|-----|----------------|-----------|
| [book](./decks/book/) | Book | Basic (type in the answer) + audio |
| [interview](./decks/interview/) | Interview | Basic (with typing)+audio+state |
| [it-deck](./decks/it-deck/) | IT_deck | Basic (type in the answer) + audio |
| [l2-vocab](./decks/l2-vocab/) | L2_vocab | Basic (type in the answer) + audio |
| [medicine](./decks/medicine/) | Medicine | Basic (type in the answer) + audio |
| [video-by-movies](./decks/video-by-movies/) | Video_by_movies | Video (type in the answer) |

## next step

Write a sync script that pushes local `cards.yaml` changes back to Anki via AnkiConnect (`updateNoteFields`, `addNote`).
