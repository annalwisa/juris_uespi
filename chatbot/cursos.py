"""Cursos de graduação da UESPI e seus centros (fonte: uespi.br/graduacao-inicio)."""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

import yaml

from chatbot.config import ROOT

CURSOS_DATA_PATH = ROOT / "data" / "cursos_centros.yaml"
GRADUACAO_URL = "https://uespi.br/graduacao-inicio/"

# Ordem de exibição dos graus dentro de cada centro.
_GRAU_ORDER = ("Bacharelado", "Licenciatura", "Tecnologia", "Não informado")
_GRAU_PLURAL = {
    "Bacharelado": "Bacharelados",
    "Licenciatura": "Licenciaturas",
    "Tecnologia": "Tecnólogos",
    "Não informado": "Outros (grau não informado na página)",
}

# Termos que indicam pergunta sobre curso x centro/campus.
_CENTER_KEYWORDS = (
    "centro",
    "centros",
    "cceca",
    "cchl",
    "ccn",
    "ccs",
    "ccsa",
    "ctu",
    "cca",
    "cies",
    "bacharelado",
    "bacharelados",
    "licenciatura",
    "licenciaturas",
    "tecnologo",
    "tecnólogo",
    "tecnologia",
    "qual centro",
    "que centro",
    "quais cursos",
    "que cursos",
)


def _normalize(text: str) -> str:
    if not text:
        return ""
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", stripped.lower()).strip()


@lru_cache(maxsize=1)
def _load_data() -> dict:
    if not CURSOS_DATA_PATH.exists():
        return {"campi": [], "fonte": GRADUACAO_URL}
    with CURSOS_DATA_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {"campi": [], "fonte": GRADUACAO_URL}


def _iter_courses():
    """Gera tuplas (cidade, campus, sigla_centro, nome_centro, curso, grau)."""
    for campus in _load_data().get("campi", []):
        cidade = campus.get("cidade", "")
        nome_campus = campus.get("campus", "")
        for centro in campus.get("centros", []):
            sigla = centro.get("sigla", "")
            nome_centro = centro.get("nome", "")
            for curso in centro.get("cursos", []):
                yield (
                    cidade,
                    nome_campus,
                    sigla,
                    nome_centro,
                    curso.get("nome", ""),
                    curso.get("grau", "Não informado"),
                )


def is_cursos_centro_question(question: str, history: list | None = None) -> bool:
    blob = _normalize(question)
    if any(_normalize(k) in blob for k in _CENTER_KEYWORDS):
        return True
    if history:
        from chatbot.history import _message_text

        for item in history[-4:]:
            parsed = _message_text(item)
            if parsed and parsed[1]:
                if any(_normalize(k) in _normalize(parsed[1]) for k in _CENTER_KEYWORDS):
                    return True
    return False


def _format_centro(centro: dict) -> list[str]:
    sigla = centro.get("sigla", "")
    nome_centro = centro.get("nome", "")
    cabecalho = f"- **{sigla}** ({nome_centro}):" if nome_centro else f"- **{sigla}**:"

    por_grau: dict[str, list[str]] = {}
    for curso in centro.get("cursos", []):
        grau = curso.get("grau", "Não informado")
        por_grau.setdefault(grau, []).append(curso.get("nome", ""))

    linhas = [cabecalho]
    graus = list(_GRAU_ORDER) + [g for g in por_grau if g not in _GRAU_ORDER]
    for grau in graus:
        nomes = por_grau.get(grau)
        if not nomes:
            continue
        rotulo = _GRAU_PLURAL.get(grau, grau)
        linhas.append(f"  - {rotulo}: " + ", ".join(nomes))
    return linhas


def format_cursos_context(question: str = "") -> str:
    data = _load_data()
    campi = data.get("campi", [])
    if not campi:
        return f"(Sem dados de cursos por centro. Consulte {GRADUACAO_URL})"

    fonte = data.get("fonte", GRADUACAO_URL)
    lines = [
        "## Cursos de graduação presencial da UESPI por campus e centro",
        f"Fonte oficial: {fonte}",
        "Em Teresina (Campus Poeta Torquato Neto) cada curso pertence a um centro "
        "específico (CCECA, CCHL, CCN, CCS, CCSA, CTU, CCA). Nos demais campi os cursos "
        "são ofertados pelo CIES (Centro Integrado de Ensino Superior) do campus.",
        "",
    ]
    for campus in campi:
        lines.append(f"### {campus.get('campus', '')} — {campus.get('cidade', '')}")
        for centro in campus.get("centros", []):
            lines.extend(_format_centro(centro))
        lines.append("")

    lines.append(
        "Use estes dados para dizer a qual centro um curso pertence e quais cursos "
        "cada centro/campus oferece. Para coordenador, modalidade e vagas atualizadas, "
        "priorize o SIGAA."
    )
    return "\n".join(lines)


def get_cursos_context(question: str, history: list | None = None) -> str:
    if is_cursos_centro_question(question, history):
        return format_cursos_context(question)
    return "(Não se aplica a esta pergunta.)"
