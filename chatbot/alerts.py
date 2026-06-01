"""Alertas institucionais exibidos em perguntas específicas."""

from __future__ import annotations

import re
import unicodedata

ABSENCE_KEYWORDS = (
    "falta",
    "faltas",
    "frequencia",
    "frequência",
    "presença",
    "presenca",
    "ausencia",
    "ausência",
    "comparecimento",
    "reprovar por falta",
    "percentual de falta",
    "limite de falta",
    "maximo de falta",
    "máximo de falta",
)

ABSENCE_ALERT = """**Atenção — contagem de faltas:** em disciplinas com **duas aulas no mesmo dia**, **uma única ausência** pode ser registrada como **duas faltas** no sistema. Ao calcular se você está dentro do limite permitido pelo Regimento (em geral, até 25% de faltas / mínimo de 75% de frequência), some as faltas conforme o registro acadêmico, não apenas os dias em que faltou."""


def _normalize(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def is_absence_question(question: str, history: list | None = None) -> bool:
    blob = _normalize(question)
    if any(k in blob for k in ABSENCE_KEYWORDS):
        return True
    if history:
        from chatbot.history import _message_text

        for item in history[-6:]:
            parsed = _message_text(item)
            if parsed and parsed[0] == "user":
                h = _normalize(parsed[1])
                if any(k in h for k in ABSENCE_KEYWORDS):
                    return True
    return False


def get_contextual_alerts(question: str, history: list | None = None) -> str:
    if is_absence_question(question, history):
        return ABSENCE_ALERT
    return "(Nenhum alerta adicional para esta pergunta.)"
