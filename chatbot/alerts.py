"""Alertas contextuais exibidos em perguntas específicas.

Atualmente sem alertas configurados — a função `get_contextual_alerts` é
mantida porque o `RAG_PROMPT` já tem um placeholder dedicado e isso permite
adicionar novos avisos no futuro sem mexer no `chain.py`.
"""

from __future__ import annotations


_NO_ALERT = "(Nenhum alerta adicional para esta pergunta.)"


def get_contextual_alerts(question: str, history: list | None = None) -> str:
    return _NO_ALERT
