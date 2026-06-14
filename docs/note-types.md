# Note Types

All custom Anki note types used across decks in this project.

## Basic-UA-EN

Simple two-sided card. Ukrainian → English.

| field | description |
|-------|-------------|
| UA | Ukrainian word or phrase (front) |
| EN | English translation (back) |

Used by: `it-vocab`

---

## Basic-UA-EN-Audio

Like Basic-UA-EN but includes an audio clip on the back.

| field | description |
|-------|-------------|
| UA | Ukrainian word or phrase (front) |
| EN | English translation (back) |
| Audio | Audio file reference, e.g. `[sound:word.mp3]` |

Used by: `medical`

---

## Sentence-Video

Full sentence in context, linked to a video clip.

| field | description |
|-------|-------------|
| UA | Ukrainian translation of the sentence |
| EN | English sentence (front) |
| Video | Video clip reference |
| Context | Where the sentence is from (chapter, page, timestamp) |

Used by: `how-to-win-friends`
