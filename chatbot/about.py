"""Resposta sobre o próprio assistente Juris UESPI (não confundir com Empresa Júnior)."""

from __future__ import annotations

import re
import unicodedata

ABOUT_PATTERNS = (
    r"\bjuris[\s\-_]?uespi\b",
    r"\bo\s+que\s+[eé]\s+(o\s+)?juris\b",
    r"\bquem\s+[eé]\s+(o\s+)?juris\b",
    r"\bsobre\s+o\s+juris\b",
    r"\beste\s+(chat|chatbot|assistente)\b",
    r"\beste\s+sistema\b",
    r"\bo\s+que\s+(voce|você)\s+(faz|e[eé])\b",
    r"\bpara\s+que\s+serve\s+(este|esse)\s+(assistente|chatbot|sistema)\b",
    r"\bcomo\s+funciona\s+(este|esse)\s+(assistente|chatbot)\b",
)

IDENTITY_PATTERNS = (
    r"\bqual\s+(e\s+)?(o\s+)?(seu|teu)\s+nome\b",
    r"\bcomo\s+(voce|vc)\s+se\s+chama\b",
    r"\bqual\s+(e\s+)?o\s+nome\s+(do|de)\s+(assistente|chatbot|bot)\b",
    r"\bquem\s+e\s+(vc|voce)\b",
    r"\bo\s+que\s+(vc|voce)\s+faz\b",
)

# Compatibilidade com imports antigos
NAME_PATTERNS = IDENTITY_PATTERNS

NAME_INTRO_RESPONSE = """Olá! Eu sou o **Juris UESPI**, assistente inteligente da **Universidade Estadual do Piauí (UESPI)**.

Estou aqui para ajudar a comunidade acadêmica com dúvidas sobre normas, cursos, matrícula, faltas, bolsas e outros temas da universidade. Como posso ajudar?"""

ABOUT_RESPONSE = """O **Juris UESPI** é um **assistente inteligente** criado para ajudar a **comunidade acadêmica** da Universidade Estadual do Piauí (UESPI).

Ele foi desenvolvido para sanar dúvidas sobre a universidade, com base em:

- **Documentos oficiais** indexados (regimento, resoluções, leis e normas)
- **SIGAA** (cursos de graduação, coordenadores, sede e modalidade)
- **Busca na web**, quando necessário (por exemplo, gestão atual e reitoria)

Você pode perguntar sobre normas acadêmicas, cursos, campi, coordenação, matrícula, faltas, estágio e outros temas institucionais da UESPI."""


def _normalize(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def _identity_blocklist(n: str) -> bool:
    if re.search(r"\bnome\s+(do|da|de)\s+", n):
        return True
    return any(
        x in n
        for x in (
            "reitor",
            "coordenador",
            "professor",
            "disciplina",
            "edital",
            "regimento",
            "resolucao",
            "resolução",
        )
    )


def is_assistant_identity_question(question: str) -> bool:
    """Nome ou identidade do assistente (ex.: «qual seu nome?», «quem é vc?»)."""
    n = _normalize(question)
    if _identity_blocklist(n):
        return False
    return any(re.search(p, n) for p in IDENTITY_PATTERNS)


def is_assistant_name_question(question: str) -> bool:
    return is_assistant_identity_question(question)


def is_about_assistant_question(question: str) -> bool:
    n = _normalize(question)
    if is_assistant_identity_question(question):
        return False
    return any(re.search(p, n) for p in ABOUT_PATTERNS)


def assistant_name_response() -> str:
    return NAME_INTRO_RESPONSE


def about_assistant_response() -> str:
    return ABOUT_RESPONSE
