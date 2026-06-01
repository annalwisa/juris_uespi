"""Histórico de conversa para contexto multi-turno."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from chatbot.config import CHAT_HISTORY_MAX_MESSAGES


def _message_text(item: dict | list | tuple) -> tuple[str, str] | None:
    """Retorna (role, content) ou None."""
    if isinstance(item, dict):
        role = item.get("role", "")
        content = item.get("content", "")
        if isinstance(content, list):
            # Gradio multimodal — só texto
            parts = [p.get("text", "") for p in content if isinstance(p, dict)]
            content = " ".join(p for p in parts if p)
        return role, str(content).strip()

    if isinstance(item, (list, tuple)) and len(item) >= 2:
        user, bot = item[0], item[1]
        if user:
            return "user", str(user).strip()
        if bot:
            return "assistant", str(bot).strip()
    return None


def to_langchain_messages(history: list | None) -> list:
    """Converte histórico Gradio em tuplas para MessagesPlaceholder."""
    if not history:
        return []

    messages: list = []
    for item in history[-CHAT_HISTORY_MAX_MESSAGES:]:
        parsed = _message_text(item)
        if not parsed:
            continue
        role, content = parsed
        if not content:
            continue
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role in ("assistant", "ai"):
            messages.append(AIMessage(content=content))

    return messages


def build_retrieval_query(question: str, history: list | None) -> str:
    """
    Enriquece a busca RAG/SIGAA com perguntas anteriores do usuário
    (ex.: 'e em Piripiri?' após perguntar sobre Computação).
    """
    if not history:
        return question

    prior_user: list[str] = []
    for item in history[-CHAT_HISTORY_MAX_MESSAGES:]:
        parsed = _message_text(item)
        if parsed and parsed[0] == "user" and parsed[1]:
            prior_user.append(parsed[1])

    if not prior_user:
        return question

    context = " ".join(prior_user[-2:])
    return f"{context} — Pergunta atual: {question}"


def format_history_for_prompt(history: list | None) -> str:
    """Resumo legível do histórico (fallback/debug)."""
    msgs = to_langchain_messages(history)
    if not msgs:
        return ""
    lines = []
    for m in msgs:
        label = "Usuário" if isinstance(m, HumanMessage) else "Assistente"
        lines.append(f"{label}: {m.content}")
    return "\n".join(lines)
