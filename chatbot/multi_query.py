"""Reescrita de consulta (multi-query retrieval).

Gera variações da pergunta do usuário para ampliar a cobertura semântica da
busca — útil quando o aluno usa linguagem coloquial e a norma usa juridiquês.
"""

from __future__ import annotations

import json
import re

from langchain_openai import ChatOpenAI

import chatbot.config as config


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
    raw = llm.invoke(prompt).content
    if isinstance(raw, list):
        raw = "".join(part if isinstance(part, str) else "" for part in raw)
    raw = str(raw).strip()

    queries: list[str] = []
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            queries = [q.strip() for q in data.get("queries", []) if isinstance(q, str)]
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                queries = [
                    q.strip() for q in data.get("queries", []) if isinstance(q, str)
                ]
            except json.JSONDecodeError:
                pass

    seen = {question.strip().lower()}
    out = [question.strip()]
    for q in queries:
        key = q.lower()
        if key not in seen and q.strip():
            seen.add(key)
            out.append(q.strip())
    return out
