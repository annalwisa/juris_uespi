"""Recuperação RAG com filtro de revogados e priorização por vigência/ano."""

import re

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from chatbot.citations import format_source_citation
import chatbot.config as config
from chatbot.config import RETRIEVAL_FETCH_K, RETRIEVAL_K
from chatbot.hybrid import bm25_search, merge_hybrid_results
from chatbot.metadata import STATUS_REVOGADO, status_rank, year_value
from chatbot.multi_query import generate_query_variations
from chatbot.rerank import rerank_documents

# Documentos cujos trechos exigem citação de artigo (regimento/estatuto/editais/resoluções)
_ARTICLE_TIPOS = {"regimento", "estatuto", "resolucao", "edital", "lei", "portaria"}

# Captura "Art. 46", "Artigo 46", "Art. 46-A", "Art. 3º", etc.
_ARTICLE_RE = re.compile(
    r"\bart(?:igo|\.)?\s*(\d+[º°]?(?:[-–]?[A-Z])?)",
    re.IGNORECASE,
)


def extract_articles(text: str, limit: int = 6) -> list[str]:
    """Extrai referências de artigo do trecho, preservando a ordem e sem duplicar."""
    seen: list[str] = []
    for match in _ARTICLE_RE.finditer(text or ""):
        num = match.group(1).replace("°", "º")
        label = f"Art. {num}"
        if label not in seen:
            seen.append(label)
        if len(seen) >= limit:
            break
    return seen


# Boost lexical leve (Opção D): quando a PERGUNTA cita um artigo/resolução/lei,
# priorizamos os trechos que contêm literalmente esse termo. Cobre os casos em
# que a busca puramente semântica erra tokens exatos ("Art. 46", "004/2021").
_REF_NUM_RE = re.compile(r"\b\d{1,4}/\d{2,4}\b")  # ex.: 004/2021, 20/2016
_REF_LAW_RE = re.compile(r"\b\d{1,3}\.\d{3}\b")  # ex.: 11.788


def _norm_num(value: str) -> str:
    return value.lstrip("0") or "0"


def build_lexical_matchers(question: str) -> list[re.Pattern]:
    """Regexes que detectam, no texto dos trechos, as referências citadas na pergunta."""
    matchers: list[re.Pattern] = []
    q = question or ""

    for m in _ARTICLE_RE.finditer(q):
        digits = re.match(r"\d+", m.group(1))
        if digits:
            n = _norm_num(digits.group())
            # 0*N e (?!\d) toleram zeros à esquerda e sufixos como "º"/"-A".
            matchers.append(
                re.compile(rf"\bart(?:igo|\.)?\s*0*{n}(?!\d)", re.IGNORECASE)
            )

    for m in _REF_NUM_RE.finditer(q):
        matchers.append(re.compile(re.escape(m.group()), re.IGNORECASE))

    for m in _REF_LAW_RE.finditer(q):
        matchers.append(re.compile(re.escape(m.group())))

    return matchers


def _doc_has_ref(text: str, matchers: list[re.Pattern]) -> bool:
    return any(p.search(text or "") for p in matchers)


# Exclui documentos revogados já na busca vetorial (Pinecone e Chroma suportam $ne).
# Mantém-se o filtro em Python como defesa caso o store ignore o filtro ou um
# chunk antigo não tenha o campo "status".
REVOGADO_FILTER = {"status": {"$ne": STATUS_REVOGADO}}


def _search(vector_store: VectorStore, question: str, *, use_filter: bool) -> list[Document]:
    search_kwargs: dict = {"k": RETRIEVAL_FETCH_K}
    if use_filter:
        search_kwargs["filter"] = REVOGADO_FILTER
    return vector_store.as_retriever(search_kwargs=search_kwargs).invoke(question)


def _dense_search(vector_store: VectorStore, question: str) -> list[Document]:
    try:
        docs = _search(vector_store, question, use_filter=True)
    except Exception:
        docs = _search(vector_store, question, use_filter=False)
    if not docs:
        docs = _search(vector_store, question, use_filter=False)
    return [d for d in docs if d.metadata.get("status") != STATUS_REVOGADO]


def _dedupe_docs(docs: list[Document]) -> list[Document]:
    seen: set[str] = set()
    out: list[Document] = []
    for d in docs:
        key = f"{d.metadata.get('source','')}|{d.metadata.get('page','')}|{d.page_content[:120]}"
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    return out


def _apply_vigency_sort(docs: list[Document], question: str) -> list[Document]:
    """Ordenação final: preserva score do reranker e aplica vigência/lexical como desempate."""
    matchers = build_lexical_matchers(question)
    has_rerank = any(d.metadata.get("_rerank_score") is not None for d in docs)

    def sort_key(d: Document) -> tuple:
        rerank = float(d.metadata.get("_rerank_score", 0.0))
        lexical = 0 if matchers and _doc_has_ref(d.page_content, matchers) else 1
        if has_rerank:
            return (-rerank, lexical, status_rank(d.metadata.get("status")), -year_value(d.metadata))
        if matchers:
            return (lexical, status_rank(d.metadata.get("status")), -year_value(d.metadata))
        return (status_rank(d.metadata.get("status")), -year_value(d.metadata))

    docs.sort(key=sort_key)
    return docs


def retrieve_context(vector_store: VectorStore, question: str) -> list[Document]:
    """Recupera trechos com pipeline configurável:

    1. Multi-query (opcional) — variações da pergunta.
    2. Busca densa (vetorial) + BM25 (híbrido, opcional).
    3. Reranking com cross-encoder (opcional).
    4. Ordenação final por vigência/ano e boost lexical de artigo/resolução.
    """
    queries = (
        generate_query_variations(question)
        if config.MULTI_QUERY_ENABLED
        else [question]
    )

    dense_pool: list[Document] = []
    for q in queries:
        dense_pool.extend(_dense_search(vector_store, q))
    dense_pool = _dedupe_docs(dense_pool)[:RETRIEVAL_FETCH_K]

    if config.HYBRID_ENABLED:
        sparse_pool = bm25_search(question, RETRIEVAL_FETCH_K)
        docs = merge_hybrid_results(
            dense_pool, sparse_pool, top_k=RETRIEVAL_FETCH_K
        )
    else:
        docs = dense_pool

    if config.RERANKER_ENABLED and docs:
        docs = rerank_documents(question, docs, RETRIEVAL_K)
    else:
        docs = docs[:RETRIEVAL_K]

    return _apply_vigency_sort(docs, question)


def format_context(docs: list[Document]) -> str:
    if not docs:
        return "(Nenhum trecho relevante encontrado nos documentos indexados.)"

    parts = []
    for i, doc in enumerate(docs, start=1):
        meta = doc.metadata
        source = format_source_citation(meta.get("source", "documento"))
        year = meta.get("year")
        status = meta.get("status", "vigente")
        page = meta.get("page")
        subst = meta.get("substituido_por")
        nota = meta.get("nota")
        tipo = meta.get("tipo")

        header = f"[{i}] Fonte: {source}"
        if tipo:
            header += f" | Tipo: {tipo}"
        if year:
            header += f" | Ano: {year}"
        header += f" | Status: {status}"
        if page:
            header += f" | Página: {page}"
        if subst:
            header += f" | Ver também (mais recente): {subst}"
        if nota:
            header += f" | Nota: {nota}"

        if tipo in _ARTICLE_TIPOS:
            articles = extract_articles(doc.page_content)
            if articles:
                header += (
                    f" | Artigos detectados: {', '.join(articles)}"
                    " (CITE o(s) artigo(s) ao usar este trecho)"
                )
        if status == "desatualizado":
            header += (
                " | ATENÇÃO: documento marcado como possivelmente desatualizado — "
                "prefira fontes mais recentes no contexto se houver conflito."
            )

        parts.append(f"{header}\n{doc.page_content}")

    return "\n\n---\n\n".join(parts)
