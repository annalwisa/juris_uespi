"""Bloqueio de linguagem ofensiva, discriminatória ou de baixo calão."""

from __future__ import annotations

import os
import re
import unicodedata
from functools import lru_cache

import yaml

from chatbot.config import ROOT

TERMS_PATH = ROOT / "data" / "termos_proibidos.yaml"

MODERATION_ENABLED = os.getenv("MODERATION_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
    "on",
)

MODERATION_MESSAGE = """Não posso processar mensagens com termos ofensivos.

Por favor, reformule sua pergunta sobre a UESPI."""

_LEET = str.maketrans(
    {
        "@": "a",
        "4": "a",
        "3": "e",
        "1": "i",
        "!": "i",
        "0": "o",
        "$": "s",
        "5": "s",
        "7": "t",
    }
)


def _normalize(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    lowered = stripped.lower().translate(_LEET)
    lowered = re.sub(r"[*_\-]+", "", lowered)
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


@lru_cache(maxsize=1)
def _moderation_rules() -> tuple[tuple[re.Pattern[str], ...], frozenset[str]]:
    if not TERMS_PATH.exists():
        return (), frozenset()

    with TERMS_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    raw_terms: list[str] = []
    for key in ("palavras", "frases", "termos"):
        block = data.get(key)
        if isinstance(block, list):
            raw_terms.extend(str(t) for t in block if t)

    patterns: list[re.Pattern[str]] = []
    compact_terms: set[str] = set()
    seen: set[str] = set()
    for term in raw_terms:
        n = _normalize(term)
        if not n or n in seen:
            continue
        seen.add(n)
        if " " in n:
            patterns.append(re.compile(re.escape(n)))
        else:
            patterns.append(re.compile(rf"\b{re.escape(n)}\b"))
            if len(n) >= 5:
                compact_terms.add(n)

    return tuple(patterns), frozenset(compact_terms)


def contains_prohibited_language(text: str) -> bool:
    if not text or not text.strip():
        return False

    normalized = _normalize(text)
    if not normalized:
        return False

    patterns, compact_terms = _moderation_rules()
    for pattern in patterns:
        if pattern.search(normalized):
            return True

    compact = normalized.replace(" ", "")
    if compact:
        for term in compact_terms:
            if term in compact:
                return True

    return False


def is_message_allowed(text: str) -> bool:
    if not MODERATION_ENABLED:
        return True
    return not contains_prohibited_language(text)


def moderation_response() -> str:
    return MODERATION_MESSAGE
