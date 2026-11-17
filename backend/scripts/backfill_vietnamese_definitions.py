"""Translate existing English vocabulary definitions with Azure AI Translator.

Run only on the backend host after AZURE_TRANSLATOR_KEY is configured:
    .venv/bin/python -m scripts.backfill_vietnamese_definitions
"""
from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.vocabulary import Vocabulary
from app.services.azure_translator import translate_english_texts_to_vietnamese


def main() -> None:
    db = SessionLocal()
    try:
        rows = db.scalars(select(Vocabulary).where(Vocabulary.definition.is_not(None))).all()
        updated = 0
        for start in range(0, len(rows), 100):
            batch = rows[start:start + 100]
            translations = translate_english_texts_to_vietnamese([row.definition for row in batch])
            for row, translated in zip(batch, translations):
                if translated:
                    row.vietnamese_definition = translated
                    updated += 1
            db.commit()
            print(f"Translated {min(start + len(batch), len(rows))}/{len(rows)} definitions")
        print(f"Completed: {updated}/{len(rows)} definitions translated.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
