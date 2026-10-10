#!/usr/bin/env python3
"""Build a portable ZIP of Anki deck packages from the open Anki profile.

Requires Anki with AnkiConnect enabled and a successful repository sync.
The exported packages contain cards, note types/templates, and media, but no
review scheduling history.
"""

import argparse
import hashlib
import json
import re
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
ANKI_URL = "http://127.0.0.1:8765"
DEFAULT_OUTPUT = ROOT / "distribution" / "build"
MEDIA_DIR = ROOT / "media"
MEDIA_EXTENSIONS = "mp3|webm|ogg|wav|m4a|mp4|png|jpg|jpeg|gif|svg|webp"


def anki(action, **params):
    response = requests.post(
        ANKI_URL,
        json={"action": action, "version": 6, "params": params},
        timeout=300,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise RuntimeError(f"AnkiConnect {action}: {data['error']}")
    return data["result"]


def load_decks():
    decks = []
    for meta_path in sorted((ROOT / "decks").glob("*/_meta.yaml")):
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        cards = []
        for cards_path in sorted(meta_path.parent.glob("cards*.yaml")):
            cards.extend(yaml.safe_load(cards_path.read_text(encoding="utf-8")) or [])
        decks.append({
            "directory": meta_path.parent.name,
            "name": meta["deckName"],
            "note_type": meta["noteType"],
            "cards": cards,
        })
    return decks


def safe_filename(name):
    return "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")


def media_files_for_deck(deck, model_media_fields, media_by_casefold):
    """Resolve media refs in declared media fields to the repository files."""
    filenames = set()
    pattern = re.compile(rf"[^\s<>\"']+\.(?:{MEDIA_EXTENSIONS})", re.IGNORECASE)
    for card in deck["cards"]:
        fields = card.get("fields", {}) or {}
        for field in model_media_fields:
            value = fields.get(field, "") or ""
            for reference in pattern.findall(str(value)):
                filename = reference.rsplit("/", 1)[-1].rstrip(")]},;:")
                filenames.add(filename)
    missing = sorted(name for name in filenames if name.casefold() not in media_by_casefold)
    if missing:
        raise RuntimeError(f"{deck['name']}: referenced media missing from media/: {missing[:5]}")
    return [(name, media_by_casefold[name.casefold()]) for name in sorted(filenames, key=str.casefold)]


def embed_media(package_path, media_files):
    """Add custom-template media refs to Anki's numeric media map in an .apkg."""
    if not media_files:
        return
    with zipfile.ZipFile(package_path, "r") as source:
        original = [(item.filename, source.read(item.filename))
                    for item in source.infolist() if item.filename != "media"]
    media_map = {str(index): filename for index, (filename, _) in enumerate(media_files)}
    with tempfile.NamedTemporaryFile(dir=package_path.parent, suffix=".apkg", delete=False) as temp:
        temp_path = Path(temp.name)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as target:
            for name, data in original:
                target.writestr(name, data)
            target.writestr("media", json.dumps(media_map, ensure_ascii=False))
            for index, (_, media_path) in enumerate(media_files):
                target.write(media_path, str(index))
        temp_path.replace(package_path)
    finally:
        temp_path.unlink(missing_ok=True)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"output directory (default: {DEFAULT_OUTPUT})")
    args = parser.parse_args()
    output = args.output.expanduser().resolve()

    try:
        version = anki("version")
        decks = load_decks()
        if not decks:
            raise RuntimeError("No decks found under decks/.")

        # Fail closed if the local Anki profile does not represent the YAML source.
        for deck in decks:
            expected = {card.get("id") for card in deck["cards"]}
            if None in expected:
                raise RuntimeError(
                    f"{deck['directory']}: some cards have no Anki id; sync the repository first."
                )
            actual = set(anki("findNotes", query=f'deck:"{deck["name"]}"'))
            missing = expected - actual
            if missing:
                raise RuntimeError(
                    f"{deck['name']}: {len(missing)} YAML note(s) are missing from Anki. "
                    "Run scripts/sync.py, then retry."
                )

        models = {}
        for meta_path in (ROOT / "models").glob("*/_meta.yaml"):
            model = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
            models[model["noteType"]] = model
        media_by_casefold = {path.name.casefold(): path for path in MEDIA_DIR.iterdir() if path.is_file()}

        output.mkdir(parents=True, exist_ok=True)
        package_dir = output / "anki-english-decks"
        package_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "anki_version": version,
            "review_history_included": False,
            "decks": [],
        }

        for deck in decks:
            package_name = f"{safe_filename(deck['directory'])}.apkg"
            package_path = package_dir / package_name
            anki("exportPackage", deck=deck["name"], path=str(package_path), includeSched=False)
            if not package_path.is_file() or package_path.stat().st_size == 0:
                raise RuntimeError(f"Anki did not create a valid package for {deck['name']}.")
            model = models.get(deck["note_type"])
            if model is None:
                raise RuntimeError(f"No model metadata found for {deck['note_type']}.")
            media_files = media_files_for_deck(deck, model.get("mediaFields", []), media_by_casefold)
            embed_media(package_path, media_files)
            with zipfile.ZipFile(package_path) as archive:
                if archive.testzip() is not None:
                    raise RuntimeError(f"Anki package failed ZIP integrity check: {package_name}")
                media_map = json.loads(archive.read("media"))
                if len(media_map) != len(media_files):
                    raise RuntimeError(f"{deck['name']}: package does not include all referenced media.")
            manifest["decks"].append({
                "name": deck["name"],
                "directory": deck["directory"],
                "note_type": deck["note_type"],
                "notes": len(deck["cards"]),
                "media_files": len(media_files),
                "file": package_name,
                "size_bytes": package_path.stat().st_size,
                "sha256": sha256(package_path),
            })
            print(f"✓ {deck['name']}: {len(deck['cards'])} notes → {package_name}")

        (package_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        install = ROOT / "distribution" / "INSTALL.txt"
        zip_path = output / "anki-english-decks.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            archive.write(install, "INSTALL.txt")
            for path in sorted(package_dir.iterdir()):
                archive.write(path, f"decks/{path.name}")
        with zipfile.ZipFile(zip_path) as archive:
            if archive.testzip() is not None:
                raise RuntimeError("The distribution ZIP failed its integrity check.")
        print(f"\nDistribution ready: {zip_path}")
        print(f"Size: {zip_path.stat().st_size / (1024 * 1024):.1f} MiB")
    except (requests.RequestException, RuntimeError, KeyError, ValueError, OSError, zipfile.BadZipFile) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
