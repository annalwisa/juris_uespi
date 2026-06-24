from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.vectorstores import VectorStore
from langchain_openai import ChatOpenAI

from chatbot.config import (
    CHAT_MODEL,
    HYBRID_PROMPT_SUFFIX,
    OPENAI_API_KEY,
    SIGAA_CURSOS_URL,
    SYSTEM_PROMPT,
    WEB_SEARCH_MODE,
)
from chatbot.about import (
    about_assistant_response,
    assistant_name_response,
    is_about_assistant_question,
    is_assistant_identity_question,
)
from chatbot.faq import get_faq_response, is_monitoria_detail_question
from chatbot.cursos import get_cursos_context
from chatbot.alerts import get_contextual_alerts
from chatbot.estagio import enhance_estagio_query, get_estagio_context
from chatbot.jubilacao import enhance_jubilacao_query, get_jubilacao_context
from chatbot.gestao import get_gestao_context, parse_gestao_context
from chatbot.programs import enhance_retrieval_query, get_programs_context
from chatbot.guard import is_uespi_related, refusal_response
from chatbot.moderation import is_message_allowed, moderation_response
from chatbot.history import build_retrieval_query, to_langchain_messages
from chatbot.retrieval import format_context, retrieve_context
from chatbot.sigaa import get_sigaa_context_for_question
from chatbot.vectorstore import get_vector_store
from chatbot.web_search import (
    format_web_context,
    is_course_staff_question,
    search_uespi_web,
    should_search_web,
    web_search_enabled as _ws_on,
)

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT + HYBRID_PROMPT_SUFFIX),
        MessagesPlaceholder("history"),
        (
            "human",
            """## Documentos oficiais indexados (regimento, resoluções — podem estar desatualizados em nomes)
{context}

## SIGAA — cursos de graduação (coordenador, sede, modalidade — fonte oficial)
{sigaa_context}

## Cursos por campus e centro (a qual centro/CIES cada curso pertence: bacharelado, licenciatura, tecnólogo)
{cursos_context}

## Gestão de centros e campi (diretor(a) — fonte oficial uespi.br; NÃO confundir com coordenação de curso)
{gestao_context}

## Busca na web (reitoria e complemento quando o SIGAA não bastar)
{web_context}

## Alertas (informe o usuário quando aplicável)
{alerts}

## Programas de bolsas (PIBIC, PIBIT, PIBEU)
{programs_context}

## Estágio supervisionado (Lei 11.788/2008, Resolução CEPEX 004/2021, PREG/DAP/DES, planilha de conveniadas)
{estagio_context}

## Jubilação na UESPI (formalmente: Cancelamento da Matrícula Institucional — Regimento, Art. 46)
{jubilacao_context}

Pergunta atual do usuário:
{question}""",
        ),
    ]
)

CHAT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            SYSTEM_PROMPT
            + "\n\n(Nenhum documento indexado no momento — não responda sobre normas específicas.)",
        ),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ]
)

NO_WEB = "(Busca web não acionada — priorize SIGAA para cursos ou PDFs para normas.)"
NO_SIGAA = (
    f"(SIGAA não consultado para esta pergunta. Lista de cursos: {SIGAA_CURSOS_URL})"
)


@lru_cache(maxsize=1)
def _llm():
    return ChatOpenAI(model=CHAT_MODEL, api_key=OPENAI_API_KEY, temperature=0.2)


def _sigaa_has_results(sigaa_context: str) -> bool:
    return "[SIGAA 1]" in sigaa_context


def _build_search_query(question: str, history: list | None) -> str:
    search_query = enhance_retrieval_query(
        question, build_retrieval_query(question, history)
    )
    search_query = enhance_estagio_query(question, search_query)
    search_query = enhance_jubilacao_query(question, search_query)
    if is_monitoria_detail_question(question):
        search_query = (
            f"{search_query} Edita-de-Monitorias edital monitoria requisitos inscricao"
        )
    return search_query


def _resolve_sigaa_context(sigaa_future) -> str:
    try:
        sig_ctx = sigaa_future.result()
        return sig_ctx or NO_SIGAA
    except Exception as e:
        return f"(Erro ao consultar SIGAA: {e}. Consulte {SIGAA_CURSOS_URL})"


def _should_run_web(search_query: str, docs: list[Document], sigaa_context: str) -> bool:
    if not should_search_web(search_query, docs):
        return False
    if is_course_staff_question(search_query) and _sigaa_has_results(sigaa_context):
        return False
    gestao_ctx = parse_gestao_context(search_query)
    if gestao_ctx.get("is_gestao") and (
        gestao_ctx.get("centro") or gestao_ctx.get("campus") or gestao_ctx.get("nucleo")
    ):
        return False
    return True


def _resolve_web_context(
    search_query: str, docs: list[Document], sigaa_context: str
) -> str:
    if not _should_run_web(search_query, docs, sigaa_context):
        return NO_WEB
    try:
        results = search_uespi_web(search_query)
        return format_web_context(results, search_query)
    except Exception as e:
        return f"(Erro na busca web: {e}. Para reitoria, consulte uespi.br.)"


def answer_with_rag(
    vector_store: VectorStore,
    question: str,
    history: list | None = None,
) -> str:
    answer, _docs = answer_with_rag_details(vector_store, question, history)
    return answer


def answer_with_rag_details(
    vector_store: VectorStore,
    question: str,
    history: list | None = None,
) -> tuple[str, list[Document]]:
    """Igual a ``answer_with_rag``, mas também retorna os trechos recuperados.

    Útil para avaliação (métricas RAG) e para etapas que precisam inspecionar
    o contexto efetivamente usado na geração da resposta.
    """
    search_query = _build_search_query(question, history)

    with ThreadPoolExecutor(max_workers=6) as executor:
        docs_future = executor.submit(retrieve_context, vector_store, search_query)
        sigaa_future = executor.submit(get_sigaa_context_for_question, search_query)
        cursos_future = executor.submit(get_cursos_context, question, history)
        programs_future = executor.submit(get_programs_context, question, history)
        estagio_future = executor.submit(get_estagio_context, question, history)
        jubilacao_future = executor.submit(get_jubilacao_context, question, history)
        gestao_future = executor.submit(get_gestao_context, question, history)
        alerts_future = executor.submit(get_contextual_alerts, question, history)

        docs = docs_future.result()
        sigaa_context = _resolve_sigaa_context(sigaa_future)
        cursos_context = cursos_future.result()
        programs_context = programs_future.result()
        estagio_context = estagio_future.result()
        jubilacao_context = jubilacao_future.result()
        gestao_context = gestao_future.result()
        alerts = alerts_future.result()

    context = format_context(docs)
    web_context = _resolve_web_context(search_query, docs, sigaa_context)
    lc_history = to_langchain_messages(history)

    chain = RAG_PROMPT | _llm() | StrOutputParser()
    answer = chain.invoke(
        {
            "history": lc_history,
            "context": context,
            "sigaa_context": sigaa_context,
            "cursos_context": cursos_context,
            "web_context": web_context,
            "alerts": alerts,
            "programs_context": programs_context,
            "estagio_context": estagio_context,
            "jubilacao_context": jubilacao_context,
            "gestao_context": gestao_context,
            "question": question,
        }
    )
    return answer, docs


def get_answer(question: str, history: list | None = None) -> str:
    answer, _docs = get_answer_details(question, history)
    return answer


def get_answer_details(
    question: str, history: list | None = None
) -> tuple[str, list[Document]]:
    """Resposta + trechos recuperados, aplicando os mesmos filtros de ``get_answer``.

    Para perguntas que não passam pelo RAG (saudação, FAQ, moderação, fora de
    escopo), a lista de trechos retorna vazia.
    """
    if not OPENAI_API_KEY:
        return (
            "Configure OPENAI_API_KEY no arquivo .env e reinicie o aplicativo.",
            [],
        )

    question = question.strip()
    history = history or []

    if not is_message_allowed(question):
        return moderation_response(), []

    if is_assistant_identity_question(question):
        return assistant_name_response(), []

    if is_about_assistant_question(question):
        return about_assistant_response(), []

    faq = get_faq_response(question, history)
    if faq is not None:
        return faq, []

    if not is_uespi_related(question, history):
        return refusal_response(), []

    vector_store = get_vector_store()
    if vector_store is not None:
        return answer_with_rag_details(vector_store, question, history)

    chain = CHAT_PROMPT | _llm() | StrOutputParser()
    answer = chain.invoke(
        {
            "question": question,
            "history": to_langchain_messages(history),
        }
    )
    return answer, []


def web_search_status_label() -> str:
    if not _ws_on():
        return "desativada"
    return f"ativa (modo `{WEB_SEARCH_MODE}`)"
