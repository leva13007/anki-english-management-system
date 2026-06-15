"""
bootstrap_media.py — завантажує медіа-файли з Anki у локальну папку media/.

Що робить:
  - читає mediaFields з кожного models/*/_meta.yaml
  - визначає, які моделі які поля містять медіа
  - проходить по decks/*/cards.yaml, збирає всі імена файлів
  - завантажує через AnkiConnect (ідемпотентно — пропускає вже завантажене)
  - попереджає про осиротілі файли в media/ (не видаляє)

Запуск:
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
        timeout=60,  # відео можуть бути великі
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
    """{noteType -> [field_name, ...]} з models/*/_meta.yaml."""
    result = {}
    for meta_path in MODELS_DIR.glob("*/_meta.yaml"):
        meta = load_yaml(meta_path)
        media_fields = meta.get("mediaFields", [])
        if media_fields:
            result[meta["noteType"]] = media_fields
    return result


def collect_required_files(model_media_map):
    """Обходить decks/*/cards*.yaml, збирає унікальні імена медіа."""
    required = set()
    references = 0

    for meta_path in DECKS_DIR.glob("*/_meta.yaml"):
        deck_dir = meta_path.parent
        meta = load_yaml(meta_path)

        # У колоді може бути 1 основний noteType або кілька (cards.<type>.yaml)
        for cards_file in deck_dir.glob("cards*.yaml"):
            cards = load_yaml(cards_file) or []
            for note in cards:
                fields = note.get("fields", {})
                # Шукаємо який тип нотатки відповідає цьому файлу — за полями
                # Простіше: для кожного знаного типу перевіряємо, чи всі його
                # медіа-поля присутні в нотатці
                for note_type, media_fields in model_media_map.items():
                    if all(f in fields for f in media_fields):
                        for field in media_fields:
                            value = (fields.get(field) or "").strip()
                            if value:
                                required.add(value)
                                references += 1
                        break  # знайшли тип — далі не шукаємо

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
        print("✓ AnkiConnect відповідає")
    except requests.exceptions.ConnectionError:
        print("✗ Не можу підключитись до AnkiConnect. Чи запущений Anki?")
        sys.exit(1)

    model_media_map = build_model_media_map()
    if not model_media_map:
        print("✗ У жодному models/*/_meta.yaml не знайдено mediaFields")
        sys.exit(1)

    print(f"✓ Медіа-поля по типах:")
    for note_type, fields in model_media_map.items():
        print(f"    {note_type}: {fields}")

    required, refs = collect_required_files(model_media_map)
    print(f"\n✓ У картках {refs} посилань на медіа, унікальних файлів: {len(required)}")

    MEDIA_DIR.mkdir(exist_ok=True)

    # Скільки вже маємо локально
    already_have = {p.name for p in MEDIA_DIR.iterdir() if p.is_file()}
    to_download = sorted(required - already_have)
    already_present = required & already_have

    print(f"  вже локально: {len(already_present)}")
    print(f"  треба завантажити: {len(to_download)}")

    if not to_download:
        print("\n✓ Усі потрібні файли вже на місці")
    else:
        confirm = input(f"\nЗавантажити {len(to_download)} файлів? [y/N] ")
        if confirm.lower() != "y":
            print("Скасовано")
            sys.exit(0)

        total_bytes = 0
        for i, filename in enumerate(to_download, 1):
            try:
                # retrieveMediaFile повертає base64-рядок або False, якщо немає
                b64 = anki("retrieveMediaFile", filename=filename)
                if not b64:
                    print(f"  [{i:04d}/{len(to_download)}] ✗ {filename}: немає в Anki")
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

        print(f"\n✓ Завантажено {human_size(total_bytes)}")

    # Осиротілі файли в media/
    orphans = already_have - required
    if orphans:
        print(f"\n⚠ Знайдено {len(orphans)} осиротілих файлів у ./{MEDIA_DIR}/")
        print("  (немає посилань з карток — не видаляю автоматично)")
        for name in sorted(orphans)[:10]:
            print(f"    {name}")
        if len(orphans) > 10:
            print(f"    ... і ще {len(orphans) - 10}")


if __name__ == "__main__":
    main()