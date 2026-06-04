"""Bloqueia perguntas fora do escopo UESPI antes de chamar o modelo."""

from __future__ import annotations

import re
import unicodedata

from chatbot.about import is_about_assistant_question, is_assistant_identity_question
from chatbot.campi import get_campus_entries
from chatbot.history import _message_text

# Menção explícita à universidade
UESPI_MARKERS = (
    "uespi",
    "universidade estadual do piaui",
    "universidade estadual do piauí",
    "sigaa.uespi",
    "sigaa uespi",
)

# Vocabulário acadêmico típico de dúvidas institucionais (com histórico UESPI ou menção implícita)
ACADEMIC_TERMS = (
    "reitor",
    "reitoria",
    "pró-reitor",
    "pro-reitor",
    "coordenador",
    "coordenadora",
    "coordenação",
    "coordenacao",
    "regimento",
    "resolução",
    "resolucao",
    "cepex",
    "consun",
    "conaplan",
    "matrícula",
    "matricula",
    "vestibular",
    "crédito",
    "credito",
    "disciplina",
    "grade curricular",
    "tcc",
    "estágio",
    "estagio",
    "stricto sensu",
    "lato sensu",
    "estagio supervisionado",
    "estágio supervisionado",
    "estagiário",
    "estagiaria",
    "estagiária",
    "estagiarios",
    "estagiários",
    "convenio",
    "convênio",
    "conveniada",
    "conveniadas",
    "conveniado",
    "conveniados",
    "termo de compromisso",
    "parte concedente",
    "lei 11.788",
    "lei 11788",
    "residencia pedagogica",
    "residência pedagógica",
    "preg",
    "dap",
    "preg-dap-des",
    "mestrado",
    "doutorado",
    "graduação",
    "graduacao",
    "pós-graduação",
    "pos-graduacao",
    "campus",
    "sede",
    "modalidade",
    "frequência",
    "frequencia",
    "falta",
    "faltas",
    "nota",
    "notas",
    "aprovação",
    "aprovar",
    "reprovação",
    "reprovar",
    "reprovacao",
    "colação",
    "diploma",
    "histórico escolar",
    "historico escolar",
    "transferência",
    "transferencia",
    "trancamento",
    "jubilado",
    "jubilada",
    "jubilar",
    "jubilados",
    "jubiladas",
    "jubilamento",
    "jubilação",
    "jubilacao",
    "cancelamento de matrícula",
    "cancelamento de matricula",
    "cancelamento da matrícula",
    "cancelamento da matricula",
    "integralização",
    "integralizacao",
    "integralizar o curso",
    "prazo máximo do curso",
    "prazo maximo do curso",
    "edital",
    "cota",
    "cotas",
    "prouni",
    "fies",
    "prograd",
    "proex",
    "cepex",
    "dae",
    "biblioteca",
    "bibliotecas",
    "biblioteca universitária",
    "biblioteca central",
    "acervo",
    "pibic",
    "pibit",
    "pibeu",
    "iniciação científica",
    "iniciacao cientifica",
    "iniciação tecnológica",
    "iniciacao tecnologica",
    "iniciação em extensão",
    "iniciacao em extensao",
    "bolsa de iniciação",
    "bolsa de iniciacao",
    "monitoria",
    "monitor",
    "bolsa de pesquisa",
    "cnpq",
    "propi",
    "prop",
    "sigprop",
    "proex",
    "pibiti",
    "valor da bolsa",
    "vigencia",
    "vigência",
    "pesquisa institucional",
    "extensão universitária",
    "extensao universitaria",
)

# Padrões claramente fora do escopo (só bloqueia se NÃO houver sinal UESPI)
OFF_TOPIC_PATTERNS = (
    r"\breceita\s+de\b",
    r"\bcomo\s+fazer\s+(um\s+)?(bolo|pizza|sushi)\b",
    r"\bpython\s+(tutorial|curso|aprender)\b",
    r"\bjavascript\b",
    r"\bcopa\s+do\s+mundo\b",
    r"\bfutebol\b",
    r"\bbitcoin\b",
    r"\bcrypto\b",
    r"\bgpt-4\b",
    r"\bopenai\b",
    r"\bchatgpt\b",
    r"\bnetflix\b",
    r"\bspotify\b",
    r"\bwhatsapp\b",
    r"\binstagram\b",
    r"\btiktok\b",
    r"\bgame\s+of\s+thrones\b",
    r"\btraduz(a|ir)\s+para\s+inglês\b",
    r"\btraduza\s+para\b",
    r"\bpiada\b",
    r"\bconte\s+uma\s+história\b",
    r"\bconte\s+uma\s+historia\b",
    r"\bcódigo\s+fonte\b",
    r"\bprogramar\s+em\b",
    r"\bqual\s+a\s+capital\s+(da|de)\s+(frança|argentina|brasil)\b",
    r"\bquem\s+é\s+o\s+presidente\s+(do|da)\s+brasil\b",
    r"\bclima\s+em\b",
    r"\bprevisão\s+do\s+tempo\b",
)

REFUSAL_MESSAGE = """Só posso ajudar com assuntos relacionados à **Universidade Estadual do Piauí (UESPI)**.

Exemplos do que posso responder:
- Regimento, resoluções, faltas, matrícula e normas acadêmicas
- Cursos, coordenadores, campi e modalidades (SIGAA)
- Reitoria e gestão atual da universidade

Reformule sua pergunta incluindo o contexto da UESPI ou visite [uespi.br](https://uespi.br)."""


def _normalize(text: str) -> str:
    if not text:
        return ""
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def _campus_aliases() -> tuple[str, ...]:
    aliases: list[str] = []
    for entry in get_campus_entries():
        nome = entry.get("nome", "")
        if nome:
            aliases.append(_normalize(nome))
        for a in entry.get("aliases", []):
            if a:
                aliases.append(_normalize(str(a)))
    return tuple(aliases)


def _text_from_history(history: list | None) -> str:
    if not history:
        return ""
    parts: list[str] = []
    for item in history:
        parsed = _message_text(item)
        if parsed and parsed[1]:
            parts.append(parsed[1])
    return " ".join(parts)


def _has_uespi_marker(text: str) -> bool:
    n = _normalize(text)
    if any(m in n for m in UESPI_MARKERS):
        return True
    if "sigaa" in n and ("uespi" in n or "piauí" in n or "piaui" in n):
        return True
    return False


def _has_campus_marker(text: str) -> bool:
    n = _normalize(text)
    return any(alias in n for alias in _campus_aliases() if len(alias) >= 4)


def _has_academic_term(text: str) -> bool:
    n = _normalize(text)
    return any(term in n for term in ACADEMIC_TERMS)


def _is_clearly_off_topic(text: str) -> bool:
    n = _normalize(text)
    return any(re.search(p, n) for p in OFF_TOPIC_PATTERNS)


def _conversation_was_uespi(history: list | None) -> bool:
    blob = _text_from_history(history)
    if not blob:
        return False
    return (
        _has_uespi_marker(blob)
        or _has_campus_marker(blob)
        or _has_academic_term(blob)
    )


def is_uespi_related(question: str, history: list | None = None) -> bool:
    """
    True se a pergunta (ou o histórico recente) for sobre a UESPI.
    Perguntas fora do escopo retornam False — o modelo não é chamado.
    """
    q = question.strip()
    if not q:
        return False

    if is_assistant_identity_question(q) or is_about_assistant_question(q):
        return True

    combined = f"{_text_from_history(history)} {q}"

    if _has_uespi_marker(q) or _has_uespi_marker(combined):
        return True

    if _has_campus_marker(q):
        return True

    # Follow-up na mesma conversa sobre UESPI (ex.: "e em Teresina?")
    if _conversation_was_uespi(history):
        if _is_clearly_off_topic(q) and not _has_academic_term(q):
            return False
        return True

    n = _normalize(q)

    if _is_clearly_off_topic(q):
        return False

    # Assistente exclusivo UESPI: normas, faltas, matrícula etc. não exigem citar "UESPI"
    if _has_academic_term(q):
        return True

    # Termos acadêmicos + Piauí/Teresina
    if any(x in n for x in ("piauí", "piaui", "teresina")):
        return True

    # Saudação ou mensagem muito curta sem conteúdo acadêmico
    if len(n.split()) <= 3 and not _conversation_was_uespi(history):
        return False

    return False


def refusal_response() -> str:
    return REFUSAL_MESSAGE
