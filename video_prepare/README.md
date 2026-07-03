# video_prepare

Staging area for producing a new batch of `video-by-movies` clips, before they
get merged into `decks/video-by-movies/cards.yaml` + `media/` and synced to
Anki. Not a deck itself, not scripted end-to-end — a working folder for a
manual pipeline.

One episode is worked on at a time. When it's done, this folder gets cleared
out (or overwritten) for the next episode.

## Layout

| path | what it is |
|------|-----------|
| `link.md` | Log of episodes worked on: show/episode, opensubtitles link, status (`in progress` / `done`), last video filename produced. |
| `*.srt` | Subtitles for the current episode, downloaded from the link in `link.md`. Source of English text + timing for cutting clips. |
| `tracks/*.mov` | Raw clips exported from Final Cut Pro after cutting, renamed to `0001.mov, 0002.mov, …` (sequential within this batch, not the final card number). |
| `converted_webm/*.webm` | Output of `src/convert_tracks.sh` — final, effect-processed clips named `<show>_NNNN.webm`, ready to drop into `media/`. |
| `vocab.csv` | `English;Ukrainian;filename` — one row per clip, matching `converted_webm` filenames. |
| `src/remane.sh` | Renames FCP export filenames into sequential `000N.mov`. |
| `src/convert_tracks.sh` | ffmpeg pass: crop, flip, watermark, desaturate, slow down, add noise, encode to vp9/opus. |

## Workflow

1. **Pick an episode**, find subtitles on opensubtitles, add a row to
   `link.md` with status `in progress`. Download the `.srt` into this folder.

2. **Find the next available card number.** Check the highest existing
   `<show>_NNNN.webm` in `media/` (or the last row of
   `decks/video-by-movies/cards.yaml` for that show) and continue from there.
   This number becomes both the starting `counter` in `convert_tracks.sh` and
   the last entry recorded in `link.md`.

3. **Cut clips in Final Cut Pro** for the chosen scenes/lines (short
   fragments, a few seconds each), export as `.mov` into `tracks/`. FCP
   exports come out named like `91 - 720WebShareName.mov`.

4. **Rename raw tracks** — from `video_prepare/src/`:
   ```bash
   ./remane.sh
   ```
   Strips the FCP suffix and renumbers files sequentially as `0001.mov,
   0002.mov, …` inside `tracks/`.

5. **Convert clips** — edit `counter` at the top of `convert_tracks.sh` to the
   next available card number from step 2, then from `video_prepare/src/`:
   ```bash
   ./convert_tracks.sh
   ```
   For each `.mov` in `tracks/`, runs one ffmpeg pass that:
   - crops out letterbox/logo (`crop=iw-80:ih-60`)
   - flips horizontally and desaturates (`hflip`, `hue=s=0.25`)
   - slows down and adds grain/blur (`fps=18`, `setpts=1.08*PTS`, `noise`, `boxblur`)
   - overlays `watermark.png` centered
   - encodes to `libvpx-vp9`/`libopus`, ~450kbps, 503px wide

   These transforms exist so clips aren't a verbatim copy of the source
   file — deliberate, not incidental. Output goes to `converted_webm/` as
   `<show>_NNNN.webm`, counter incrementing per file.

6. **Fill in `vocab.csv`.** One row per clip: the English line (from the
   `.srt`), its Ukrainian translation, and the matching
   `converted_webm` filename — `English;Ukrainian;filename`.

7. **Merge into the deck** (manual — no script does this yet):
   - copy each `converted_webm/*.webm` into `media/`
   - append one entry per row of `vocab.csv` to
     `decks/video-by-movies/cards.yaml`:
     ```yaml
     - id: <new anki noteId, or omit — sync.py fills it in>
       fields:
         VideoFilename: <show>_NNNN.webm
         Front: <English line>
         Back: <Ukrainian translation>
       tags: []
     ```

8. **Sync to Anki:**
   ```bash
   python scripts/sync.py --dry-run   # review the plan
   python scripts/sync.py             # apply
   ```

9. **Update `link.md`** status to `done` (or leave `in progress` with the
   latest `last video file` if the episode isn't fully clipped yet), and
   update the clip count for the show in `CLAUDE.md` / `docs/decks-overview.md`.

## Notes

- Numbering is per-show, not global — `sherlok_*`, `silicon_valley_*`,
  `pets_*` each have their own counter.
- `tracks/` and `converted_webm/` are scratch — once a batch is merged into
  `media/` and synced, they can be emptied for the next episode.
- This folder is currently untracked in git (not committed, not
  gitignored) — treat it as local working state, not versioned history.
