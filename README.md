---
status: active
category: learning
stack: Python, YAML, AnkiConnect
---

# anki-english

Version-controlled source of truth for all Anki flashcard decks. Cards and note types are stored as YAML; AnkiConnect bridges local files and Anki over HTTP.

## workflows

> Activate venv first: `source .venv/bin/activate`

---

### 1. First-time setup

Pull everything from Anki into the repo. Anki must be open.

```
python scripts/bootstrap_models.py   # note types → models/
python scripts/bootstrap_decks.py    # cards      → decks/
python scripts/bootstrap_media.py    # media files → media/
git commit -m "bootstrap"
```

---

### 2. Add / edit cards (YAML → Anki)

Edit `decks/*/cards.yaml`, then push to Anki. Anki must be open.

```
# edit decks/*/cards.yaml
python scripts/validate.py           # lint — fix errors before syncing
python scripts/sync.py --dry-run     # preview what will change
python scripts/sync.py               # apply (asks confirmation, writes new ids back)
git commit
```

---

### 3. Generate audio (ElevenLabs → media/ → Anki)

Fills empty `Audio` fields. **Anki not required.** Requires `ELEVENLABS_API_KEY` in `.env`.

```
python scripts/generate_audio.py --deck interview
```

Interactive keys per card: `y` keep · `p` replay · `r` regenerate (new voice) · `s` skip · `q` quit

Each card gets a random voice from the built-in pool. Progress saves immediately on `y`.

```
python scripts/validate.py           # verify all Audio refs have matching files
python scripts/sync.py               # push updated cards + new mp3s to Anki
git commit
```

---

### 4. Interview deck: fill in Ukrainian translations (Front field)

The `interview` deck has a special field layout:

| field | what goes here |
|-------|----------------|
| `State` | Interview question in Ukrainian (already filled) |
| `Back` | English answer to practice |
| `Front` | **Your** Ukrainian translation of Back — fill in manually |
| `Audio` | MP3 of Back — generated via `generate_audio.py` |

Open `decks/interview/cards.yaml`, find cards where `Front: ''`, and fill in the Ukrainian translation of `Back`. Then sync:

```
python scripts/validate.py
python scripts/sync.py
git commit
```

---

### 5. Pull changes from Anki back to YAML (Anki → YAML)

Use when you edited cards directly in Anki. Anki must be open.

```
python scripts/sync_back.py                              # updates changed fields
python scripts/sync_back.py --add-new                    # + write cards added in Anki GUI
python scripts/sync_back.py --download-media             # + download new media files
python scripts/sync_back.py --add-new --download-media   # full pull
git commit
```

Cards deleted in Anki are reported but NOT auto-removed from YAML — resolve manually.

---

### 6. Clean up orphaned media

Run after deleting cards or regenerating audio files.

```
python scripts/validate.py           # shows count of unreferenced files in media/
python scripts/validate.py --prune   # same + offers to delete them (asks confirmation)
git commit
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
  validate.py         — lint repo before committing
  sync.py             — push YAML changes to Anki
  sync_back.py        — pull changes from Anki back into YAML
  generate_audio.py   — interactive ElevenLabs TTS session; fills empty Audio fields
.env                  — API keys (gitignored, never commit)
docs/
  note-types.md       — human-readable summary of models
  word-lists.md       — vocabulary roadmap: IT terms, phrases, phrasal verbs not yet in cards
  decks-overview.md   — why each deck exists, what gap it fills
  hint-dsl.md         — planned hint system for card Front fields (concept, not implemented yet)
backups/              — .colpkg snapshots (gitignored)
```

## decks

| dir | Anki deck name | cards | purpose |
|-----|----------------|-------|---------|
| [it-deck](./decks/it-deck/) | IT_deck | 853 | IT professional vocabulary — sentence production for work communication |
| [video-by-movies](./decks/video-by-movies/) | Video_by_movies | 1331 | Listening + spoken fluency — clips from Sherlock, Silicon Valley, Secret Life of Pets |
| [interview](./decks/interview/) | Interview | 58 | Interview prep: State = interview question (ukr), Front = ukr translation of answer (manual), Back = English answer |
| [l2-vocab](./decks/l2-vocab/) | L2_vocab | 267 | Vocabulary from ESOL L2 Writing/Reading course |
| [medicine](./decks/medicine/) | Medicine | 100 | Medical vocabulary for GP visits and health conversations |
| [book](./decks/book/) | Book | 53 | Phrases and expressions collected while reading English books |

See [docs/decks-overview.md](./docs/decks-overview.md) for full context on each deck.

## next step

Sync 81 new Silicon Valley S1 clips from Anki (`sync_back.py --add-new --download-media`). Rebuild interview deck. Expand it-deck with code review and stand-up vocabulary (see [docs/word-lists.md](./docs/word-lists.md)).
