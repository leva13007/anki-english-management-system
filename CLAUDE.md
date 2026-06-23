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
| `generate_audio.py` | generates MP3 audio for cards via ElevenLabs TTS (interactive session) |

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

### sync_back.py flags

```
python scripts/sync_back.py --dry-run             # preview plan, no changes
python scripts/sync_back.py                       # apply with confirmation
python scripts/sync_back.py --add-new             # also write new Anki cards to YAML
python scripts/sync_back.py --download-media      # also download missing media files
python scripts/sync_back.py --add-new --download-media  # full pull
```

Cards deleted in Anki are reported but NOT removed from YAML — resolve manually.

### generate_audio.py

Generates MP3 audio for cards where the `Audio` field is empty. Reads the `Back` field (English text), sends it to ElevenLabs TTS, plays back the result, and on confirmation saves the file to `media/` and updates `cards.yaml` immediately. Does not require Anki to be running.

```
python scripts/generate_audio.py --deck interview   # process interview deck
python scripts/generate_audio.py --deck l2-vocab    # process any other deck
```

**Interactive keys:**

| key | action |
|-----|--------|
| `y` | accept — save MP3 to `media/`, write `[sound:…]` into cards.yaml, next card |
| `p` | replay — play the same audio again without a new API call |
| `r` | regenerate — new ElevenLabs call with a fresh random voice, play again |
| `s` | skip — leave this card's Audio empty, move to next |
| `q` | quit — save progress so far and exit |

**Voice pool:** a random voice is picked from `DEFAULT_VOICES` for each new card (and on `r`). The pool is defined in the script. On `p` replay the already-generated audio plays unchanged.

**Config (`.env`):**

```
ELEVENLABS_API_KEY=...          # required
ELEVENLABS_VOICE_IDS=id1,id2   # optional — replaces the built-in voice pool
ELEVENLABS_VOICE_ID=...        # optional — single voice (used if VOICE_IDS not set)
ELEVENLABS_MODEL_ID=...        # optional — defaults to eleven_multilingual_v2
```

**Workflow after a session:**

```bash
python scripts/generate_audio.py --deck interview   # fill in Audio fields
python scripts/validate.py                          # check media refs are valid
python scripts/sync.py                              # push to Anki
```

Video decks (`video-by-movies`) are automatically rejected — they use `VideoFilename`, not `Audio`.

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
    Audio: filename.mp3             # or VideoFilename: 00001.webm
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

## Environment config (`.env`)

`.env` lives in the project root and is gitignored. Never read, print, or commit it.

| key | required | description |
|-----|----------|-------------|
| `ELEVENLABS_API_KEY` | yes (for `generate_audio.py`) | ElevenLabs API key |
| `ELEVENLABS_VOICE_IDS` | no | comma-separated voice ID pool for random selection |
| `ELEVENLABS_VOICE_ID` | no | single voice override (fallback if VOICE_IDS not set) |
| `ELEVENLABS_MODEL_ID` | no | TTS model, defaults to `eleven_multilingual_v2` |

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
- `.env` — API keys and secrets (never commit)
