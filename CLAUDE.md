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
| `validate.py` | lints repo: structure, duplicates, media refs, HTML noise — exit 1 on errors |
| `sync.py` | pushes YAML → Anki: add/update notes, upload media, write back new ids |
| `sync_back.py` | pulls changes from Anki back into YAML (reverse sync) |

Bootstrap scripts are **idempotent** — safe to re-run.  
`bootstrap_media.py` reads `mediaFields` from `models/*/_meta.yaml` to know which fields contain filenames.

### sync.py flags

```
python scripts/sync.py --dry-run             # preview plan, no changes
python scripts/sync.py                       # apply with confirmation
python scripts/sync.py --check-media-hashes  # also compare MD5 of media files
python scripts/sync.py --prune               # remove orphaned notes from Anki (with confirmation)
```

`sync.py` writes new `id` values back into `cards.yaml` after `addNote`.

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

| dir | Anki deck name | note type | purpose |
|-----|----------------|-----------|---------|
| `it-deck` | IT_deck | Basic (type in the answer) + audio | IT professional vocab — sentence production |
| `video-by-movies` | Video_by_movies | Video (type in the answer) | Listening + fluency — clips from shows |
| `interview` | Interview | Basic (with typing)+audio+state | Gaps found in mock interviews |
| `l2-vocab` | L2_vocab | Basic (type in the answer) + audio | ESOL L2 course vocabulary |
| `medicine` | Medicine | Basic (type in the answer) + audio | Medical vocab for GP visits |
| `book` | Book | Basic (type in the answer) + audio | Phrases from English books |

See `docs/decks-overview.md` for full context on each deck.

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

### video-by-movies specifics

Clips are short video fragments (max 5 sec, 320px) cut from shows in Final Cut Pro.
Front = English transcript (what the user types). Back = Ukrainian translation (secondary).

**Current content:**
- `sherlok_*.webm` — Sherlock BBC, Season 1 complete (660 clips)
- `silicon_*.webm` — Silicon Valley HBO, Season 1 ~half done (343 clips)
- `pets_*.webm` — The Secret Life of Pets, complete (273 clips)

**Next candidates:** finish Silicon Valley S1, then House MD / Suits / Sherlock S2.

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

## Docs

| file | what it contains |
|------|-----------------|
| `docs/decks-overview.md` | why each deck exists, motivation, content details |
| `docs/word-lists.md` | vocabulary roadmap — IT terms, phrases, phrasal verbs not yet in cards |
| `docs/hint-dsl.md` | planned hint system for card Front fields (HTML-based, not implemented yet) |
| `docs/note-types.md` | human-readable summary of note type models |

---

## Gitignore

- `.venv/` — Python venv
- `__pycache__/` — bytecode
- `backups/` — `.colpkg` snapshots (kept locally, not in git)
