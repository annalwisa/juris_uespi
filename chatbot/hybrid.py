"""Busca híbrida: BM25 (esparso) + vetorial (denso).

O índice BM25 é construído a partir dos mesmos trechos indexados no ingest
e persistido em ``vector_db/bm25_index.pkl``. Complementa a busca semântica
em consultas com termos exatos (Art. 46, 004/2021, Lei 11.788).
"""

from __future__ import annotations

import pickle  # nosec B403 - índice BM25 gerado e lido localmente pelo ingest (dado confiável)
import re
from functools import lru_cache

from langchain_core.documents import Document

import chatbot.config as config
from chatbot.config import VECTOR_DB_DIR
from chatbot.metadata import STATUS_REVOGADO

BM25_INDEX_PATH = VECTOR_DB_DIR / "bm25_index.pkl"

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def save_bm25_index(chunks: list[Document]) -> None:
    """Persiste o índice BM25 após a indexação vetorial."""
    if not chunks:
        return
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        return

    corpus = [_tokenize(c.page_content) for c in chunks]
    bm25 = BM25Okapi(corpus)
    payload = {
        "bm25": bm25,
        "documents": chunks,
    }
    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
    with BM25_INDEX_PATH.open("wb") as f:
        pickle.dump(payload, f)
    clear_bm25_cache()


@lru_cache(maxsize=1)
def get_bm25_index() -> tuple | None:
    """Índice BM25 em memória (invalidar após reindexar com ``clear_bm25_cache``)."""
    if not config.HYBRID_ENABLED or not BM25_INDEX_PATH.exists():
        return None
    try:
        with BM25_INDEX_PATH.open("rb") as f:
            payload = pickle.load(f)  # nosec B301 - arquivo local gerado pelo próprio ingest
        return payload.get("bm25"), payload.get("documents", [])
    except Exception:
        return None


def clear_bm25_cache() -> None:
    get_bm25_index.cache_clear()


def bm25_search(question: str, k: int) -> list[Document]:
    """Retorna até ``k`` trechos pelo BM25 (exclui revogados)."""
    loaded = get_bm25_index()
    if not loaded:
        return []
    bm25, documents = loaded
    if not bm25 or not documents:
        return []

    tokens = _tokenize(question)
    if not tokens:
        return []

    scores = bm25.get_scores(tokens)
    ranked = sorted(
        enumerate(scores),
        key=lambda x: float(x[1]),
        reverse=True,
    )
    out: list[Document] = []
    for idx, _score in ranked:
        doc = documents[idx]
        if doc.metadata.get("status") == STATUS_REVOGADO:
            continue
        out.append(doc)
        if len(out) >= k:
            break
    return out


def _doc_key(doc: Document) -> str:
    meta = doc.metadata
    return f"{meta.get('source','')}|{meta.get('page','')}|{hash(doc.page_content[:200])}"


def merge_hybrid_results(
    dense_docs: list[Document],
    sparse_docs: list[Document],
    *,
    top_k: int,
) -> list[Document]:
    """Combina listas denso + esparso com Reciprocal Rank Fusion (RRF)."""
    if not sparse_docs:
        return dense_docs[:top_k]

    k_rrf = 60  # constante padrão RRF
    scores: dict[str, float] = {}
    by_key: dict[str, Document] = {}

    for rank, doc in enumerate(dense_docs):
        key = _doc_key(doc)
        by_key[key] = doc
        scores[key] = scores.get(key, 0.0) + config.HYBRID_ALPHA / (k_rrf + rank + 1)

    sparse_weight = 1.0 - config.HYBRID_ALPHA
    for rank, doc in enumerate(sparse_docs):
        key = _doc_key(doc)
        by_key[key] = doc
        scores[key] = scores.get(key, 0.0) + sparse_weight / (k_rrf + rank + 1)

    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [by_key[key] for key, _ in ordered[:top_k]]
