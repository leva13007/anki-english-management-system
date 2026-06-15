# CLAUDE.md — anki-english

Version-controlled source of truth for Anki flashcard decks. Cards, note types, and media are pulled from Anki via AnkiConnect and stored as YAML/HTML/CSS in git.

---

## AnkiConnect

Plugin code: `2055492159`. Runs at `http://localhost:8765`.  
Anki must be open for any script to work.

---

## Scripts

All scripts live in `scripts/`, require `.venv` activated, use `requests` + `yaml`.

| script | what it does |
|--------|--------------|
| `bootstrap_models.py` | pulls note types → `models/` (fields, templates, CSS) |
| `bootstrap_decks.py` | pulls card data → `decks/` (_meta.yaml + cards.yaml) |
| `bootstrap_media.py` | pulls media files → `media/` (interactive, confirms before downloading) |

Bootstrap scripts are **idempotent** — safe to re-run.  
`bootstrap_media.py` reads `mediaFields` from `models/*/_meta.yaml` to know which fields contain filenames.

---

## Note types (models)

Stored in `models/<safe-name>/`. `safe-name` is the Anki name lowercased, non-alphanum replaced with `-`.

| Anki name | dir | fields | media field |
|-----------|-----|--------|-------------|
| Basic (type in the answer) + audio | `basic-type-in-the-answer-audio` | Front, Back, Audio | Audio |
| Basic (with typing)+audio+state | `basic-with-typing-audio-state` | Front, Back, Audio, State | Audio |
| Video (type in the answer) | `video-type-in-the-answer` | Front, Back, VideoFilename | VideoFilename |

`_meta.yaml` in each model dir is the authoritative schema. `mediaFields` key tells `bootstrap_media.py` which fields hold filenames.

---

## Decks

Stored in `decks/<safe-name>/`. Each deck has `_meta.yaml` (deckName + noteType) and `cards.yaml`.

| dir | Anki deck name | note type |
|-----|----------------|-----------|
| `book` | Book | Basic (type in the answer) + audio |
| `interview` | Interview | Basic (with typing)+audio+state |
| `it-deck` | IT_deck | Basic (type in the answer) + audio |
| `l2-vocab` | L2_vocab | Basic (type in the answer) + audio |
| `medicine` | Medicine | Basic (type in the answer) + audio |
| `video-by-movies` | Video_by_movies | Video (type in the answer) |

`cards.yaml` format:
```yaml
- id: 1756166410321       # Anki noteId (integer)
  fields:
    Front: English sentence
    Back: Ukrainian translation
    Audio: "[sound:filename.mp3]"   # or VideoFilename: 00001.webm
  tags: []
```

If a deck has multiple note types, bootstrap creates `cards.<safe-type>.yaml` files instead of a single `cards.yaml`.

---

## Media

All files are flat in `media/`. Video cards use `.webm`, audio cards use `.mp3`.  
Filenames in cards reference media directly (e.g. `00001.webm`, not a full path).  
`media/` is committed to git (files are checked in).

---

## Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests pyyaml
```

`.venv/` is gitignored.

---

## Gitignore

- `.venv/` — Python venv
- `__pycache__/` — bytecode
- `backups/` — `.colpkg` snapshots (kept locally, not in git)
