"""Small server-side client for Azure AI Translator."""
import logging
from typing import Iterable

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


def translate_english_to_vietnamese(text: str | None) -> str | None:
    if not text:
        return text
    translated = translate_english_texts_to_vietnamese([text])
    return translated[0] if translated else None


def translate_english_texts_to_vietnamese(texts: Iterable[str]) -> list[str | None]:
    """Translate up to 100 definitions, returning None for an unavailable provider.

    A translation failure must not block dictionary lookup or corrupt an existing
    English definition.
    """
    items = list(texts)
    if not items:
        return []
    if len(items) > 100:
        raise ValueError("Azure Translator accepts at most 100 texts per request")
    if settings.azure_translator_key is None:
        logger.info("Azure Translator is not configured; skipping translation")
        return [None] * len(items)
    try:
        response = requests.post(
            settings.azure_translator_endpoint.rstrip("/") + "/translate",
            params={"api-version": "3.0", "from": "en", "to": "vi"},
            headers={
                "Ocp-Apim-Subscription-Key": settings.azure_translator_key.get_secret_value(),
                "Content-Type": "application/json",
            },
            json=[{"Text": text} for text in items],
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or len(payload) != len(items):
            raise ValueError("Unexpected Azure Translator response")
        return [
            entry.get("translations", [{}])[0].get("text") or None
            for entry in payload
        ]
    except (requests.RequestException, ValueError, IndexError, TypeError):
        logger.warning("Azure Translator request failed", exc_info=True)
        return [None] * len(items)
