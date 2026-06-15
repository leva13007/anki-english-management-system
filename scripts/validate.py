"""
validate.py — linter for the Anki card repository.

Checks invariants that must always hold.

Usage:
  source .venv/bin/activate
  python scripts/validate.py

Exit codes:
  0 — all good (warnings may be present)
  1 — errors found; sync will not run
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

MODELS_DIR = Path("models")
DECKS_DIR = Path("decks")
MEDIA_DIR = Path("media")


# ─────────────────────────── helpers ───────────────────────────


class Report:
    """Collects errors and warnings, prints them grouped at the end."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, msg, location=None):
        self.errors.append((location, msg))

    def warn(self, msg, location=None):
        self.warnings.append((location, msg))

    def print_summary(self):
        if self.warnings:
            print(f"\n⚠ Warnings ({len(self.warnings)}):")
            for loc, msg in self.warnings:
                prefix = f"  [{loc}] " if loc else "  "
                print(f"{prefix}{msg}")

        if self.errors:
            print(f"\n✗ Errors ({len(self.errors)}):")
            for loc, msg in self.errors:
                prefix = f"  [{loc}] " if loc else "  "
                print(f"{prefix}{msg}")
            return False
        return True


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def normalize_for_dup_check(text):
    """Normalise text to a canonical form for near-duplicate detection."""
    if not text:
        return ""
    s = text.lower()
    s = s.replace("&nbsp;", " ")
    s = re.sub(r"<[^>]+>", "", s)        # strip HTML tags
    s = re.sub(r"[^\w\s]", "", s, flags=re.UNICODE)  # strip punctuation
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ─────────────────────────── model loading ───────────────────────────


def load_models(report):
    """{noteType -> {fields: [...], mediaFields: [...]}}."""
    models = {}
    for meta_path in MODELS_DIR.glob("*/_meta.yaml"):
        try:
            meta = load_yaml(meta_path)
        except yaml.YAMLError as e:
            report.error(f"YAML parse error: {e}", str(meta_path))
            continue

        if not meta or "noteType" not in meta or "fields" not in meta:
            report.error("missing noteType or fields in _meta.yaml", str(meta_path))
            continue

        # sortField — the field Anki uses for uniqueness checking.
        # Defaults to the first field if not explicitly set.
        sort_field = meta.get("sortField") or meta["fields"][0]
        if sort_field not in meta["fields"]:
            report.error(
                f"sortField {sort_field!r} is not in fields: {meta['fields']}",
                str(meta_path),
            )
            continue

        models[meta["noteType"]] = {
            "fields": meta["fields"],
            "mediaFields": meta.get("mediaFields", []),
            "sortField": sort_field,
            "path": meta_path,
        }
    return models


# ─────────────────────────── card iteration ───────────────────────────


def iter_cards(report):
    """Yields (deck_meta, cards_file, card_index, card_dict)."""
    for deck_meta_path in DECKS_DIR.glob("*/_meta.yaml"):
        try:
            deck_meta = load_yaml(deck_meta_path)
        except yaml.YAMLError as e:
            report.error(f"YAML parse error: {e}", str(deck_meta_path))
            continue

        deck_dir = deck_meta_path.parent

        for cards_file in sorted(deck_dir.glob("cards*.yaml")):
            try:
                cards = load_yaml(cards_file) or []
            except yaml.YAMLError as e:
                report.error(f"YAML parse error: {e}", str(cards_file))
                continue

            if not isinstance(cards, list):
                report.error("expected a list of notes in this file", str(cards_file))
                continue

            for idx, card in enumerate(cards):
                yield deck_meta, cards_file, idx, card


# ─────────────────────────── checks ───────────────────────────


def check_structure(card, card_loc, models, deck_meta, report):
    """Note structure check and Note Type validation."""
    if not isinstance(card, dict):
        report.error("note is not a dict", card_loc)
        return None

    if "fields" not in card:
        report.error("missing 'fields' key", card_loc)
        return None

    # Which Note Type is expected in this file?
    note_type = deck_meta.get("noteType")
    if note_type not in models:
        report.error(f"unknown Note Type: {note_type!r}", card_loc)
        return None

    model = models[note_type]
    expected_fields = set(model["fields"])
    actual_fields = set(card["fields"].keys())

    missing = expected_fields - actual_fields
    extra = actual_fields - expected_fields

    if missing:
        report.error(f"missing fields: {sorted(missing)}", card_loc)
    if extra:
        report.error(f"extra fields: {sorted(extra)} (not in _meta.yaml)", card_loc)

    return note_type


def check_empty_fields(card, card_loc, card_id, report):
    id_str = f"id={card_id}" if card_id is not None else "no id"
    for field, value in card["fields"].items():
        if not (value or "").strip():
            report.warn(f"empty field {field!r}  [{card_loc} ({id_str})]")


def check_html_noise(card, card_loc, card_id, report):
    """Looks for &nbsp; and unnecessary <div> wrappers in text fields."""
    id_str = f"id={card_id}" if card_id is not None else "no id"

    for field, value in card["fields"].items():
        if not value:
            continue

        if "&nbsp;" in value:
            # Show ~30 chars of context around the first &nbsp;
            pos = value.find("&nbsp;")
            start = max(0, pos - 25)
            end = min(len(value), pos + len("&nbsp;") + 25)
            prefix = "..." if start > 0 else ""
            suffix = "..." if end < len(value) else ""
            fragment = prefix + value[start:end] + suffix
            report.warn(
                f"field {field!r} contains &nbsp;\n"
                f"      {fragment!r}\n"
                f"      [{card_loc} ({id_str})]"
            )

        # <div>...</div> wrapping the entire content with no clear reason
        if re.match(r"^\s*<div>[^<]*</div>\s*$", value):
            preview = value if len(value) <= 80 else value[:77] + "..."
            report.warn(
                f"field {field!r} unnecessarily wrapped in <div>\n"
                f"      {preview!r}\n"
                f"      [{card_loc} ({id_str})]"
            )


def check_media_references(card, card_loc, models, deck_meta, available_media, used_media, report):
    note_type = deck_meta.get("noteType")
    if note_type not in models:
        return
    media_fields = models[note_type]["mediaFields"]
    for field in media_fields:
        filename = (card["fields"].get(field) or "").strip()
        if not filename:
            continue
        used_media.add(filename)
        if filename not in available_media:
            report.error(
                f"reference to {filename!r} in field {field!r} — file missing from media/",
                card_loc,
            )


# ─────────────────────────── main ───────────────────────────


def main():
    report = Report()

    # 1. Models
    models = load_models(report)
    if not models:
        report.error("no models found in models/")
        report.print_summary()
        sys.exit(1)

    # 2. Media inventory
    available_media = set()
    if MEDIA_DIR.is_dir():
        available_media = {p.name for p in MEDIA_DIR.iterdir() if p.is_file()}

    # 3. Global state for duplicate detection
    ids_seen = {}                          # id -> location
    # note_type -> {sort_value: (location, id)}
    sort_values_by_type = defaultdict(dict)
    # note_type -> {normalized_value: [(location, id, original_value)]}
    normalized_by_type = defaultdict(dict)
    used_media = set()

    total_cards = 0

    # 4. Walk all cards
    for deck_meta, cards_file, idx, card in iter_cards(report):
        total_cards += 1
        card_loc = f"{cards_file}#{idx}"

        note_type = check_structure(card, card_loc, models, deck_meta, report)
        if note_type is None:
            continue

        card_id = card.get("id")

        check_empty_fields(card, card_loc, card_id, report)
        check_html_noise(card, card_loc, card_id, report)
        check_media_references(card, card_loc, models, deck_meta, available_media, used_media, report)

        # Duplicate id (within YAML — our bug)
        if card_id is not None:
            if card_id in ids_seen:
                report.error(
                    f"duplicate id={card_id}\n"
                    f"      here:  {card_loc}\n"
                    f"      also:  {ids_seen[card_id]}"
                )
            else:
                ids_seen[card_id] = card_loc

        # Duplicate sortField value within a Note Type (Anki rejects addNote).
        # For most types this is Front; for video — VideoFilename.
        sort_field = models[note_type]["sortField"]
        sort_value = (card["fields"].get(sort_field) or "").strip()
        if sort_value:
            preview = sort_value if len(sort_value) <= 80 else sort_value[:77] + "..."
            id_str = f"id={card_id}" if card_id is not None else "no id"

            if sort_value in sort_values_by_type[note_type]:
                other_loc, other_id = sort_values_by_type[note_type][sort_value]
                other_id_str = f"id={other_id}" if other_id is not None else "no id"
                report.error(
                    f"duplicate {sort_field} in Note Type {note_type!r}\n"
                    f"      {sort_field}: {preview!r}\n"
                    f"      here:  {card_loc}  ({id_str})\n"
                    f"      also:  {other_loc}  ({other_id_str})"
                )
            else:
                sort_values_by_type[note_type][sort_value] = (card_loc, card_id)

            # Near-duplicate — warning. Makes sense for text sortFields and
            # also for filenames (catches hello.mp3 vs Hello.mp3).
            norm = normalize_for_dup_check(sort_value)
            if norm:
                normalized_by_type[note_type].setdefault(norm, []).append(
                    (card_loc, card_id, sort_value, sort_field)
                )

    # 5. Near-duplicates — checked after full walk
    for note_type, groups in normalized_by_type.items():
        for norm, entries in groups.items():
            if len(entries) > 1:
                # If all values are identical, it was already caught as an error;
                # only warn when originals differ.
                unique_values = {value for _, _, value, _ in entries}
                if len(unique_values) < 2:
                    continue

                sort_field = entries[0][3]
                lines = [
                    f"similar {sort_field} in Note Type {note_type!r} (after normalisation):"
                ]
                for loc, card_id, value, _ in entries:
                    preview = value if len(value) <= 80 else value[:77] + "..."
                    id_str = f"id={card_id}" if card_id is not None else "no id"
                    lines.append(f"      {loc} ({id_str}): {preview!r}")
                report.warn("\n".join(lines))

    # 6. Orphaned files in media/
    orphans = available_media - used_media
    if orphans:
        examples = sorted(orphans)[:5]
        more = f", and {len(orphans) - 5} more" if len(orphans) > 5 else ""
        report.warn(
            f"{len(orphans)} files in media/ with no references (examples: {examples}{more})"
        )

    # 7. Summary
    print(f"Checked {total_cards} notes across {len(models)} Note Types")
    print(f"Media: {len(available_media)} files in media/, {len(used_media)} referenced")

    ok = report.print_summary()
    if not report.errors and not report.warnings:
        print("\n✓ All clean")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
