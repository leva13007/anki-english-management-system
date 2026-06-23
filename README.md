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

**Ongoing (YAML → Anki):**
```
Edit decks/*/cards.yaml
python scripts/validate.py          # lints repo, exit 1 on errors
python scripts/sync.py --dry-run    # preview changes
python scripts/sync.py              # apply to Anki (asks confirmation)
git commit
```

**Generate audio via ElevenLabs (Anki not required):**
```
python scripts/generate_audio.py --deck interview   # walk through cards with empty Audio
# interactive session: [y] keep  [p] replay  [r] regenerate  [s] skip  [q] quit
python scripts/validate.py          # verify media refs
python scripts/sync.py              # push to Anki
```

Requires `ELEVENLABS_API_KEY` in `.env`. Each card gets a random voice from the built-in pool; `r` picks a fresh one.

**Pull changes from Anki back (Anki → YAML):**
```
python scripts/sync_back.py                              # preview plan
python scripts/sync_back.py --add-new                    # also write new Anki cards to YAML
python scripts/sync_back.py --download-media             # also download missing media files
python scripts/sync_back.py --add-new --download-media   # full pull
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
| [interview](./decks/interview/) | Interview | — | Gaps found during mock interviews — fluency under pressure |
| [l2-vocab](./decks/l2-vocab/) | L2_vocab | 267 | Vocabulary from ESOL L2 Writing/Reading course |
| [medicine](./decks/medicine/) | Medicine | 100 | Medical vocabulary for GP visits and health conversations |
| [book](./decks/book/) | Book | 53 | Phrases and expressions collected while reading English books |

See [docs/decks-overview.md](./docs/decks-overview.md) for full context on each deck.

## next step

Sync 81 new Silicon Valley S1 clips from Anki (`sync_back.py --add-new --download-media`). Rebuild interview deck. Expand it-deck with code review and stand-up vocabulary (see [docs/word-lists.md](./docs/word-lists.md)).
