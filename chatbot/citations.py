"""Links oficiais para citação nas respostas."""

from chatbot.config import REGIMENTO_PDF_URL


def format_source_citation(source: str) -> str:
    """Formata nome de arquivo/fonte; Regimento.pdf vira link oficial."""
    if not source:
        return "documento"
    name = source.strip()
    if name.lower() in ("regimento.pdf", "regimento"):
        return f"[Regimento.pdf]({REGIMENTO_PDF_URL})"
    return name


def regimento_link_markdown() -> str:
    return f"[Regimento.pdf]({REGIMENTO_PDF_URL})"
