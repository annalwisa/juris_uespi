"""Fábrica do banco vetorial: Pinecone (nuvem) ou Chroma (local)."""

from __future__ import annotations

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_openai import OpenAIEmbeddings

from chatbot.config import (
    CHROMA_COLLECTION_NAME,
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL,
    OPENAI_API_KEY,
    PINECONE_API_KEY,
    PINECONE_CLOUD,
    PINECONE_CREATE_INDEX,
    PINECONE_INDEX_NAME,
    PINECONE_NAMESPACE,
    PINECONE_REGION,
    VECTOR_DB_DIR,
    VECTOR_STORE,
)


def get_embeddings() -> OpenAIEmbeddings:
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY não definida. Configure no arquivo .env na raiz do projeto."
        )
    return OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=OPENAI_API_KEY)


def _use_pinecone() -> bool:
    return VECTOR_STORE == "pinecone"


def _pinecone_index():
    from pinecone import Pinecone, ServerlessSpec

    if not PINECONE_API_KEY:
        raise ValueError(
            "VECTOR_STORE=pinecone, mas PINECONE_API_KEY não está no .env."
        )

    pc = Pinecone(api_key=PINECONE_API_KEY)

    if PINECONE_CREATE_INDEX and not pc.has_index(PINECONE_INDEX_NAME):
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
        )

    if not pc.has_index(PINECONE_INDEX_NAME):
        raise ValueError(
            f"Índice Pinecone '{PINECONE_INDEX_NAME}' não existe. "
            "Crie no console (https://app.pinecone.io) com dimensão "
            f"{EMBEDDING_DIMENSION} e métrica cosine, ou defina "
            "PINECONE_CREATE_INDEX=true no .env."
        )

    return pc.Index(PINECONE_INDEX_NAME)


def _clear_pinecone_namespace() -> None:
    from pinecone.exceptions import NotFoundException

    index = _pinecone_index()
    try:
        index.delete(delete_all=True, namespace=PINECONE_NAMESPACE)
    except NotFoundException:
        pass  # namespace ainda não existe na primeira indexação


def _build_pinecone(chunks: list[Document], *, reset: bool) -> VectorStore:
    from langchain_pinecone import PineconeVectorStore

    if reset:
        _clear_pinecone_namespace()

    embeddings = get_embeddings()

    batch_size = 100
    store: PineconeVectorStore | None = None
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        if store is None:
            store = PineconeVectorStore.from_documents(
                batch,
                embedding=embeddings,
                index_name=PINECONE_INDEX_NAME,
                namespace=PINECONE_NAMESPACE,
            )
        else:
            store.add_documents(batch, namespace=PINECONE_NAMESPACE)

    if store is None:
        raise ValueError("Nenhum trecho para indexar no Pinecone.")
    return store


def _build_chroma(chunks: list[Document], *, reset: bool) -> VectorStore:
    persist_dir = VECTOR_DB_DIR
    embeddings = get_embeddings()

    if reset and persist_dir.exists():
        import shutil

        shutil.rmtree(persist_dir)

    persist_dir.mkdir(parents=True, exist_ok=True)

    batch_size = 100
    store: Chroma | None = None
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        if store is None:
            store = Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                collection_name=CHROMA_COLLECTION_NAME,
                persist_directory=str(persist_dir),
            )
        else:
            store.add_documents(batch)

    if store is None:
        raise ValueError("Nenhum trecho para indexar no Chroma.")
    return store


def build_vector_store(chunks: list[Document], *, reset: bool = False) -> VectorStore:
    if _use_pinecone():
        return _build_pinecone(chunks, reset=reset)
    return _build_chroma(chunks, reset=reset)


def get_vector_store() -> VectorStore | None:
    if not OPENAI_API_KEY:
        return None

    embeddings = get_embeddings()

    if _use_pinecone():
        if not PINECONE_API_KEY:
            return None
        try:
            from langchain_pinecone import PineconeVectorStore

            index = _pinecone_index()
            stats = index.describe_index_stats()
            ns_stats = stats.get("namespaces", {}).get(PINECONE_NAMESPACE)
            count = (ns_stats or {}).get("vector_count", 0)
            if not count:
                return None

            return PineconeVectorStore(
                index,
                embeddings,
                text_key="text",
                namespace=PINECONE_NAMESPACE,
            )
        except Exception:
            return None

    if not VECTOR_DB_DIR.exists():
        return None

    return Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(VECTOR_DB_DIR),
    )


def vector_store_count(store: VectorStore) -> int | str:
    if _use_pinecone():
        try:
            index = _pinecone_index()
            stats = index.describe_index_stats()
            ns = stats.get("namespaces", {}).get(PINECONE_NAMESPACE, {})
            return ns.get("vector_count", 0)
        except Exception:
            return "?"
    try:
        return store._collection.count()  # type: ignore[attr-defined]
    except Exception:
        return "?"


def store_label() -> str:
    if _use_pinecone():
        return f"Pinecone (`{PINECONE_INDEX_NAME}` / namespace `{PINECONE_NAMESPACE}`)"
    return f"Chroma (`{VECTOR_DB_DIR}`)"
