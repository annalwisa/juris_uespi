"""Reescrita de consulta (multi-query retrieval).

Gera variações da pergunta do usuário para ampliar a cobertura semântica da
busca — útil quando o aluno usa linguagem coloquial e a norma usa juridiquês.
"""

from __future__ import annotations

import json
import re

from langchain_openai import ChatOpenAI

import chatbot.config as config


def _coerce_text(raw) -> str:
    if isinstance(raw, list):
        raw = "".join(part if isinstance(part, str) else "" for part in raw)
    return str(raw).strip()


def _queries_from_json(text: str) -> list[str] | None:
    """Lista de queries de um JSON; ``None`` quando o texto não é JSON válido."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict):
        return [q.strip() for q in data.get("queries", []) if isinstance(q, str)]
    return []


def _parse_queries(raw: str) -> list[str]:
    queries = _queries_from_json(raw)
    if queries is not None:
        return queries
    # Fallback: extrai o primeiro objeto JSON embutido em texto livre.
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return []
    return _queries_from_json(match.group()) or []


def _dedupe_queries(question: str, queries: list[str]) -> list[str]:
    seen = {question.strip().lower()}
    out = [question.strip()]
    for q in queries:
        key = q.lower()
        if key not in seen and q.strip():
            seen.add(key)
            out.append(q.strip())
    return out


def generate_query_variations(question: str, n: int | None = None) -> list[str]:
    """Devolve a pergunta original + até ``n`` reformulações."""
    n = n if n is not None else config.MULTI_QUERY_COUNT
    if not config.MULTI_QUERY_ENABLED or not config.OPENAI_API_KEY or n <= 0:
        return [question]

    llm = ChatOpenAI(
        model=config.CHAT_MODEL, api_key=config.OPENAI_API_KEY, temperature=0.3
    )
    prompt = (
        f"Reescreva a PERGUNTA abaixo em {n} formas diferentes, mantendo o mesmo "
        "significado, mas usando vocabulário alternativo (incluindo termos formais "
        "de normas acadêmicas quando fizer sentido). "
        "Responda APENAS em JSON: {{\"queries\": [\"...\"]}}.\n\n"
        f"PERGUNTA: {question}"
    )
    raw = _coerce_text(llm.invoke(prompt).content)
    queries = _parse_queries(raw)
    return _dedupe_queries(question, queries)
