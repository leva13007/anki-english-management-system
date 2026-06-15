"""
bootstrap_decks.py — одноразовий експорт даних карток з Anki у плоскі YAML-файли.

Що робить:
  - запитує AnkiConnect (HTTP localhost:8765)
  - для кожної колоди створює decks/<safe-name>/{_meta.yaml, cards.yaml}
  - НЕ чіпає шаблони, CSS, медіа — тільки дані нотаток

Запуск:
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

# Системні колоди, які пропускаємо
SKIP_DECKS = {"Default"}


def anki(action, **params):
    """Один виклик AnkiConnect. Кидає виняток при помилці."""
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
    """'How to Win Friends' -> 'how-to-win-friends'. Для імен папок."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9а-яіїєґ]+", "-", name, flags=re.IGNORECASE)
    return name.strip("-")


def yaml_dump(data, path):
    """YAML з адекватними налаштуваннями для читабельності."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            allow_unicode=True,      # кирилиця як є, не \uXXXX
            sort_keys=False,         # порядок ключів зберігаємо
            default_flow_style=False,
            width=100,
            indent=2,
        )


def main():
    # 1. Перевірка зв'язку
    try:
        version = anki("version")
        print(f"✓ AnkiConnect v{version} відповідає")
    except requests.exceptions.ConnectionError:
        print("✗ Не можу підключитись до AnkiConnect (localhost:8765).")
        print("  Чи запущений Anki? Чи встановлений аддон?")
        sys.exit(1)

    # 2. Список колод
    deck_names = anki("deckNames")
    deck_names = [d for d in deck_names if d not in SKIP_DECKS]
    print(f"✓ Знайдено {len(deck_names)} колод: {deck_names}")

    OUTPUT_DIR.mkdir(exist_ok=True)

    total_notes = 0

    # 3. Обхід колод
    for deck_name in deck_names:
        # Anki query syntax: лапки навколо назви, бо може містити пробіли
        note_ids = anki("findNotes", query=f'deck:"{deck_name}"')

        if not note_ids:
            print(f"  ⊘ {deck_name}: порожня, пропускаю")
            continue

        # Витягуємо повні дані пачкою (один запит на колоду)
        notes_info = anki("notesInfo", notes=note_ids)

        # Групуємо по Note Type — на випадок, якщо в одній колоді кілька типів
        by_model = defaultdict(list)
        for note in notes_info:
            by_model[note["modelName"]].append(note)

        # Якщо в колоді кілька Note Type'ів — попереджаємо
        if len(by_model) > 1:
            print(
                f"  ⚠ {deck_name}: знайдено {len(by_model)} різних Note Type'ів — "
                f"{list(by_model.keys())}. Створю окремі файли cards.<type>.yaml"
            )

        deck_dir = OUTPUT_DIR / safe_dirname(deck_name)
        deck_dir.mkdir(parents=True, exist_ok=True)

        # _meta.yaml: інформація про колоду
        primary_model = max(by_model.keys(), key=lambda m: len(by_model[m]))
        meta = {
            "deckName": deck_name,
            "noteType": primary_model,
        }
        if len(by_model) > 1:
            meta["additionalNoteTypes"] = [m for m in by_model if m != primary_model]
        yaml_dump(meta, deck_dir / "_meta.yaml")

        # cards.yaml: самі картки
        for model_name, notes in by_model.items():
            cards = []
            for note in notes:
                cards.append({
                    "id": note["noteId"],
                    # fields в AnkiConnect — це {fieldName: {value, order}}
                    # нам треба тільки value, в порядку order
                    "fields": {
                        name: data["value"]
                        for name, data in sorted(
                            note["fields"].items(),
                            key=lambda kv: kv[1]["order"],
                        )
                    },
                    "tags": note["tags"],
                })

            # Якщо тип один — cards.yaml, якщо кілька — cards.<safe-type>.yaml
            if len(by_model) == 1:
                filename = "cards.yaml"
            else:
                filename = f"cards.{safe_dirname(model_name)}.yaml"

            yaml_dump(cards, deck_dir / filename)
            print(f"  ✓ {deck_name} / {model_name}: {len(cards)} нотаток → {filename}")
            total_notes += len(cards)

    print(f"\n✓ Готово. Усього експортовано {total_notes} нотаток у ./{OUTPUT_DIR}/")


if __name__ == "__main__":
    main()