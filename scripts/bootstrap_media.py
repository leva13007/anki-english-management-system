"""
bootstrap_media.py — downloads media files from Anki into the local media/ directory.

What it does:
  - reads mediaFields from each models/*/_meta.yaml
  - determines which fields contain media per Note Type
  - scans decks/*/cards.yaml and collects all referenced filenames
  - downloads via AnkiConnect (idempotent — skips files already present)
  - warns about orphaned files in media/ (does not delete them)

Usage:
  source .venv/bin/activate
  python scripts/bootstrap_media.py
"""

import base64
import hashlib
import sys
from pathlib import Path

import requests
import yaml

ANKI_URL = "http://localhost:8765"
MEDIA_DIR = Path("media")
MODELS_DIR = Path("models")
DECKS_DIR = Path("decks")


def anki(action, **params):
    response = requests.post(
        ANKI_URL,
        json={"action": action, "version": 6, "params": params},
        timeout=60,  # videos can be large
    )
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise RuntimeError(f"AnkiConnect error on {action}: {data['error']}")
    return data["result"]


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def human_size(n):
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def build_model_media_map():
    """{noteType -> [field_name, ...]} from models/*/_meta.yaml."""
    result = {}
    for meta_path in MODELS_DIR.glob("*/_meta.yaml"):
        meta = load_yaml(meta_path)
        media_fields = meta.get("mediaFields", [])
        if media_fields:
            result[meta["noteType"]] = media_fields
    return result


def collect_required_files(model_media_map):
    """Walks decks/*/cards*.yaml and collects unique media filenames."""
    required = set()
    references = 0

    for meta_path in DECKS_DIR.glob("*/_meta.yaml"):
        deck_dir = meta_path.parent

        # A deck may have one primary noteType or several (cards.<type>.yaml)
        for cards_file in deck_dir.glob("cards*.yaml"):
            cards = load_yaml(cards_file) or []
            for note in cards:
                fields = note.get("fields", {})
                # Identify which Note Type matches this card by checking its fields
                # For each known type, check whether all its media fields are present
                for note_type, media_fields in model_media_map.items():
                    if all(f in fields for f in media_fields):
                        for field in media_fields:
                            value = (fields.get(field) or "").strip()
                            if value:
                                required.add(value)
                                references += 1
                        break  # stop once a matching type is found

    return required, references


def file_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    try:
        anki("version")
        print("✓ AnkiConnect is up")
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to AnkiConnect. Is Anki running?")
        sys.exit(1)

    model_media_map = build_model_media_map()
    if not model_media_map:
        print("✗ No mediaFields found in any models/*/_meta.yaml")
        sys.exit(1)

    print("✓ Media fields by Note Type:")
    for note_type, fields in model_media_map.items():
        print(f"    {note_type}: {fields}")

    required, refs = collect_required_files(model_media_map)
    print(f"\n✓ Cards reference {refs} media values, {len(required)} unique files")

    MEDIA_DIR.mkdir(exist_ok=True)

    # How many we already have locally
    already_have = {p.name for p in MEDIA_DIR.iterdir() if p.is_file()}
    to_download = sorted(required - already_have)
    already_present = required & already_have

    print(f"  already local: {len(already_present)}")
    print(f"  to download: {len(to_download)}")

    if not to_download:
        print("\n✓ All required files already present")
    else:
        confirm = input(f"\nDownload {len(to_download)} files? [y/N] ")
        if confirm.lower() != "y":
            print("Cancelled")
            sys.exit(0)

        total_bytes = 0
        for i, filename in enumerate(to_download, 1):
            try:
                # retrieveMediaFile returns a base64 string or False if not found
                b64 = anki("retrieveMediaFile", filename=filename)
                if not b64:
                    print(f"  [{i:04d}/{len(to_download)}] ✗ {filename}: not found in Anki")
                    continue

                data = base64.b64decode(b64)
                out_path = MEDIA_DIR / filename
                out_path.write_bytes(data)
                total_bytes += len(data)
                print(
                    f"  [{i:04d}/{len(to_download)}] ✓ {filename} "
                    f"({human_size(len(data))})"
                )
            except Exception as e:
                print(f"  [{i:04d}/{len(to_download)}] ✗ {filename}: {e}")

        print(f"\n✓ Downloaded {human_size(total_bytes)}")

    # Orphaned files in media/
    orphans = already_have - required
    if orphans:
        print(f"\n⚠ Found {len(orphans)} orphaned files in ./{MEDIA_DIR}/")
        print("  (no card references — not deleting automatically)")
        for name in sorted(orphans)[:10]:
            print(f"    {name}")
        if len(orphans) > 10:
            print(f"    ... and {len(orphans) - 10} more")


if __name__ == "__main__":
    main()
