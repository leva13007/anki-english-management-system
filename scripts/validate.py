"""
validate.py — лінтер репозиторію Anki-карток.

Перевіряє інваріанти, які мають триматись завжди.

Запуск:
  source .venv/bin/activate
  python scripts/validate.py

Exit codes:
  0 — все ок (warnings можуть бути)
  1 — знайдені errors, sync не запустиш
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

MODELS_DIR = Path("models")
DECKS_DIR = Path("decks")
MEDIA_DIR = Path("media")


# ─────────────────────────── допоміжне ───────────────────────────


class Report:
    """Збирає errors і warnings, виводить групами в кінці."""

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
    """Зведення тексту до канонічної форми для пошуку 'майже-дублів'."""
    if not text:
        return ""
    s = text.lower()
    s = s.replace("&nbsp;", " ")
    s = re.sub(r"<[^>]+>", "", s)        # знімаємо HTML-теги
    s = re.sub(r"[^\w\s]", "", s, flags=re.UNICODE)  # знімаємо пунктуацію
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ─────────────────────────── завантаження моделей ───────────────────────────


def load_models(report):
    """{noteType -> {fields: [...], mediaFields: [...]}}."""
    models = {}
    for meta_path in MODELS_DIR.glob("*/_meta.yaml"):
        try:
            meta = load_yaml(meta_path)
        except yaml.YAMLError as e:
            report.error(f"YAML не парситься: {e}", str(meta_path))
            continue

        if not meta or "noteType" not in meta or "fields" not in meta:
            report.error("немає noteType або fields у _meta.yaml", str(meta_path))
            continue

        # sortField — поле, по якому Anki перевіряє унікальність.
        # Якщо явно не вказано — перше поле в списку (дефолт Anki).
        sort_field = meta.get("sortField") or meta["fields"][0]
        if sort_field not in meta["fields"]:
            report.error(
                f"sortField {sort_field!r} не входить у fields: {meta['fields']}",
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


# ─────────────────────────── обхід карток ───────────────────────────


def iter_cards(report):
    """Yields (deck_meta, cards_file, card_index, card_dict)."""
    for deck_meta_path in DECKS_DIR.glob("*/_meta.yaml"):
        try:
            deck_meta = load_yaml(deck_meta_path)
        except yaml.YAMLError as e:
            report.error(f"YAML не парситься: {e}", str(deck_meta_path))
            continue

        deck_dir = deck_meta_path.parent

        for cards_file in sorted(deck_dir.glob("cards*.yaml")):
            try:
                cards = load_yaml(cards_file) or []
            except yaml.YAMLError as e:
                report.error(f"YAML не парситься: {e}", str(cards_file))
                continue

            if not isinstance(cards, list):
                report.error("очікую список нотаток у файлі", str(cards_file))
                continue

            for idx, card in enumerate(cards):
                yield deck_meta, cards_file, idx, card


# ─────────────────────────── перевірки ───────────────────────────


def check_structure(card, card_loc, models, deck_meta, report):
    """Структура нотатки + наявність Note Type."""
    if not isinstance(card, dict):
        report.error("нотатка не є словником", card_loc)
        return None

    if "fields" not in card:
        report.error("немає ключа 'fields'", card_loc)
        return None

    # Який тип очікуємо в цьому файлі?
    note_type = deck_meta.get("noteType")
    if note_type not in models:
        report.error(f"невідомий Note Type: {note_type!r}", card_loc)
        return None

    model = models[note_type]
    expected_fields = set(model["fields"])
    actual_fields = set(card["fields"].keys())

    missing = expected_fields - actual_fields
    extra = actual_fields - expected_fields

    if missing:
        report.error(f"відсутні поля: {sorted(missing)}", card_loc)
    if extra:
        report.error(f"зайві поля: {sorted(extra)} (немає в _meta.yaml)", card_loc)

    return note_type


def check_empty_fields(card, card_loc, card_id, report):
    id_str = f"id={card_id}" if card_id is not None else "no id"
    for field, value in card["fields"].items():
        if not (value or "").strip():
            report.warn(f"порожнє поле {field!r}  [{card_loc} ({id_str})]")


def check_html_noise(card, card_loc, card_id, report):
    """Шукає &nbsp; та зайві <div> у текстових полях."""
    id_str = f"id={card_id}" if card_id is not None else "no id"

    for field, value in card["fields"].items():
        if not value:
            continue

        if "&nbsp;" in value:
            # Контекст: ~30 символів навколо першого &nbsp;
            pos = value.find("&nbsp;")
            start = max(0, pos - 25)
            end = min(len(value), pos + len("&nbsp;") + 25)
            prefix = "..." if start > 0 else ""
            suffix = "..." if end < len(value) else ""
            fragment = prefix + value[start:end] + suffix
            report.warn(
                f"поле {field!r} містить &nbsp;\n"
                f"      {fragment!r}\n"
                f"      [{card_loc} ({id_str})]"
            )

        # <div>...</div> навколо всього тексту без явної причини
        if re.match(r"^\s*<div>[^<]*</div>\s*$", value):
            preview = value if len(value) <= 80 else value[:77] + "..."
            report.warn(
                f"поле {field!r} обгорнуте в <div> без потреби\n"
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
                f"посилання на {filename!r} у полі {field!r} — файлу немає в media/",
                card_loc,
            )


# ─────────────────────────── головне ───────────────────────────


def main():
    report = Report()

    # 1. Моделі
    models = load_models(report)
    if not models:
        report.error("не знайшов жодної моделі в models/")
        report.print_summary()
        sys.exit(1)

    # 2. Медіа-інвентаризація
    available_media = set()
    if MEDIA_DIR.is_dir():
        available_media = {p.name for p in MEDIA_DIR.iterdir() if p.is_file()}

    # 3. Глобальні стани для дублів
    ids_seen = {}                          # id -> location
    # note_type -> {sort_value: (location, id)}
    sort_values_by_type = defaultdict(dict)
    # note_type -> {normalized_value: [(location, id, original_value)]}
    normalized_by_type = defaultdict(dict)
    used_media = set()

    total_cards = 0

    # 4. Обхід усіх карток
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

        # Дубль id (всередині YAML — наша помилка)
        if card_id is not None:
            if card_id in ids_seen:
                report.error(
                    f"дубль id={card_id}\n"
                    f"      тут:   {card_loc}\n"
                    f"      також: {ids_seen[card_id]}"
                )
            else:
                ids_seen[card_id] = card_loc

        # Дубль значення sortField у межах Note Type (Anki впаде на створенні).
        # Для більшості типів це Front, для video — VideoFilename.
        sort_field = models[note_type]["sortField"]
        sort_value = (card["fields"].get(sort_field) or "").strip()
        if sort_value:
            preview = sort_value if len(sort_value) <= 80 else sort_value[:77] + "..."
            id_str = f"id={card_id}" if card_id is not None else "no id"

            if sort_value in sort_values_by_type[note_type]:
                other_loc, other_id = sort_values_by_type[note_type][sort_value]
                other_id_str = f"id={other_id}" if other_id is not None else "no id"
                report.error(
                    f"дубль {sort_field} у Note Type {note_type!r}\n"
                    f"      {sort_field}: {preview!r}\n"
                    f"      тут:   {card_loc}  ({id_str})\n"
                    f"      також: {other_loc}  ({other_id_str})"
                )
            else:
                sort_values_by_type[note_type][sort_value] = (card_loc, card_id)

            # Нормалізований дубль — warning. Для текстових sortField має сенс,
            # для імен файлів (video) — теж: ловить hello.mp3 vs Hello.mp3.
            norm = normalize_for_dup_check(sort_value)
            if norm:
                normalized_by_type[note_type].setdefault(norm, []).append(
                    (card_loc, card_id, sort_value, sort_field)
                )

    # 5. Нормалізовані дублі — після обходу
    for note_type, groups in normalized_by_type.items():
        for norm, entries in groups.items():
            if len(entries) > 1:
                # Якщо всі значення абсолютно однакові — це вже зловлено як error,
                # warning тут буде шумом. Показуємо тільки якщо оригінали різні.
                unique_values = {value for _, _, value, _ in entries}
                if len(unique_values) < 2:
                    continue

                sort_field = entries[0][3]
                lines = [
                    f"схожі {sort_field} у Note Type {note_type!r} (після нормалізації):"
                ]
                for loc, card_id, value, _ in entries:
                    preview = value if len(value) <= 80 else value[:77] + "..."
                    id_str = f"id={card_id}" if card_id is not None else "no id"
                    lines.append(f"      {loc} ({id_str}): {preview!r}")
                report.warn("\n".join(lines))

    # 6. Орфани в media/
    orphans = available_media - used_media
    if orphans:
        examples = sorted(orphans)[:5]
        more = f", ще {len(orphans) - 5}" if len(orphans) > 5 else ""
        report.warn(
            f"{len(orphans)} файлів у media/ без посилань (приклад: {examples}{more})"
        )

    # 7. Підсумок
    print(f"Перевірено {total_cards} нотаток у {len(models)} типах")
    print(f"Медіа: {len(available_media)} файлів у media/, {len(used_media)} використовуються")

    ok = report.print_summary()
    if not report.errors and not report.warnings:
        print("\n✓ Все чисто")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()