"""
sync.py — синхронізація локального репо → Anki.

Workflow:
  1. читає decks/*, models/*, media/
  2. для кожної картки в cards.yaml порівнює стан з Anki
  3. будує план дій (add, update, upload media)
  4. у dry-run — друкує план
  5. інакше — питає підтвердження, виконує, дописує id у YAML для нових карток

Запуск:
  python scripts/sync.py --dry-run             # план без змін
  python scripts/sync.py                       # з підтвердженням
  python scripts/sync.py --check-media-hashes  # звіряти хеші локальних і Anki-медіа
  python scripts/sync.py --prune               # видалити осиротілі нотатки з Anki

Exit codes:
  0 — все ок
  1 — помилка (аномалія в даних, обірваний sync)
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


# ─────────────────────────── завантаження репо ───────────────────────────


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def dump_yaml(data, path):
    """Запис із консервативним форматуванням — щоб git diff був мінімальний."""
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

    cards_list — посилання на список з YAML, мутації відобразяться при dump.
    """
    for deck_meta_path in sorted(DECKS_DIR.glob("*/_meta.yaml")):
        deck_meta = load_yaml(deck_meta_path)
        deck_dir = deck_meta_path.parent

        for cards_file in sorted(deck_dir.glob("cards*.yaml")):
            cards = load_yaml(cards_file) or []
            # Якщо в колоді кілька типів — _meta каже тільки про основний.
            # Для cards.<type>.yaml тип треба визначати інакше — поки що беремо з meta.
            yield deck_meta["deckName"], deck_meta["noteType"], cards_file, cards


# ─────────────────────────── план змін ───────────────────────────


class Plan:
    """Збирає всі дії, потім виконує одним пакетом."""

    def __init__(self):
        self.to_add = []        # [(deck_name, note_type, card_ref, cards_file)]
        self.to_update = []     # [(note_id, new_fields, new_tags, card_loc)]
        self.media_to_upload = [] # [filename]
        self.errors = []        # ["text"]
        self.warnings = []      # ["text"]
        self.orphan_note_ids = []  # noteIds в Anki, але не в YAML

    def has_errors(self):
        return bool(self.errors)

    def has_changes(self):
        return bool(self.to_add or self.to_update or self.media_to_upload)

    def print_summary(self):
        print()
        print("─" * 60)
        print("ПЛАН:")
        print(f"  додати нотаток:     {len(self.to_add)}")
        print(f"  оновити нотаток:    {len(self.to_update)}")
        print(f"  залити медіа:       {len(self.media_to_upload)}")
        if self.orphan_note_ids:
            print(f"  осиротілих в Anki:  {len(self.orphan_note_ids)} (не чіпаємо без --prune)")
        print("─" * 60)

        if self.warnings:
            print(f"\n⚠ Warnings ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"  {w}")

        if self.errors:
            print(f"\n✗ Errors ({len(self.errors)}):")
            for e in self.errors:
                print(f"  {e}")


# ─────────────────────────── порівняння ───────────────────────────


def normalize_fields_from_anki(note):
    """notesInfo повертає {name: {value, order}}, нам треба {name: value}."""
    return {name: data["value"] for name, data in note["fields"].items()}


def fields_differ(yaml_fields, anki_fields):
    """True якщо є хоч одна різниця."""
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


# ─────────────────────────── побудова плану ───────────────────────────


def build_plan(models, check_media_hashes):
    plan = Plan()

    # 1. Зібрати всі id з YAML — для пошуку осиротілих
    yaml_note_ids = set()

    # 2. Підвантажити стан Anki: усі noteIds з усіх наших колод
    deck_note_ids = {}  # deck_name -> set of noteIds in Anki
    seen_decks = set()
    for deck_name, _, _, _ in load_decks():
        seen_decks.add(deck_name)

    print("✓ Збираю стан Anki...")
    anki_note_ids_all = set()
    for deck_name in seen_decks:
        ids = anki("findNotes", query=f'deck:"{deck_name}"')
        deck_note_ids[deck_name] = set(ids)
        anki_note_ids_all.update(ids)
    print(f"  в Anki по нашим колодам: {len(anki_note_ids_all)} нотаток")

    # 3. Підвантажити повну інфу про нотатки одним запитом
    anki_notes = {}
    if anki_note_ids_all:
        notes_info = anki("notesInfo", notes=list(anki_note_ids_all))
        for note in notes_info:
            anki_notes[note["noteId"]] = note

    # 4. Обхід YAML
    for deck_name, note_type, cards_file, cards in load_decks():
        if note_type not in models:
            plan.errors.append(
                f"{cards_file}: невідомий Note Type {note_type!r}"
            )
            continue

        for idx, card in enumerate(cards):
            card_loc = f"{cards_file}#{idx}"
            card_id = card.get("id")
            yaml_fields = card.get("fields", {})
            yaml_tags = card.get("tags", []) or []

            if card_id is None:
                # Нова картка
                plan.to_add.append({
                    "deck": deck_name,
                    "model": note_type,
                    "fields": yaml_fields,
                    "tags": yaml_tags,
                    "card_ref": card,           # для запису id назад
                    "cards_file": cards_file,
                    "loc": card_loc,
                })
                continue

            yaml_note_ids.add(card_id)

            if card_id not in anki_notes:
                # Аномалія: id є в YAML, але в Anki такої нотатки немає
                plan.errors.append(
                    f"{card_loc}: id={card_id} вказаний у YAML, але в Anki такої нотатки немає. "
                    f"Або відновіть нотатку в Anki, або приберіть id (буде створено заново, прогрес SRS втрачено)."
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

    # 5. Осиротілі в Anki
    orphans = anki_note_ids_all - yaml_note_ids
    plan.orphan_note_ids = sorted(orphans)

    # 6. Медіа
    # Збираємо, які файли реально треба для всіх карток
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

    print("✓ Звіряю медіа...")
    # Які з них уже в Anki
    if needed_media:
        # AnkiConnect getMediaFilesNames приймає pattern, але ми поіменно перевіряємо
        in_anki = set(anki("getMediaFilesNames", pattern="*"))
    else:
        in_anki = set()

    local_files = {p.name for p in MEDIA_DIR.iterdir() if p.is_file()} if MEDIA_DIR.exists() else set()

    for filename in sorted(needed_media):
        local_path = MEDIA_DIR / filename
        if not local_path.exists():
            plan.errors.append(f"медіа {filename!r} згадане в картках, але немає в media/")
            continue

        if filename not in in_anki:
            plan.media_to_upload.append(filename)
            continue

        if check_media_hashes:
            # Тягнемо з Anki, порівнюємо хеш
            anki_b64 = anki("retrieveMediaFile", filename=filename)
            if anki_b64:
                anki_md5 = hashlib.md5(base64.b64decode(anki_b64)).hexdigest()
                local_md5 = file_md5(local_path)
                if anki_md5 != local_md5:
                    plan.media_to_upload.append(filename)
                    plan.warnings.append(
                        f"медіа {filename!r}: локальний хеш ≠ Anki — перезалью"
                    )

    return plan


# ─────────────────────────── виконання плану ───────────────────────────


def upload_media(plan):
    """Заливаємо медіа спочатку — щоб коли картки додаються, файли вже були в Anki."""
    if not plan.media_to_upload:
        return

    print(f"\n→ Заливаю {len(plan.media_to_upload)} медіа-файлів...")
    for i, filename in enumerate(plan.media_to_upload, 1):
        local_path = MEDIA_DIR / filename
        with open(local_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        anki("storeMediaFile", filename=filename, data=data)
        print(f"  [{i:04d}/{len(plan.media_to_upload)}] {filename}")


def add_notes(plan):
    """Додаємо нові нотатки, записуємо отримані noteId назад у YAML-структури."""
    if not plan.to_add:
        return

    print(f"\n→ Додаю {len(plan.to_add)} нових нотаток...")

    # Групуємо по cards_file — після додавання треба буде переписати файл
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
            # Записуємо id назад у структуру (це посилання — мутація відобразиться у файлі)
            # Важливо: id має бути першим ключем картки. Перебудовуємо dict.
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

    # Перезаписати змінені файли — треба перечитати, оновити, записати
    # Простіше: reload + dump кожного файлу через мапінг
    print(f"\n→ Дописую id у {len(files_changed)} файлів...")
    for cards_file in files_changed:
        # Знаходимо всі картки з цього файлу серед plan.to_add
        items_for_file = [item for item in plan.to_add if item["cards_file"] == cards_file]
        # Перечитуємо файл
        cards = load_yaml(cards_file) or []
        # Знаходимо нові id за позицією та оновлюємо
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

    print(f"\n→ Оновлюю {len(plan.to_update)} нотаток...")
    for i, item in enumerate(plan.to_update, 1):
        try:
            anki(
                "updateNoteFields",
                note={
                    "id": item["id"],
                    "fields": item["fields"],
                },
            )

            # Теги — окремо: вираховуємо diff
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
        print("\nОсиротілих нотаток немає")
        return

    print(f"\n⚠ Знайдено {len(plan.orphan_note_ids)} нотаток в Anki, що відсутні в YAML:")
    # Показуємо перші 10 з контекстом
    sample_ids = plan.orphan_note_ids[:10]
    sample_info = anki("notesInfo", notes=sample_ids)
    for note in sample_info:
        fields = normalize_fields_from_anki(note)
        # Беремо перше непорожнє поле для пред'явлення
        preview = next((v for v in fields.values() if v), "")
        if len(preview) > 60:
            preview = preview[:57] + "..."
        print(f"  id={note['noteId']}: {preview!r}")
    if len(plan.orphan_note_ids) > 10:
        print(f"  ... і ще {len(plan.orphan_note_ids) - 10}")

    confirm = input(f"\nВидалити всі {len(plan.orphan_note_ids)} нотаток з Anki? Прогрес повторень буде втрачено. [y/N] ")
    if confirm.lower() != "y":
        print("Скасовано")
        return

    anki("deleteNotes", notes=plan.orphan_note_ids)
    print(f"✓ Видалено {len(plan.orphan_note_ids)} нотаток")


# ─────────────────────────── main ───────────────────────────


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="показати план, нічого не змінювати")
    ap.add_argument("--check-media-hashes", action="store_true",
                    help="звіряти MD5 локальних медіа і тих, що в Anki (повільніше)")
    ap.add_argument("--prune", action="store_true",
                    help="видалити з Anki нотатки, відсутні в YAML (з підтвердженням)")
    args = ap.parse_args()

    try:
        anki("version")
    except requests.exceptions.ConnectionError:
        print("✗ Не можу підключитись до AnkiConnect. Чи запущений Anki?")
        sys.exit(1)

    models = load_models()
    if not models:
        print("✗ Не знайшов моделей у models/")
        sys.exit(1)

    plan = build_plan(models, check_media_hashes=args.check_media_hashes)
    plan.print_summary()

    if plan.has_errors():
        print("\n✗ Sync зупинено через errors. Виправ і запусти знов.")
        sys.exit(1)

    if not plan.has_changes() and not args.prune:
        print("\n✓ Все актуально, нічого робити.")
        return

    if args.dry_run:
        print("\n(dry-run, нічого не змінено)")
        return

    if plan.has_changes():
        confirm = input("\nЗастосувати зміни? [y/N] ")
        if confirm.lower() != "y":
            print("Скасовано")
            return

        upload_media(plan)
        add_notes(plan)
        update_notes(plan)
        print("\n✓ Sync завершено")

    if args.prune:
        prune_orphans(plan)


if __name__ == "__main__":
    main()