"""
generate_audio.py — interactive ElevenLabs audio generation for Anki cards.

Walks through cards with an empty Audio field, generates MP3 via ElevenLabs TTS,
plays it back, and on acceptance saves to media/ and updates cards.yaml immediately.

Usage:
  python scripts/generate_audio.py --deck interview
  python scripts/generate_audio.py --deck l2-vocab

Keys during session:
  y — keep this audio, save to media/, next card
  p — replay without re-generating
  r — regenerate (new API call), play again
  s — skip this card (leave Audio empty)
  q — quit, save progress so far

Config via .env (project root):
  ELEVENLABS_API_KEY    — required
  ELEVENLABS_VOICE_IDS  — optional, comma-separated pool; random voice picked per card
  ELEVENLABS_VOICE_ID   — optional, single override (used if VOICE_IDS not set)
  ELEVENLABS_MODEL_ID   — optional, defaults to eleven_multilingual_v2

Exit codes:
  0 — ok
  1 — bad args or missing config
"""

import argparse
import hashlib
import random
import shutil
import subprocess
import sys
import tempfile
import termios
import textwrap
import tty
from pathlib import Path

import requests
import yaml

DECKS_DIR = Path("decks")
MODELS_DIR = Path("models")
MEDIA_DIR = Path("media")

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"

DEFAULT_VOICES = [
    ("Oleh",  "2E14mjucXVut8FlMiThE"),  # Ukrainian male
    ("Edward Sterling",    "VsQmyFHffusQDewmHB5v"),   # Corporate & Medical
    ("Sam",  "G7ILShrCNLfmS0A37SXS"),   # British Male - Warm, Articulate Non
    ("Dexter",    "oTQK6KgOJHp8UGGZjwUu"),   # Dynamic British Presenter
    ("Shelley",    "4CrZuIW9am7gYAxgo2Af"),   # Clear and confident British female
    ("Amelia",    "ZF6FPAbjXT4488VcRRnw"),   # young and enthusiastic
    ("Bradford",    "NNl6r8mD7vthiJatiJt1"),   # British Narrator, Storyteller
    ("Allison",    "Se2Vw1WbHmGbBbyWTuu4"),   # inviting and velvety British accent
    ("Blondie",    "exsUS4vynmxd379XN4yO"),   # Conversational
]

TEMP_AUDIO = Path(tempfile.gettempdir()) / "anki_audio_preview.mp3"
SEP = "─" * 52


# ─────────────────────────── helpers ───────────────────────────


def load_env():
    env = {}
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def dump_yaml(data, path):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            data, f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=100,
            indent=2,
        )


def find_model_meta(note_type):
    for meta_path in MODELS_DIR.glob("*/_meta.yaml"):
        meta = load_yaml(meta_path)
        if meta and meta.get("noteType") == note_type:
            return meta
    return None


def card_filename(deck_dir_name, card):
    card_id = card.get("id")
    if card_id:
        ident = str(card_id)
    else:
        front = card.get("fields", {}).get("Front", "")
        ident = hashlib.md5(front.encode()).hexdigest()[:12]
    return f"{deck_dir_name}_{ident}.mp3"


def getch():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


# ─────────────────────────── ElevenLabs ───────────────────────────


def generate_mp3(text, api_key, voice_id, model_id):
    url = ELEVENLABS_TTS_URL.format(voice_id=voice_id)
    resp = requests.post(
        url,
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": model_id,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.content


def play_mp3(path):
    subprocess.run(["afplay", str(path)], check=True)


# ─────────────────────────── TUI ───────────────────────────


def print_card(card, session_idx, total, deck_name):
    fields = card.get("fields", {})
    state = fields.get("State", "")
    front = fields.get("Front", "")
    back = fields.get("Back", "")

    print(f"\n{SEP}")
    header = f"[{session_idx}/{total}] {deck_name}"
    if state:
        header += f"  |  {state}"
    print(header)
    print(SEP)
    print(f"Q: {front}")
    wrapped = textwrap.fill(back, width=60, initial_indent="A: ", subsequent_indent="   ")
    print(wrapped)
    if len(back) > 500:
        print(f"   ({len(back)} chars)")
    print(SEP)


def prompt_key():
    print("  [y] keep  [p] replay  [r] regenerate  [s] skip  [q] quit > ", end="", flush=True)
    key = getch().lower()
    print(key)
    return key


# ─────────────────────────── session ───────────────────────────


def run_session(deck_dir, env):
    api_key = env.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("✗ ELEVENLABS_API_KEY not found in .env")
        sys.exit(1)

    model_id = env.get("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID)

    if env.get("ELEVENLABS_VOICE_IDS"):
        ids = [v.strip() for v in env["ELEVENLABS_VOICE_IDS"].split(",") if v.strip()]
        voices_pool = [(f"Voice {i+1}", vid) for i, vid in enumerate(ids)]
    elif env.get("ELEVENLABS_VOICE_ID"):
        voices_pool = [("Custom", env["ELEVENLABS_VOICE_ID"])]
    else:
        voices_pool = DEFAULT_VOICES

    meta_path = deck_dir / "_meta.yaml"
    if not meta_path.exists():
        print(f"✗ No _meta.yaml found in {deck_dir}")
        sys.exit(1)

    meta = load_yaml(meta_path)
    deck_name = meta["deckName"]
    note_type = meta.get("noteType", "")

    model_meta = find_model_meta(note_type)
    if model_meta:
        media_fields = model_meta.get("mediaFields", [])
        if "VideoFilename" in media_fields:
            print(f"✗ Deck '{deck_name}' uses video cards — audio generation not applicable.")
            sys.exit(1)

    cards_path = deck_dir / "cards.yaml"
    if not cards_path.exists():
        print(f"✗ No cards.yaml found in {deck_dir}")
        sys.exit(1)

    all_cards = load_yaml(cards_path) or []
    pending = [
        (i, c) for i, c in enumerate(all_cards)
        if not (c.get("fields", {}).get("Audio") or "").strip()
    ]

    if not pending:
        print(f"✓ All cards in '{deck_name}' already have audio. Nothing to do.")
        return

    total_cards = len(all_cards)
    voice_names = ", ".join(name for name, _ in voices_pool)
    print(f"\n✓ Deck: {deck_name}")
    print(f"  Total cards: {total_cards}  |  Missing audio: {len(pending)}")
    print(f"  Voice pool: {voice_names}")
    print(f"\n  Keys: [y] keep  [p] replay  [r] regenerate  [s] skip  [q] quit")

    MEDIA_DIR.mkdir(exist_ok=True)
    accepted = skipped = 0

    for session_idx, (card_idx, card) in enumerate(pending, 1):
        print_card(card, session_idx, len(pending), deck_name)

        back_text = (card.get("fields", {}).get("Back") or "").strip()
        if not back_text:
            print("  ⚠ Back field is empty — skipping")
            skipped += 1
            continue

        audio_bytes = None
        current_voice_name = None

        while True:
            if audio_bytes is None:
                current_voice_name, current_voice_id = random.choice(voices_pool)
                print(f"  ♪ Generating... [{current_voice_name}]", end=" ", flush=True)
                try:
                    audio_bytes = generate_mp3(back_text, api_key, current_voice_id, model_id)
                    TEMP_AUDIO.write_bytes(audio_bytes)
                    print("done. Playing...", flush=True)
                except requests.HTTPError as e:
                    print(f"\n  ✗ API error: {e.response.status_code} {e.response.text[:120]}")
                    print("  [r] retry  [s] skip  [q] quit > ", end="", flush=True)
                    key = getch().lower()
                    print(key)
                    if key == "r":
                        continue
                    elif key == "q":
                        _print_exit_summary(accepted, skipped, len(pending), session_idx)
                        return
                    else:
                        skipped += 1
                        break
                except Exception as e:
                    print(f"\n  ✗ Error: {e}")
                    skipped += 1
                    break
            else:
                print("  ♪ Playing...", flush=True)

            try:
                play_mp3(TEMP_AUDIO)
            except Exception as e:
                print(f"  ✗ Playback error: {e}")

            key = prompt_key()

            if key == "y":
                filename = card_filename(deck_dir.name, card)
                dest = MEDIA_DIR / filename
                shutil.copy2(TEMP_AUDIO, dest)
                all_cards[card_idx]["fields"]["Audio"] = filename
                dump_yaml(all_cards, cards_path)
                print(f"  ✓ Saved → media/{filename}")
                accepted += 1
                break

            elif key == "p":
                continue  # audio_bytes still set — skip generation, replay

            elif key == "r":
                audio_bytes = None  # force new API call
                continue

            elif key == "s":
                print("  → skipped")
                skipped += 1
                break

            elif key == "q":
                _print_exit_summary(accepted, skipped, len(pending), session_idx)
                return

            else:
                print("  (y / p / r / s / q)")

    print(f"\n{SEP}")
    print(f"✓ Done! Accepted: {accepted}  Skipped: {skipped}")
    if accepted:
        print(f"  Run `python scripts/sync.py` to push changes to Anki.")


def _print_exit_summary(accepted, skipped, total, current_idx):
    remaining = total - current_idx
    print(f"\n✓ Session ended. Accepted: {accepted}  Skipped: {skipped}  Remaining: {remaining}")
    if accepted:
        print(f"  Run `python scripts/sync.py` to push changes to Anki.")


# ─────────────────────────── main ───────────────────────────


def main():
    ap = argparse.ArgumentParser(description="Generate audio for Anki cards via ElevenLabs TTS")
    ap.add_argument("--deck", required=True, help="Deck directory name under decks/ (e.g. interview)")
    args = ap.parse_args()

    deck_dir = DECKS_DIR / args.deck
    if not deck_dir.is_dir():
        print(f"✗ Deck directory not found: {deck_dir}")
        sys.exit(1)

    env = load_env()
    run_session(deck_dir, env)


if __name__ == "__main__":
    main()
