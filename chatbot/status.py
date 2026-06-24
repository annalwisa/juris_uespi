"""Mensagem de status da base documental e integrações."""

import json

from chatbot.chain import web_search_status_label
from chatbot.config import (
    CHAT_HISTORY_MAX_MESSAGES,
    DOCS_DIR,
    OPENAI_API_KEY,
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
    PINECONE_NAMESPACE,
    SIGAA_CURSOS_URL,
    VECTOR_STORE,
)
from chatbot.sigaa import CACHE_FILE
from chatbot.vectorstore import get_vector_store, store_label, vector_store_count


def sigaa_status() -> str:
    if not CACHE_FILE.exists():
        return "cache vazio (consulta na 1ª pergunta sobre cursos)"
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        return f"{data.get('count', '?')} cursos (atualizado {data.get('fetched_at', '?')[:10]})"
    except Exception:
        return "cache presente"


def _missing_store_hint() -> str:
    if VECTOR_STORE == "pinecone":
        parts = []
        if not OPENAI_API_KEY:
            parts.append("defina `OPENAI_API_KEY`")
        if not PINECONE_API_KEY:
            parts.append("defina `PINECONE_API_KEY`")
        if not parts:
            return (
                f"o índice `{PINECONE_INDEX_NAME}` (namespace `{PINECONE_NAMESPACE}`) "
                "parece vazio ou inacessível. Quem mantém o projeto já deixa os PDFs "
                "indexados no Pinecone — não é preciso rodar o ingest para testar."
            )
        return f"{'; '.join(parts)} no `.env`."
    return (
        f"coloque PDFs em `{DOCS_DIR}` e execute `python -m chatbot.ingest_cli`, "
        "ou use Pinecone (veja o README)."
    )


def status_message() -> str:
    store = get_vector_store()
    backend = store_label()
    sigaa = sigaa_status()
    if store is None:
        return (
            f"**Modo sem base documental** ({backend}). {_missing_store_hint()} "
            f"**SIGAA:** {sigaa}."
        )
    count = vector_store_count(store)
    return (
        f"**Base ativa** ({backend}): {count} trechos. "
        f"**SIGAA:** {sigaa} — [lista de cursos]({SIGAA_CURSOS_URL}). "
        f"**Busca web:** {web_search_status_label()}. "
        f"**Memória:** últimas {CHAT_HISTORY_MAX_MESSAGES} mensagens da conversa."
    )
