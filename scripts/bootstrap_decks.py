"""
bootstrap_decks.py — one-time export of card data from Anki to flat YAML files.

What it does:
  - queries AnkiConnect (HTTP localhost:8765)
  - for each deck creates decks/<safe-name>/{_meta.yaml, cards.yaml}
  - does NOT touch templates, CSS, or media — card data only

Usage:
  source .venv/bin/activate
  python scripts/bootstrap_decks.py
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

import requests
import yaml

ANKI_URL = "http://localhost:8765"
OUTPUT_DIR = Path("decks")

# Built-in decks to skip
SKIP_DECKS = {"Default"}


def anki(action, **params):
    """Single AnkiConnect call. Raises on error."""
    response = requests.post(
        ANKI_URL,
        json={"action": action, "version": 6, "params": params},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise RuntimeError(f"AnkiConnect error on {action}: {data['error']}")
    return data["result"]


def safe_dirname(name):
    """'How to Win Friends' -> 'how-to-win-friends'. Used for directory names."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9а-яіїєґ]+", "-", name, flags=re.IGNORECASE)
    return name.strip("-")


def yaml_dump(data, path):
    """YAML with settings for human-readable output."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            allow_unicode=True,      # Cyrillic as-is, not \uXXXX
            sort_keys=False,         # preserve key order
            default_flow_style=False,
            width=100,
            indent=2,
        )


def main():
    # 1. Connectivity check
    try:
        version = anki("version")
        print(f"✓ AnkiConnect v{version} is up")
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to AnkiConnect (localhost:8765).")
        print("  Is Anki running? Is the add-on installed?")
        sys.exit(1)

    # 2. Deck list
    deck_names = anki("deckNames")
    deck_names = [d for d in deck_names if d not in SKIP_DECKS]
    print(f"✓ Found {len(deck_names)} decks: {deck_names}")

    OUTPUT_DIR.mkdir(exist_ok=True)

    total_notes = 0

    # 3. Iterate decks
    for deck_name in deck_names:
        # Anki query syntax: quotes around name in case it contains spaces
        note_ids = anki("findNotes", query=f'deck:"{deck_name}"')

        if not note_ids:
            print(f"  ⊘ {deck_name}: empty, skipping")
            continue

        # Fetch full note data in one batch request
        notes_info = anki("notesInfo", notes=note_ids)

        # Group by Note Type — a deck may contain more than one
        by_model = defaultdict(list)
        for note in notes_info:
            by_model[note["modelName"]].append(note)

        # Warn if a deck contains multiple Note Types
        if len(by_model) > 1:
            print(
                f"  ⚠ {deck_name}: found {len(by_model)} different Note Types — "
                f"{list(by_model.keys())}. Creating separate cards.<type>.yaml files"
            )

        deck_dir = OUTPUT_DIR / safe_dirname(deck_name)
        deck_dir.mkdir(parents=True, exist_ok=True)

        # _meta.yaml: deck metadata
        primary_model = max(by_model.keys(), key=lambda m: len(by_model[m]))
        meta = {
            "deckName": deck_name,
            "noteType": primary_model,
        }
        if len(by_model) > 1:
            meta["additionalNoteTypes"] = [m for m in by_model if m != primary_model]
        yaml_dump(meta, deck_dir / "_meta.yaml")

        # cards.yaml: the notes
        for model_name, notes in by_model.items():
            cards = []
            for note in notes:
                cards.append({
                    "id": note["noteId"],
                    # AnkiConnect returns {fieldName: {value, order}}
                    # we only need value, sorted by order
                    "fields": {
                        name: data["value"]
                        for name, data in sorted(
                            note["fields"].items(),
                            key=lambda kv: kv[1]["order"],
                        )
                    },
                    "tags": note["tags"],
                })

            # Single type → cards.yaml, multiple types → cards.<safe-type>.yaml
            if len(by_model) == 1:
                filename = "cards.yaml"
            else:
                filename = f"cards.{safe_dirname(model_name)}.yaml"

            yaml_dump(cards, deck_dir / filename)
            print(f"  ✓ {deck_name} / {model_name}: {len(cards)} notes → {filename}")
            total_notes += len(cards)

    print(f"\n✓ Done. Exported {total_notes} notes to ./{OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
