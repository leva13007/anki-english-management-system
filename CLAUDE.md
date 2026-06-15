# CLAUDE.md — anki-english

Version-controlled source of truth for Anki flashcard decks. Cards live as CSV in git; AnkiConnect syncs them into Anki via HTTP API.

---

## Status

AnkiConnect is **not yet installed**. Current `decks/` directories are placeholder mocks — structure is defined but cards are empty. Real work starts after AnkiConnect is set up.

---

## AnkiConnect

Plugin code: `2055492159`  
Install: Tools → Add-ons → Get Add-ons → enter code → restart Anki.  
Runs locally on `http://localhost:8765` (HTTP API, no auth).

Key actions used in this project:
- `addNote` / `updateNoteFields` — create or update a card
- `addNotes` (bulk) — sync a full CSV batch
- `storeMediaFile` — upload audio/image to `collection.media/`
- `findNotes` / `notesInfo` — check what's already in Anki

---

## Deck structure

```
decks/<deck-name>/
  _meta.yaml   — noteType, deck name, fields, tags
  cards.csv    — one row per card, header matches fields
```

`_meta.yaml` is the authoritative schema for a deck. `cards.csv` column order must match `fields` in `_meta.yaml`.

---

## Note types and fields

**Not yet defined.** Note types and their fields will be confirmed after connecting to Anki via AnkiConnect (`modelNames` / `modelFieldNames` actions). Document them in `docs/note-types.md` once known.

---

## Media

Files in `media/audio/` and `media/images/` must be uploaded to Anki's `collection.media/` before cards referencing them are imported. Use AnkiConnect `storeMediaFile` action.

---

## Conventions

- One `cards.csv` per deck — no splitting.
- Tags come from `_meta.yaml` (deck-level) and can be added per-card in the Tags column.
- Never commit `.apkg` or `.colpkg` files — they are in `.gitignore`.
- `docs/word-lists.md` is a staging area for vocabulary not yet turned into cards.
