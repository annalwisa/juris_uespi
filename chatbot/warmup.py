"""Pré-carrega modelos e caches na subida da API para reduzir latência da 1ª pergunta."""

from __future__ import annotations

import logging
import threading

import chatbot.config as config

logger = logging.getLogger(__name__)
_warmup_started = False
_warmup_lock = threading.Lock()


def warmup() -> None:
    """Carrega vector store, reranker, SIGAA e BM25 em background."""
    if not config.RAG_PRELOAD_ON_STARTUP:
        return

    if config.RERANKER_ENABLED:
        try:
            from chatbot.rerank import _cross_encoder

            _cross_encoder()
            logger.info("Reranker carregado.")
        except Exception as exc:
            logger.warning("Falha ao pré-carregar reranker: %s", exc)

    try:
        from chatbot.vectorstore import get_vector_store

        store = get_vector_store()
        if store is not None:
            from chatbot.vectorstore import vector_store_count

            count = vector_store_count(store)
            logger.info("Vector store pronto (%s trechos).", count)
        else:
            logger.warning(
                "Vector store indisponível — verifique OPENAI_API_KEY e Pinecone no .env."
            )
    except Exception as exc:
        logger.warning("Falha ao pré-carregar vector store: %s", exc)

    try:
        from chatbot.hybrid import get_bm25_index

        if get_bm25_index() is not None:
            logger.info("Índice BM25 carregado.")
    except Exception as exc:
        logger.warning("Falha ao pré-carregar BM25: %s", exc)

    try:
        from chatbot.sigaa import load_courses

        load_courses()
        logger.info("Cache SIGAA pronto.")
    except Exception as exc:
        logger.warning("Falha ao pré-carregar SIGAA: %s", exc)

    try:
        from chatbot.gestao import load_gestao_data

        load_gestao_data()
        logger.info("Cache gestão (agenda telefônica) pronto.")
    except Exception as exc:
        logger.warning("Falha ao pré-carregar gestão: %s", exc)


def start_warmup_background() -> None:
    """Dispara warmup uma única vez em thread daemon."""
    global _warmup_started
    with _warmup_lock:
        if _warmup_started:
            return
        _warmup_started = True
    threading.Thread(target=warmup, name="chatbot-warmup", daemon=True).start()
