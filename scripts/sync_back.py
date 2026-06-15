"""
sync_back.py — pull changes from Anki back into local YAML.

Workflow:
  1. reads current state of the repo and Anki
  2. for each card compares — if Anki differs, updates the YAML
  3. cards new in Anki (added via GUI) — warning or --add-new
  4. cards deleted in Anki — warning (does NOT remove from YAML)
  5. new media in Anki — warning or --download-media

Usage:
  python scripts/sync_back.py --dry-run
  python scripts/sync_back.py
  python scripts/sync_back.py --add-new            # also write new Anki cards to YAML
  python scripts/sync_back.py --download-media     # also download missing media files

After running: `git diff` shows all changes. If something looks wrong — `git checkout decks/`.

Exit codes:
  0 — ok
  1 — error (could not connect, could not write file)
"""

import argparse
import base64
import sys
from collections import defaultdict
from pathlib import Path

import requests
import yaml

ANKI_URL = "http://localhost:8765"
MODELS_DIR = Path("models")
DECKS_DIR = Path("decks")
MEDIA_DIR = Path("media")


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


def normalize_fields_from_anki(note):
    return {name: data["value"] for name, data in note["fields"].items()}


# ─────────────────────────── repo model ───────────────────────────


def load_repo_state():
    """
    Returns:
      decks_meta: {deck_name -> {"noteType": ..., "cards_files": [Path]}}
      cards_by_id: {note_id -> (cards_file, idx, card_dict)}
      cards_files_data: {cards_file -> list_of_cards}  (for writing back)
      models: {note_type -> {fields, mediaFields, sortField}}
    """
    models = {}
    for meta_path in MODELS_DIR.glob("*/_meta.yaml"):
        meta = load_yaml(meta_path)
        if not meta:
            continue
        models[meta["noteType"]] = {
            "fields": meta["fields"],
            "mediaFields": meta.get("mediaFields", []),
            "sortField": meta.get("sortField") or meta["fields"][0],
        }

    decks_meta = {}
    cards_by_id = {}
    cards_files_data = {}

    for deck_meta_path in DECKS_DIR.glob("*/_meta.yaml"):
        deck_meta = load_yaml(deck_meta_path)
        deck_name = deck_meta["deckName"]
        deck_dir = deck_meta_path.parent

        cards_files = []
        for cards_file in sorted(deck_dir.glob("cards*.yaml")):
            cards = load_yaml(cards_file) or []
            cards_files_data[cards_file] = cards
            cards_files.append(cards_file)

            for idx, card in enumerate(cards):
                card_id = card.get("id")
                if card_id is not None:
                    cards_by_id[card_id] = (cards_file, idx, card)

        decks_meta[deck_name] = {
            "noteType": deck_meta["noteType"],
            "cards_files": cards_files,
            "deck_dir": deck_dir,
        }

    return decks_meta, cards_by_id, cards_files_data, models


# ─────────────────────────── update plan ───────────────────────────


class BackPlan:
    def __init__(self):
        self.updates = []         # [(card_file, idx, old_fields, new_fields, old_tags, new_tags)]
        self.new_in_anki = []     # [(note_id, deck_name, anki_note)]
        self.missing_in_anki = [] # [(note_id, card_file, idx)]
        self.new_media = []       # [filename]
        self.errors = []
        self.changed_files = set()

    def print_summary(self):
        print()
        print("─" * 60)
        print("PLAN:")
        print(f"  update in YAML:           {len(self.updates)}")
        print(f"  new in Anki (not in YAML): {len(self.new_in_anki)}")
        print(f"  missing in Anki:          {len(self.missing_in_anki)}")
        print(f"  new media in Anki:        {len(self.new_media)}")
        print("─" * 60)

        if self.errors:
            print(f"\n✗ Errors ({len(self.errors)}):")
            for e in self.errors:
                print(f"  {e}")


def build_plan(decks_meta, cards_by_id, models):
    plan = BackPlan()

    # 1. Collect Anki state for our decks
    print("✓ Fetching Anki state...")
    anki_note_to_deck = {}
    all_anki_ids = set()
    for deck_name in decks_meta:
        ids = anki("findNotes", query=f'deck:"{deck_name}"')
        for nid in ids:
            anki_note_to_deck[nid] = deck_name
        all_anki_ids.update(ids)

    print(f"  notes in Anki across our decks: {len(all_anki_ids)}")

    if not all_anki_ids:
        return plan, set()

    # 2. Fetch full note data
    notes_info = anki("notesInfo", notes=list(all_anki_ids))
    anki_notes = {n["noteId"]: n for n in notes_info}

    # 3. Cards present in both YAML and Anki — compare
    for note_id, (cards_file, idx, card) in cards_by_id.items():
        if note_id not in anki_notes:
            plan.missing_in_anki.append((note_id, cards_file, idx))
            continue

        anki_note = anki_notes[note_id]
        anki_fields = normalize_fields_from_anki(anki_note)
        yaml_fields = card.get("fields", {})

        anki_tags = sorted(anki_note.get("tags", []))
        yaml_tags = sorted(card.get("tags", []) or [])

        fields_changed = yaml_fields != anki_fields
        tags_changed = yaml_tags != anki_tags

        if fields_changed or tags_changed:
            plan.updates.append({
                "cards_file": cards_file,
                "idx": idx,
                "note_id": note_id,
                "yaml_fields": yaml_fields,
                "anki_fields": anki_fields,
                "yaml_tags": yaml_tags,
                "anki_tags": anki_note.get("tags", []),
                "fields_changed": fields_changed,
                "tags_changed": tags_changed,
            })

    # 4. Cards in Anki but not in YAML — added via GUI
    yaml_ids = set(cards_by_id.keys())
    new_ids = all_anki_ids - yaml_ids
    for note_id in sorted(new_ids):
        deck_name = anki_note_to_deck[note_id]
        plan.new_in_anki.append((note_id, deck_name, anki_notes[note_id]))

    # 5. Media: all filenames referenced by Anki notes
    needed_from_anki = set()
    for note in anki_notes.values():
        model = models.get(note["modelName"])
        if not model:
            continue
        anki_fields = normalize_fields_from_anki(note)
        for field in model["mediaFields"]:
            filename = (anki_fields.get(field) or "").strip()
            if filename:
                needed_from_anki.add(filename)

    local_media = {p.name for p in MEDIA_DIR.iterdir() if p.is_file()} if MEDIA_DIR.exists() else set()
    plan.new_media = sorted(needed_from_anki - local_media)

    return plan, all_anki_ids


# ─────────────────────────── applying the plan ───────────────────────────


def show_field_diff(yaml_fields, anki_fields):
    """Small visual diff for a single note's fields."""
    lines = []
    all_keys = set(yaml_fields) | set(anki_fields)
    for k in sorted(all_keys):
        y = yaml_fields.get(k, "")
        a = anki_fields.get(k, "")
        if y != a:
            y_preview = y if len(y) <= 60 else y[:57] + "..."
            a_preview = a if len(a) <= 60 else a[:57] + "..."
            lines.append(f"      {k}:")
            lines.append(f"        - YAML: {y_preview!r}")
            lines.append(f"        + Anki: {a_preview!r}")
    return "\n".join(lines)


def apply_updates(plan, cards_files_data):
    """Update in-memory cards_files_data structures."""
    for upd in plan.updates:
        cards = cards_files_data[upd["cards_file"]]
        card = cards[upd["idx"]]

        # Preserve key order: id, fields, tags
        new_card = {"id": upd["note_id"]}
        new_card["fields"] = upd["anki_fields"]
        new_card["tags"] = upd["anki_tags"]

        cards[upd["idx"]] = new_card
        plan.changed_files.add(upd["cards_file"])


def add_new_from_anki(plan, cards_files_data, decks_meta):
    """Append new cards from Anki to the appropriate cards.yaml files."""
    # Group new cards by deck
    by_deck = defaultdict(list)
    for note_id, deck_name, anki_note in plan.new_in_anki:
        by_deck[deck_name].append((note_id, anki_note))

    for deck_name, items in by_deck.items():
        if deck_name not in decks_meta:
            plan.errors.append(f"new cards in deck {deck_name!r} but no matching dir in decks/")
            continue

        # Which cards.yaml to write to? Use the primary one (no type suffix).
        # If the deck has multiple cards.*.yaml files, each type gets its own file.
        cards_files = decks_meta[deck_name]["cards_files"]

        for note_id, anki_note in items:
            note_type = anki_note["modelName"]
            # Find the file that already has cards of this type
            target_file = None
            for cf in cards_files:
                cards = cards_files_data[cf]
                if cards and any(
                    True for c in cards  # simplified: use the first cards*.yaml in the deck
                ):
                    target_file = cf
                    break

            if target_file is None and cards_files:
                target_file = cards_files[0]

            if target_file is None:
                plan.errors.append(
                    f"new card id={note_id} in deck {deck_name} "
                    f"but no cards.yaml found in decks/{deck_name}/"
                )
                continue

            new_card = {
                "id": note_id,
                "fields": normalize_fields_from_anki(anki_note),
                "tags": anki_note.get("tags", []),
            }
            cards_files_data[target_file].append(new_card)
            plan.changed_files.add(target_file)


def download_new_media(plan):
    if not plan.new_media:
        return

    print(f"\n→ Downloading {len(plan.new_media)} new media files...")
    MEDIA_DIR.mkdir(exist_ok=True)
    for i, filename in enumerate(plan.new_media, 1):
        try:
            b64 = anki("retrieveMediaFile", filename=filename)
            if not b64:
                print(f"  [{i:04d}/{len(plan.new_media)}] ✗ {filename}: not found in Anki")
                continue
            data = base64.b64decode(b64)
            (MEDIA_DIR / filename).write_bytes(data)
            print(f"  [{i:04d}/{len(plan.new_media)}] ✓ {filename}")
        except Exception as e:
            print(f"  [{i:04d}/{len(plan.new_media)}] ✗ {filename}: {e}")


def write_changed_files(plan, cards_files_data):
    if not plan.changed_files:
        return
    print(f"\n→ Writing {len(plan.changed_files)} cards.yaml file(s)...")
    for cf in sorted(plan.changed_files):
        dump_yaml(cards_files_data[cf], cf)
        print(f"  ✓ {cf}")


# ─────────────────────────── main ───────────────────────────


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--add-new", action="store_true",
                    help="write cards added in Anki via GUI into YAML")
    ap.add_argument("--download-media", action="store_true",
                    help="download media files missing locally")
    args = ap.parse_args()

    try:
        anki("version")
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to AnkiConnect. Is Anki running?")
        sys.exit(1)

    decks_meta, cards_by_id, cards_files_data, models = load_repo_state()
    if not models:
        print("✗ No models found in models/")
        sys.exit(1)

    plan, _ = build_plan(decks_meta, cards_by_id, models)
    plan.print_summary()

    # Show first 5 updates as examples (no --verbose flag yet)
    if plan.updates:
        print(f"\nSample updates (first 5):")
        for upd in plan.updates[:5]:
            print(f"  {upd['cards_file']}#{upd['idx']}  (id={upd['note_id']})")
            if upd["fields_changed"]:
                print(show_field_diff(upd["yaml_fields"], upd["anki_fields"]))
            if upd["tags_changed"]:
                print(f"      tags: {upd['yaml_tags']} → {upd['anki_tags']}")

    if plan.new_in_anki:
        print(f"\nNew in Anki (first 5):")
        for note_id, deck_name, anki_note in plan.new_in_anki[:5]:
            fields = normalize_fields_from_anki(anki_note)
            preview = next((v for v in fields.values() if v), "")
            if len(preview) > 60:
                preview = preview[:57] + "..."
            print(f"  id={note_id} ({deck_name}): {preview!r}")
        if not args.add_new:
            print("  (use --add-new to write them to YAML)")

    if plan.missing_in_anki:
        print(f"\n⚠ Cards in YAML not found in Anki (possibly deleted manually):")
        for note_id, cards_file, idx in plan.missing_in_anki[:5]:
            print(f"  id={note_id} ({cards_file}#{idx})")
        if len(plan.missing_in_anki) > 5:
            print(f"  ... and {len(plan.missing_in_anki) - 5} more")
        print("  sync_back does not remove these — resolve manually.")

    if plan.new_media and not args.download_media:
        print(f"\n⚠ {len(plan.new_media)} media files in Anki not present locally")
        print("  (use --download-media to download)")

    has_changes = (
        plan.updates or
        (plan.new_in_anki and args.add_new) or
        (plan.new_media and args.download_media)
    )

    if not has_changes:
        print("\n✓ Nothing to change.")
        return

    if args.dry_run:
        print("\n(dry-run, no changes made)")
        return

    confirm = input("\nApply changes to YAML/media? [y/N] ")
    if confirm.lower() != "y":
        print("Cancelled")
        return

    apply_updates(plan, cards_files_data)
    if args.add_new:
        add_new_from_anki(plan, cards_files_data, decks_meta)
    if args.download_media:
        download_new_media(plan)

    write_changed_files(plan, cards_files_data)

    print("\n✓ Done. Run `git diff` to review changes before committing.")
    print("  To revert: `git checkout decks/ media/`")


if __name__ == "__main__":
    main()