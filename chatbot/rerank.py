"""Reranking com cross-encoder (segunda etapa após a busca vetorial).

Após recuperar ``fetch_k`` candidatos, o reranker reordena por relevância
par pergunta–trecho antes de cortar para ``k``. Modelo padrão leve e em
português/inglês: ``BAAI/bge-reranker-base``.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.documents import Document

import chatbot.config as config


@lru_cache(maxsize=1)
def _cross_encoder():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(config.RERANKER_MODEL)


def rerank_documents(question: str, docs: list[Document], top_k: int) -> list[Document]:
    """Reordena ``docs`` por relevância e devolve os ``top_k`` primeiros."""
    if not config.RERANKER_ENABLED or not docs:
        return docs[:top_k]
    if len(docs) <= top_k:
        return docs

    pairs = [(question, d.page_content) for d in docs]
    scores = _cross_encoder().predict(pairs)
    ranked = sorted(zip(docs, scores), key=lambda x: float(x[1]), reverse=True)
    out: list[Document] = []
    for doc, score in ranked[:top_k]:
        doc.metadata["_rerank_score"] = float(score)
        out.append(doc)
    return out
