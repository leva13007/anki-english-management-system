"""
import_backlog.py — interactive import of decks/<deck>/backlog.md into cards.yaml.

Walks through lines in backlog.md that aren't cards yet, proposes a Ukrainian
translation for each (Google Translate via deep-translator), and on
acceptance appends a new card to cards.yaml immediately (Back = English line,
Front = translation, Audio/State left empty for later steps).

Usage:
  python scripts/import_backlog.py --deck interview

Keys during session:
  y — accept the proposed translation, save card, next line
  e — edit the translation before saving
  s — skip this line (leave it for a future run)
  q — quit, save progress so far

Exit codes:
  0 — ok
  1 — bad args or missing files
"""

import argparse
import sys
import termios
import textwrap
import tty
from pathlib import Path

import yaml
from deep_translator import GoogleTranslator

DECKS_DIR = Path("decks")
SEP = "─" * 52


# ─────────────────────────── helpers ───────────────────────────


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


def load_backlog_lines(path):
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            lines.append(line)
    return lines


def getch():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


# ─────────────────────────── translation ───────────────────────────


def translate(text):
    return GoogleTranslator(source="en", target="uk").translate(text)


# ─────────────────────────── TUI ───────────────────────────


def print_line(english, translation, session_idx, total):
    print(f"\n{SEP}")
    print(f"[{session_idx}/{total}]")
    print(SEP)
    print(textwrap.fill(f"EN: {english}", width=60, subsequent_indent="    "))
    print(textwrap.fill(f"UK: {translation}", width=60, subsequent_indent="    "))
    print(SEP)


def prompt_key():
    print("  [y] accept  [e] edit  [s] skip  [q] quit > ", end="", flush=True)
    key = getch().lower()
    print(key)
    return key


# ─────────────────────────── session ───────────────────────────


def run_session(deck_dir):
    backlog_path = deck_dir / "backlog.md"
    if not backlog_path.exists():
        print(f"✗ No backlog.md found in {deck_dir}")
        sys.exit(1)

    cards_path = deck_dir / "cards.yaml"
    if not cards_path.exists():
        print(f"✗ No cards.yaml found in {deck_dir}")
        sys.exit(1)

    all_cards = load_yaml(cards_path) or []
    existing_back = {
        (c.get("fields", {}).get("Back") or "").strip()
        for c in all_cards
    }

    backlog_lines = load_backlog_lines(backlog_path)
    pending = [line for line in backlog_lines if line not in existing_back]

    if not pending:
        print("✓ backlog.md has nothing new. Nothing to do.")
        return

    print(f"\n✓ Backlog lines: {len(backlog_lines)}  |  New: {len(pending)}")
    print(f"  Keys: [y] accept  [e] edit  [s] skip  [q] quit")

    accepted = skipped = 0

    for session_idx, english in enumerate(pending, 1):
        try:
            proposed = translate(english)
        except Exception as e:
            print(f"\n  ✗ Translation error: {e}")
            print("  [r] retry  [s] skip  [q] quit > ", end="", flush=True)
            key = getch().lower()
            print(key)
            if key == "r":
                try:
                    proposed = translate(english)
                except Exception as e2:
                    print(f"  ✗ Translation error again: {e2} — skipping")
                    skipped += 1
                    continue
            elif key == "q":
                break
            else:
                skipped += 1
                continue

        while True:
            print_line(english, proposed, session_idx, len(pending))
            key = prompt_key()

            if key == "y":
                all_cards.append({
                    "fields": {
                        "Front": proposed,
                        "Back": english,
                        "Audio": "",
                        "State": "",
                    },
                    "tags": ["interview"],
                })
                dump_yaml(all_cards, cards_path)
                print("  ✓ Saved")
                accepted += 1
                break

            elif key == "e":
                termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
                print("  New translation: ", end="", flush=True)
                edited = input().strip()
                if edited:
                    proposed = edited
                continue

            elif key == "s":
                print("  → skipped")
                skipped += 1
                break

            elif key == "q":
                _print_exit_summary(accepted, skipped, len(pending), session_idx)
                return

            else:
                print("  (y / e / s / q)")

    print(f"\n{SEP}")
    print(f"✓ Done! Accepted: {accepted}  Skipped: {skipped}")
    if accepted:
        print("  Run `python scripts/generate_audio.py --deck interview` to add audio next.")


def _print_exit_summary(accepted, skipped, total, current_idx):
    remaining = total - current_idx
    print(f"\n✓ Session ended. Accepted: {accepted}  Skipped: {skipped}  Remaining: {remaining}")
    if accepted:
        print("  Run `python scripts/generate_audio.py --deck interview` to add audio next.")


# ─────────────────────────── main ───────────────────────────


def main():
    ap = argparse.ArgumentParser(description="Import backlog.md lines into cards.yaml with UK translation")
    ap.add_argument("--deck", required=True, help="Deck directory name under decks/ (e.g. interview)")
    args = ap.parse_args()

    deck_dir = DECKS_DIR / args.deck
    if not deck_dir.is_dir():
        print(f"✗ Deck directory not found: {deck_dir}")
        sys.exit(1)

    run_session(deck_dir)


if __name__ == "__main__":
    main()
