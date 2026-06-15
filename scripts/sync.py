"""
sync.py — pushes local repo changes to Anki.

Workflow:
  1. reads decks/*, models/*, media/
  2. compares each card in cards.yaml against Anki
  3. builds an action plan (add, update, upload media)
  4. in dry-run — prints the plan
  5. otherwise — asks for confirmation, applies, writes new ids to YAML

Usage:
  python scripts/sync.py --dry-run             # preview plan, no changes
  python scripts/sync.py                       # apply with confirmation
  python scripts/sync.py --check-media-hashes  # also compare MD5 hashes of media
  python scripts/sync.py --prune               # remove orphaned notes from Anki

Exit codes:
  0 — all good
  1 — error (data anomaly, interrupted sync)
"""

import argparse
import base64
import hashlib
import sys
from collections import defaultdict
from pathlib import Path

import requests
import yaml

ANKI_URL = "http://localhost:8765"
MODELS_DIR = Path("models")
DECKS_DIR = Path("decks")
MEDIA_DIR = Path("media")


# ─────────────────────────── AnkiConnect ───────────────────────────


def anki(action, **params):
    response = requests.post(
        ANKI_URL,
        json={"action": action, "version": 6, "params": params},
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise RuntimeError(f"AnkiConnect {action}: {data['error']}")
    return data["result"]


# ─────────────────────────── repo loading ───────────────────────────


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def dump_yaml(data, path):
    """Write with conservative formatting to keep git diffs minimal."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            data, f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=100,
            indent=2,
        )


def load_models():
    """{noteType -> {fields, mediaFields, sortField}}."""
    models = {}
    for meta_path in MODELS_DIR.glob("*/_meta.yaml"):
        meta = load_yaml(meta_path)
        if not meta:
            continue
        note_type = meta["noteType"]
        models[note_type] = {
            "fields": meta["fields"],
            "mediaFields": meta.get("mediaFields", []),
            "sortField": meta.get("sortField") or meta["fields"][0],
        }
    return models


def load_decks():
    """Yields (deck_name, note_type, cards_file_path, cards_list).

    cards_list is a reference to the parsed YAML list — mutations are reflected on dump.
    """
    for deck_meta_path in sorted(DECKS_DIR.glob("*/_meta.yaml")):
        deck_meta = load_yaml(deck_meta_path)
        deck_dir = deck_meta_path.parent

        for cards_file in sorted(deck_dir.glob("cards*.yaml")):
            cards = load_yaml(cards_file) or []
            # If a deck has multiple types, _meta only describes the primary one.
            # For cards.<type>.yaml the type should be derived differently — for now we use meta.
            yield deck_meta["deckName"], deck_meta["noteType"], cards_file, cards


# ─────────────────────────── plan ───────────────────────────


class Plan:
    """Collects all actions, then executes them in one batch."""

    def __init__(self):
        self.to_add = []        # [(deck_name, note_type, card_ref, cards_file)]
        self.to_update = []     # [(note_id, new_fields, new_tags, card_loc)]
        self.media_to_upload = [] # [filename]
        self.errors = []        # ["text"]
        self.warnings = []      # ["text"]
        self.orphan_note_ids = []  # noteIds present in Anki but missing from YAML

    def has_errors(self):
        return bool(self.errors)

    def has_changes(self):
        return bool(self.to_add or self.to_update or self.media_to_upload)

    def print_summary(self):
        print()
        print("─" * 60)
        print("PLAN:")
        print(f"  notes to add:    {len(self.to_add)}")
        print(f"  notes to update: {len(self.to_update)}")
        print(f"  media to upload: {len(self.media_to_upload)}")
        if self.orphan_note_ids:
            print(f"  orphans in Anki: {len(self.orphan_note_ids)} (ignored without --prune)")
        print("─" * 60)

        if self.warnings:
            print(f"\n⚠ Warnings ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"  {w}")

        if self.errors:
            print(f"\n✗ Errors ({len(self.errors)}):")
            for e in self.errors:
                print(f"  {e}")


# ─────────────────────────── comparison ───────────────────────────


def normalize_fields_from_anki(note):
    """notesInfo returns {name: {value, order}}; we only need {name: value}."""
    return {name: data["value"] for name, data in note["fields"].items()}


def fields_differ(yaml_fields, anki_fields):
    """Returns True if any field differs."""
    if set(yaml_fields.keys()) != set(anki_fields.keys()):
        return True
    return any(yaml_fields[k] != anki_fields[k] for k in yaml_fields)


def tags_differ(yaml_tags, anki_tags):
    return set(yaml_tags or []) != set(anki_tags or [])


def file_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ─────────────────────────── plan building ───────────────────────────


def build_plan(models, check_media_hashes):
    plan = Plan()

    # 1. Collect all ids from YAML — used to find orphans
    yaml_note_ids = set()

    # 2. Load Anki state: all noteIds from our decks
    deck_note_ids = {}  # deck_name -> set of noteIds in Anki
    seen_decks = set()
    for deck_name, _, _, _ in load_decks():
        seen_decks.add(deck_name)

    print("✓ Fetching Anki state...")
    anki_note_ids_all = set()
    for deck_name in seen_decks:
        ids = anki("findNotes", query=f'deck:"{deck_name}"')
        deck_note_ids[deck_name] = set(ids)
        anki_note_ids_all.update(ids)
    print(f"  notes in Anki across our decks: {len(anki_note_ids_all)}")

    # 3. Fetch full note info in one request
    anki_notes = {}
    if anki_note_ids_all:
        notes_info = anki("notesInfo", notes=list(anki_note_ids_all))
        for note in notes_info:
            anki_notes[note["noteId"]] = note

    # 4. Walk YAML
    for deck_name, note_type, cards_file, cards in load_decks():
        if note_type not in models:
            plan.errors.append(
                f"{cards_file}: unknown Note Type {note_type!r}"
            )
            continue

        for idx, card in enumerate(cards):
            card_loc = f"{cards_file}#{idx}"
            card_id = card.get("id")
            yaml_fields = card.get("fields", {})
            yaml_tags = card.get("tags", []) or []

            if card_id is None:
                # New card
                plan.to_add.append({
                    "deck": deck_name,
                    "model": note_type,
                    "fields": yaml_fields,
                    "tags": yaml_tags,
                    "card_ref": card,           # for writing id back
                    "cards_file": cards_file,
                    "loc": card_loc,
                })
                continue

            yaml_note_ids.add(card_id)

            if card_id not in anki_notes:
                # Anomaly: id is in YAML but no such note exists in Anki
                plan.errors.append(
                    f"{card_loc}: id={card_id} is set in YAML but the note does not exist in Anki. "
                    f"Either restore the note in Anki or remove the id (it will be re-created, SRS progress lost)."
                )
                continue

            anki_note = anki_notes[card_id]
            anki_fields = normalize_fields_from_anki(anki_note)

            if fields_differ(yaml_fields, anki_fields) or tags_differ(yaml_tags, anki_note.get("tags", [])):
                plan.to_update.append({
                    "id": card_id,
                    "fields": yaml_fields,
                    "tags": yaml_tags,
                    "anki_tags": anki_note.get("tags", []),
                    "loc": card_loc,
                })

    # 5. Orphaned notes in Anki
    orphans = anki_note_ids_all - yaml_note_ids
    plan.orphan_note_ids = sorted(orphans)

    # 6. Media
    # Collect all media files actually needed by cards
    needed_media = set()
    for _, note_type, _, cards in load_decks():
        if note_type not in models:
            continue
        media_fields = models[note_type]["mediaFields"]
        for card in cards:
            fields = card.get("fields", {})
            for field in media_fields:
                filename = (fields.get(field) or "").strip()
                if filename:
                    needed_media.add(filename)

    print("✓ Checking media...")
    # Which of them are already in Anki
    if needed_media:
        in_anki = set(anki("getMediaFilesNames", pattern="*"))
    else:
        in_anki = set()

    local_files = {p.name for p in MEDIA_DIR.iterdir() if p.is_file()} if MEDIA_DIR.exists() else set()

    for filename in sorted(needed_media):
        local_path = MEDIA_DIR / filename
        if not local_path.exists():
            plan.errors.append(f"media file {filename!r} is referenced in cards but missing from media/")
            continue

        if filename not in in_anki:
            plan.media_to_upload.append(filename)
            continue

        if check_media_hashes:
            anki_b64 = anki("retrieveMediaFile", filename=filename)
            if anki_b64:
                anki_md5 = hashlib.md5(base64.b64decode(anki_b64)).hexdigest()
                local_md5 = file_md5(local_path)
                if anki_md5 != local_md5:
                    plan.media_to_upload.append(filename)
                    plan.warnings.append(
                        f"media {filename!r}: local hash ≠ Anki — will re-upload"
                    )

    return plan


# ─────────────────────────── plan execution ───────────────────────────


def upload_media(plan):
    """Upload media first so files are in Anki before notes that reference them are added."""
    if not plan.media_to_upload:
        return

    print(f"\n→ Uploading {len(plan.media_to_upload)} media files...")
    for i, filename in enumerate(plan.media_to_upload, 1):
        local_path = MEDIA_DIR / filename
        with open(local_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        anki("storeMediaFile", filename=filename, data=data)
        print(f"  [{i:04d}/{len(plan.media_to_upload)}] {filename}")


def add_notes(plan):
    """Add new notes and write back the generated noteIds into the YAML structures."""
    if not plan.to_add:
        return

    print(f"\n→ Adding {len(plan.to_add)} new notes...")

    # Group by cards_file — we need to rewrite each file after adding
    files_changed = set()

    for i, item in enumerate(plan.to_add, 1):
        try:
            new_id = anki(
                "addNote",
                note={
                    "deckName": item["deck"],
                    "modelName": item["model"],
                    "fields": item["fields"],
                    "tags": item["tags"],
                    "options": {
                        "allowDuplicate": False,
                    },
                },
            )
            # Write id back into the structure (it's a reference — mutation shows up in the file)
            # id must be the first key in the card dict — rebuild it.
            new_card = {"id": new_id}
            for k, v in item["card_ref"].items():
                if k != "id":
                    new_card[k] = v
            item["card_ref"].clear()
            item["card_ref"].update(new_card)

            files_changed.add(item["cards_file"])
            print(f"  [{i:04d}/{len(plan.to_add)}] {item['loc']} → id={new_id}")
        except Exception as e:
            print(f"  ✗ {item['loc']}: {e}")

    print(f"\n→ Writing ids back to {len(files_changed)} file(s)...")
    for cards_file in files_changed:
        # Find all cards from this file in plan.to_add
        items_for_file = [item for item in plan.to_add if item["cards_file"] == cards_file]
        # Re-read the file
        cards = load_yaml(cards_file) or []
        # Locate new ids by index and update
        for item in items_for_file:
            loc_idx = int(item["loc"].rsplit("#", 1)[1])
            new_id = item["card_ref"].get("id")
            if new_id is None:
                continue
            existing = cards[loc_idx]
            new_card = {"id": new_id}
            for k, v in existing.items():
                if k != "id":
                    new_card[k] = v
            cards[loc_idx] = new_card
        dump_yaml(cards, cards_file)


def update_notes(plan):
    if not plan.to_update:
        return

    print(f"\n→ Updating {len(plan.to_update)} notes...")
    for i, item in enumerate(plan.to_update, 1):
        try:
            anki(
                "updateNoteFields",
                note={
                    "id": item["id"],
                    "fields": item["fields"],
                },
            )

            # Tags — separate call: compute diff
            old_tags = set(item["anki_tags"])
            new_tags = set(item["tags"])
            to_add = new_tags - old_tags
            to_remove = old_tags - new_tags
            if to_add:
                anki("addTags", notes=[item["id"]], tags=" ".join(to_add))
            if to_remove:
                anki("removeTags", notes=[item["id"]], tags=" ".join(to_remove))

            print(f"  [{i:04d}/{len(plan.to_update)}] id={item['id']} ({item['loc']})")
        except Exception as e:
            print(f"  ✗ {item['loc']}: {e}")


def prune_orphans(plan):
    if not plan.orphan_note_ids:
        print("\nNo orphaned notes")
        return

    print(f"\n⚠ Found {len(plan.orphan_note_ids)} notes in Anki that are absent from YAML:")
    # Show first 10 with context
    sample_ids = plan.orphan_note_ids[:10]
    sample_info = anki("notesInfo", notes=sample_ids)
    for note in sample_info:
        fields = normalize_fields_from_anki(note)
        # Use the first non-empty field as a preview
        preview = next((v for v in fields.values() if v), "")
        if len(preview) > 60:
            preview = preview[:57] + "..."
        print(f"  id={note['noteId']}: {preview!r}")
    if len(plan.orphan_note_ids) > 10:
        print(f"  ... and {len(plan.orphan_note_ids) - 10} more")

    confirm = input(f"\nDelete all {len(plan.orphan_note_ids)} notes from Anki? SRS progress will be lost. [y/N] ")
    if confirm.lower() != "y":
        print("Cancelled")
        return

    anki("deleteNotes", notes=plan.orphan_note_ids)
    print(f"✓ Deleted {len(plan.orphan_note_ids)} notes")


# ─────────────────────────── main ───────────────────────────


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="show the plan without making any changes")
    ap.add_argument("--check-media-hashes", action="store_true",
                    help="compare MD5 of local and Anki media files (slower)")
    ap.add_argument("--prune", action="store_true",
                    help="delete from Anki notes absent from YAML (with confirmation)")
    args = ap.parse_args()

    try:
        anki("version")
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to AnkiConnect. Is Anki running?")
        sys.exit(1)

    models = load_models()
    if not models:
        print("✗ No models found in models/")
        sys.exit(1)

    plan = build_plan(models, check_media_hashes=args.check_media_hashes)
    plan.print_summary()

    if plan.has_errors():
        print("\n✗ Sync aborted due to errors. Fix them and re-run.")
        sys.exit(1)

    if not plan.has_changes() and not args.prune:
        print("\n✓ Everything is up to date.")
        return

    if args.dry_run:
        print("\n(dry-run, nothing changed)")
        return

    if plan.has_changes():
        confirm = input("\nApply changes? [y/N] ")
        if confirm.lower() != "y":
            print("Cancelled")
            return

        upload_media(plan)
        add_notes(plan)
        update_notes(plan)
        print("\n✓ Sync complete")

    if args.prune:
        prune_orphans(plan)


if __name__ == "__main__":
    main()
