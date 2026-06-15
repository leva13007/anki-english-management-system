# Note Types

Human-readable summary. Authoritative schema is in `models/*/_meta.yaml`.

---

## Basic (type in the answer) + audio

Dir: `models/basic-type-in-the-answer-audio/`

| field | description |
|-------|-------------|
| Front | English sentence or word (shown on front) |
| Back | Ukrainian translation (shown on back) |
| Audio | Audio file reference, e.g. `[sound:filename.mp3]` |

Used by: `book`, `it-deck`, `l2-vocab`, `medicine`

---

## Basic (with typing)+audio+state

Dir: `models/basic-with-typing-audio-state/`

| field | description |
|-------|-------------|
| Front | English sentence or word |
| Back | Ukrainian translation |
| Audio | Audio file reference |
| State | Learning state or note (usage TBD) |

Used by: `interview`

---

## Video (type in the answer)

Dir: `models/video-type-in-the-answer/`

| field | description |
|-------|-------------|
| Front | English sentence from the video |
| Back | Ukrainian translation |
| VideoFilename | Video clip filename, e.g. `00001.webm` |

Used by: `video-by-movies`
