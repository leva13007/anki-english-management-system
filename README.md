---
status: active
category: learning
stack: Python, YAML, AnkiConnect
---
# anki-english

Version-controlled source of truth for all Anki flashcard decks. Cards and note types are stored as YAML; AnkiConnect bridges local files and Anki over HTTP.

## Download and study the decks

To use the cards, download the latest **`anki-english-decks.zip`** from the repository's
[GitHub Releases](https://github.com/leva13007/anki-english-management-system/releases). Extract it
and import the `.apkg` files from the `decks/` folder into Anki (`File → Import`, or open each
package). Import all seven packages for the full collection. The packages include the card models,
templates, and media; learners do not need Python, AnkiConnect, or this source repository.

The release is a clean content snapshot: it does not contain the maintainer's review schedule or
learning history. Each learner gets their own progress. After importing, use Anki's normal study
screen and AnkiWeb Sync to carry personal progress between devices. See the included `INSTALL.txt`
for the short install guide.

### Publishing an updated download

Maintainers need Anki Desktop open with AnkiConnect enabled and the repository synced to the desired
content. Build and check the archive with:

```
source .venv/bin/activate
python scripts/validate.py
python scripts/sync.py --dry-run
python scripts/build_distribution.py
```

The builder stops if any YAML card is missing from Anki, so the exported packages cannot silently
omit cards. It writes `distribution/build/anki-english-decks.zip`; upload that file to a new GitHub
Release and describe the content changes in the release notes. The build directory is ignored by
Git because the archive is a generated release artifact, not a second source of truth.

The download is deliberately provided as Anki packages instead of asking learners to clone this
repository or run its sync scripts. The repository is the editable source and maintainer workflow;
the `.apkg` files are Anki's portable import format and carry each deck's media and note templates.

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

### 3. Import new lines from backlog.md (English → cards.yaml)

Turns plain English sentences dropped into `decks/<deck>/backlog.md` into new cards,
proposing a Ukrainian translation for each. **Anki not required, no API key needed.**

```
python scripts/import_backlog.py --deck medicine
```

Interactive keys per line: `y` accept · `e` edit translation · `s` skip · `q` quit

Dedup is by exact match against existing `Back` values, so `backlog.md` just keeps
growing — re-running only processes what's new. `Audio`/`State` are left empty for
the next steps.

```
python scripts/generate_audio.py --deck medicine   # fill in Audio next
python scripts/validate.py
git commit
```

---

### 4. Generate audio (ElevenLabs → media/ → Anki)

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

### 5. Interview deck: fill in Ukrainian translations (Front field)

The `interview` deck has a special field layout:

| field     | what goes here                                                   |
| --------- | ---------------------------------------------------------------- |
| `State` | Interview question in Ukrainian (already filled)                 |
| `Back`  | English answer to practice                                       |
| `Front` | **Your** Ukrainian translation of Back — fill in manually |
| `Audio` | MP3 of Back — generated via`generate_audio.py`                |

Open `decks/interview/cards.yaml`, find cards where `Front: ''`, and fill in the Ukrainian translation of `Back`. Then sync:

```
python scripts/validate.py
python scripts/sync.py
git commit
```

---

### 6. Pull changes from Anki back to YAML (Anki → YAML)

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

### 7. Clean up orphaned media

Run after deleting cards or regenerating audio files.

```
python scripts/validate.py           # shows count of unreferenced files in media/
python scripts/validate.py --prune   # same + offers to delete them (asks confirmation)
git commit
```

---

### 8. Print a handwriting-practice sheet (today's due cards → PDF)

Generates a printable PDF of the cards a deck's reviewer would show today (`is:due`),
repeating each English `Back` sentence a few times in a dotted tracing font — print it
and trace by hand while the deck is reviewed in Anki as usual. **Anki must be open.**
Read-only — doesn't touch Anki or YAML. Not applicable to `video-by-movies` (video clips,
no `Back` text).

```
python scripts/generate_handwriting_pdf.py --deck interview
```

Useful flags — see [CLAUDE.md](./CLAUDE.md) for the full table:

```
--repeat 3            # times to repeat each sentence (default: 2)
--font lined-alt       # dotted / lined / lined-alt / lined-nospace
--font-size 30          # pt
--intensity 0.35        # 0.0 (white) .. 1.0 (full black, default) — lower = fainter guide to trace over
--limit 5               # cap cards, handy for quick layout tests
```

Output goes to `handwriting_practice/<deck>_<date>.pdf` (gitignored).

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
  import_backlog.py   — imports backlog.md lines into cards.yaml with auto-translated Front
  generate_handwriting_pdf.py — PDF of today's due cards in a dotted tracing font
  build_distribution.py — exports portable .apkg files and assembles the release ZIP
distribution/
  INSTALL.txt           — learner-facing import instructions included in the ZIP
kg_primary_dots/      — dotted handwriting-practice fonts (.ttf)
handwriting_practice/ — generated PDFs from generate_handwriting_pdf.py (gitignored)
.env                  — API keys (gitignored, never commit)
docs/
  note-types.md       — human-readable summary of models
  word-lists.md       — vocabulary roadmap: IT terms, phrases, phrasal verbs not yet in cards
  decks-overview.md   — why each deck exists, what gap it fills
  hint-dsl.md         — planned hint system for card Front fields (concept, not implemented yet)
  ielts-roadmap.md    — IELTS Writing skill roadmap for l2-vocab
  ielts-trends.md     — IELTS Task 1 trend-description vocab for l2-vocab
  ielts-vocab.md      — IELTS Task 2 topic vocab/collocations for l2-vocab
backups/              — .colpkg snapshots (gitignored)

# peripheral, not part of the Anki pipeline:
brain/constructions.md — personal grammar constructions reference notes
SKILLS.md              — Claude Code skill def for generating it-deck term cards
video_prepare/         — staging pipeline for producing video-by-movies clips (own README)
reviews_and_strategy/  — YouTube stream review/strategy notes, unrelated to flashcards
```

## decks

| dir                                        | Anki deck name  | cards | purpose                                                                                                             |
| ------------------------------------------ | --------------- | ----- | ------------------------------------------------------------------------------------------------------------------- |
| [it-deck](./decks/it-deck/)                 | IT_deck         | 1071  | IT professional vocabulary — sentence production for work communication                                            |
| [video-by-movies](./decks/video-by-movies/) | Video_by_movies | 1516  | Listening + spoken fluency — clips from Sherlock, Silicon Valley, Secret Life of Pets                              |
| [interview](./decks/interview/)             | Interview       | 240   | Interview prep: State = interview question (ukr), Front = ukr translation of answer (manual), Back = English answer |
| [l2-vocab](./decks/l2-vocab/)               | L2_vocab        | 407   | Vocabulary from ESOL L2 Writing/Reading course — has drifted toward IELTS Writing (see docs/ielts-roadmap.md)       |
| [medicine](./decks/medicine/)               | Medicine        | 201   | Medical vocabulary for GP visits and health conversations                                                           |
| [book](./decks/book/)                       | Book            | 53    | Phrases and expressions collected while reading English books                                                       |
| [test-english](./decks/test-english/)       | test-english    | 130   | Grammar & vocabulary from test-english.com — sentence production                                                    |

See [docs/decks-overview.md](./docs/decks-overview.md) for full context on each deck.

The current source contains **3,618 cards across seven decks**. Counts above describe the YAML source
and are refreshed when this README is updated; the generated release manifest records exact counts
and checksums for each package.
