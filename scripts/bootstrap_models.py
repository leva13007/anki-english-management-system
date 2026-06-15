"""
bootstrap_models.py — експорт Note Types з Anki у плоскі файли.

Що робить:
  - для кожного Note Type створює models/<safe-name>/{_meta.yaml, style.css, templates/}
  - templates/<card-name>/{front.html, back.html}
  - НЕ чіпає дані нотаток і медіа

Запуск:
  source .venv/bin/activate
  python scripts/bootstrap_models.py
"""

import re
import sys
from pathlib import Path

import requests
import yaml

ANKI_URL = "http://localhost:8765"
OUTPUT_DIR = Path("models")


def anki(action, **params):
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
    """'Basic (type in the answer) + audio' -> 'basic-type-in-the-answer-audio'."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9а-яіїєґ]+", "-", name, flags=re.IGNORECASE)
    return name.strip("-")


def yaml_dump(data, path):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            data, f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=100,
            indent=2,
        )


def write_text(path, content):
    """Записує текст з фінальним \\n, щоб git не лаявся."""
    if not content.endswith("\n"):
        content += "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    try:
        anki("version")
        print("✓ AnkiConnect відповідає")
    except requests.exceptions.ConnectionError:
        print("✗ Не можу підключитись до AnkiConnect. Чи запущений Anki?")
        sys.exit(1)

    # Які Note Type'и реально використовуються в наших колодах
    # (фільтруємо невикористовувані, щоб не тягнути сміття)
    deck_names = [d for d in anki("deckNames") if d != "Default"]
    used_models = set()
    for deck in deck_names:
        note_ids = anki("findNotes", query=f'deck:"{deck}"')
        if not note_ids:
            continue
        # Беремо тільки першу нотатку — нам треба тільки modelName
        info = anki("notesInfo", notes=note_ids[:1])
        used_models.add(info[0]["modelName"])

    # Можуть бути нотатки різних типів у одній колоді — добираємо
    # перевіряючи всі типи з усіх нотаток (швидкий повторний прохід)
    all_models = set(anki("modelNames"))
    print(f"✓ Усього Note Type'ів в Anki: {len(all_models)}")
    print(f"✓ Використовуються в колодах: {len(used_models)} — {sorted(used_models)}")

    unused = all_models - used_models
    if unused:
        print(f"  (пропускаю невикористовувані: {sorted(unused)})")

    OUTPUT_DIR.mkdir(exist_ok=True)

    for model_name in sorted(used_models):
        safe_name = safe_dirname(model_name)
        model_dir = OUTPUT_DIR / safe_name
        model_dir.mkdir(parents=True, exist_ok=True)

        # 1. Поля моделі
        fields = anki("modelFieldNames", modelName=model_name)

        # 2. Шаблони — dict {templateName: {"Front": "...", "Back": "..."}}
        templates = anki("modelTemplates", modelName=model_name)

        # 3. CSS — dict {"css": "..."}
        styling = anki("modelStyling", modelName=model_name)
        css = styling["css"]

        # _meta.yaml — merge з існуючим, щоб не загубити користувацькі поля
        # (mediaFields, sortField додаються вручну і не мають перезаписуватись)
        AUTO_FIELDS = {"noteType", "fields", "templates"}
        meta_path = model_dir / "_meta.yaml"

        # Авто-частина — те, що завжди береться з Anki
        auto_meta = {
            "noteType": model_name,
            "fields": fields,
            "templates": list(templates.keys()),
        }

        # Якщо файл уже є — підтягуємо все, чого нема в AUTO_FIELDS
        if meta_path.exists():
            with open(meta_path, encoding="utf-8") as f:
                existing = yaml.safe_load(f) or {}
            user_meta = {k: v for k, v in existing.items() if k not in AUTO_FIELDS}
        else:
            user_meta = {}

        # Збираємо у фінальному порядку: спочатку авто, потім користувацьке
        meta = {**auto_meta, **user_meta}
        yaml_dump(meta, meta_path)

        # style.css
        write_text(model_dir / "style.css", css)

        # Шаблони — кожен у свою підпапку
        templates_dir = model_dir / "templates"
        templates_dir.mkdir(exist_ok=True)

        for template_name, sides in templates.items():
            tpl_dir = templates_dir / safe_dirname(template_name)
            tpl_dir.mkdir(exist_ok=True)
            write_text(tpl_dir / "front.html", sides["Front"])
            write_text(tpl_dir / "back.html", sides["Back"])

        print(
            f"  ✓ {model_name}"
            f"\n    fields: {fields}"
            f"\n    templates: {list(templates.keys())}"
            f"\n    css: {len(css)} символів"
        )

    print(f"\n✓ Готово. Експортовано {len(used_models)} Note Type'ів у ./{OUTPUT_DIR}/")


if __name__ == "__main__":
    main()