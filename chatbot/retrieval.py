"""Recuperação RAG com filtro de revogados e priorização por vigência/ano."""

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from chatbot.citations import format_source_citation
from chatbot.config import RETRIEVAL_FETCH_K, RETRIEVAL_K
from chatbot.metadata import STATUS_REVOGADO, status_rank, year_value


def retrieve_context(vector_store: VectorStore, question: str) -> list[Document]:
    retriever = vector_store.as_retriever(search_kwargs={"k": RETRIEVAL_FETCH_K})
    docs = retriever.invoke(question)

    docs = [d for d in docs if d.metadata.get("status") != STATUS_REVOGADO]

    docs.sort(
        key=lambda d: (
            status_rank(d.metadata.get("status")),
            -year_value(d.metadata),
        )
    )

    return docs[:RETRIEVAL_K]


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

        header = f"[{i}] Fonte: {source}"
        if year:
            header += f" | Ano: {year}"
        header += f" | Status: {status}"
        if page:
            header += f" | Página: {page}"
        if subst:
            header += f" | Ver também (mais recente): {subst}"
        if nota:
            header += f" | Nota: {nota}"
        if status == "desatualizado":
            header += (
                " | ATENÇÃO: documento marcado como possivelmente desatualizado — "
                "prefira fontes mais recentes no contexto se houver conflito."
            )

        parts.append(f"{header}\n{doc.page_content}")

    return "\n\n---\n\n".join(parts)
