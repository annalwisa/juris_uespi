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


def _llm():
    return ChatOpenAI(model=CHAT_MODEL, api_key=OPENAI_API_KEY, temperature=0.2)


def _sigaa_has_results(sigaa_context: str) -> bool:
    return "[SIGAA 1]" in sigaa_context


def answer_with_rag(
    vector_store: VectorStore,
    question: str,
    history: list | None = None,
) -> str:
    search_query = enhance_retrieval_query(
        question, build_retrieval_query(question, history)
    )
    search_query = enhance_estagio_query(question, search_query)
    search_query = enhance_jubilacao_query(question, search_query)
    if is_monitoria_detail_question(question):
        search_query = f"{search_query} Edita-de-Monitorias edital monitoria requisitos inscricao"

    docs = retrieve_context(vector_store, search_query)
    context = format_context(docs)

    sigaa_context = NO_SIGAA
    try:
        sig_ctx = get_sigaa_context_for_question(search_query)
        if sig_ctx:
            sigaa_context = sig_ctx
    except Exception as e:
        sigaa_context = (
            f"(Erro ao consultar SIGAA: {e}. Consulte {SIGAA_CURSOS_URL})"
        )

    web_context = NO_WEB
    run_web = should_search_web(search_query, docs)
    if run_web and is_course_staff_question(search_query) and _sigaa_has_results(
        sigaa_context
    ):
        run_web = False

    if run_web:
        try:
            results = search_uespi_web(search_query)
            web_context = format_web_context(results, search_query)
        except Exception as e:
            web_context = (
                f"(Erro na busca web: {e}. Para reitoria, consulte uespi.br.)"
            )

    lc_history = to_langchain_messages(history)
    alerts = get_contextual_alerts(question, history)
    cursos_context = get_cursos_context(question, history)
    programs_context = get_programs_context(question, history)
    estagio_context = get_estagio_context(question, history)
    jubilacao_context = get_jubilacao_context(question, history)

    chain = RAG_PROMPT | _llm() | StrOutputParser()
    return chain.invoke(
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
            "question": question,
        }
    )


def get_answer(question: str, history: list | None = None) -> str:
    if not OPENAI_API_KEY:
        return "Configure OPENAI_API_KEY no arquivo .env e reinicie o aplicativo."

    question = question.strip()
    history = history or []

    if not is_message_allowed(question):
        return moderation_response()

    if is_assistant_identity_question(question):
        return assistant_name_response()

    if is_about_assistant_question(question):
        return about_assistant_response()

    faq = get_faq_response(question, history)
    if faq is not None:
        return faq

    if not is_uespi_related(question, history):
        return refusal_response()

    vector_store = get_vector_store()
    if vector_store is not None:
        return answer_with_rag(vector_store, question, history)

    chain = CHAT_PROMPT | _llm() | StrOutputParser()
    return chain.invoke(
        {
            "question": question,
            "history": to_langchain_messages(history),
        }
    )


def web_search_status_label() -> str:
    if not _ws_on():
        return "desativada"
    return f"ativa (modo `{WEB_SEARCH_MODE}`)"
