"""
bootstrap_models.py — exports Note Types from Anki to flat files.

What it does:
  - for each Note Type creates models/<safe-name>/{_meta.yaml, style.css, templates/}
  - templates/<card-name>/{front.html, back.html}
  - does NOT touch note data or media

Usage:
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
    """Writes text with a trailing newline (avoids git 'no newline at EOF' warnings)."""
    if not content.endswith("\n"):
        content += "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    try:
        anki("version")
        print("✓ AnkiConnect is up")
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to AnkiConnect. Is Anki running?")
        sys.exit(1)

    # Find which Note Types are actually used in our decks
    deck_names = [d for d in anki("deckNames") if d != "Default"]
    used_models = set()
    for deck in deck_names:
        note_ids = anki("findNotes", query=f'deck:"{deck}"')
        if not note_ids:
            continue
        # Only need one note to get modelName
        info = anki("notesInfo", notes=note_ids[:1])
        used_models.add(info[0]["modelName"])

    # Decks may mix Note Types — the set above may be incomplete
    all_models = set(anki("modelNames"))
    print(f"✓ Total Note Types in Anki: {len(all_models)}")
    print(f"✓ Used in decks: {len(used_models)} — {sorted(used_models)}")

    unused = all_models - used_models
    if unused:
        print(f"  (skipping unused: {sorted(unused)})")

    OUTPUT_DIR.mkdir(exist_ok=True)

    for model_name in sorted(used_models):
        safe_name = safe_dirname(model_name)
        model_dir = OUTPUT_DIR / safe_name
        model_dir.mkdir(parents=True, exist_ok=True)

        # 1. Model fields
        fields = anki("modelFieldNames", modelName=model_name)

        # 2. Templates — dict {templateName: {"Front": "...", "Back": "..."}}
        templates = anki("modelTemplates", modelName=model_name)

        # 3. CSS — dict {"css": "..."}
        styling = anki("modelStyling", modelName=model_name)
        css = styling["css"]

        # _meta.yaml — merge with existing to preserve user-defined fields
        # (mediaFields, sortField are added manually and must not be overwritten)
        AUTO_FIELDS = {"noteType", "fields", "templates"}
        meta_path = model_dir / "_meta.yaml"

        # Auto section — always sourced from Anki
        auto_meta = {
            "noteType": model_name,
            "fields": fields,
            "templates": list(templates.keys()),
        }

        # If file already exists — keep everything outside AUTO_FIELDS
        if meta_path.exists():
            with open(meta_path, encoding="utf-8") as f:
                existing = yaml.safe_load(f) or {}
            user_meta = {k: v for k, v in existing.items() if k not in AUTO_FIELDS}
        else:
            user_meta = {}

        # Final order: auto fields first, then user fields
        meta = {**auto_meta, **user_meta}
        yaml_dump(meta, meta_path)

        # style.css
        write_text(model_dir / "style.css", css)

        # Templates — each in its own subdirectory
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
            f"\n    css: {len(css)} chars"
        )

    print(f"\n✓ Done. Exported {len(used_models)} Note Types to ./{OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
