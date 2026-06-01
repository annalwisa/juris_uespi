"""Mensagem de status da base documental e integrações."""
import json

from chatbot.chain import web_search_status_label
from chatbot.config import CHAT_HISTORY_MAX_MESSAGES, DOCS_DIR, SIGAA_CURSOS_URL, VECTOR_STORE
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


def status_message() -> str:
    store = get_vector_store()
    backend = store_label()
    sigaa = sigaa_status()
    if store is None:
        hint = (
            f"Coloque PDFs em `{DOCS_DIR}` e execute `python -m chatbot.ingest_cli`."
        )
        if VECTOR_STORE == "pinecone":
            hint += " Configure PINECONE_API_KEY e o índice no `.env`."
        return (
            f"**Modo sem base documental** ({backend}). {hint} "
            f"**SIGAA:** {sigaa}."
        )
    count = vector_store_count(store)
    return (
        f"**Base ativa** ({backend}): {count} trechos. "
        f"**SIGAA:** {sigaa} — [lista de cursos]({SIGAA_CURSOS_URL}). "
        f"**Busca web:** {web_search_status_label()}. "
        f"**Memória:** últimas {CHAT_HISTORY_MAX_MESSAGES} mensagens da conversa."
    )
