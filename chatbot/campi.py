"""Extrai campus e curso da pergunta para buscas web direcionadas."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from chatbot.config import ROOT

CAMPUS_DATA_PATH = ROOT / "data" / "campi_cursos.yaml"

_COURSE_PATTERNS = (
    re.compile(
        r"curso\s+de\s+([a-záàâãéêíóôõúç0-9\s\-]+?)(?:\s+no\s+|\s+na\s+|\s+em\s+|\?|$|,)",
        re.I,
    ),
    re.compile(
        r"coordenador(?:a)?\s+(?:do|da|de)\s+(?:curso\s+)?([a-záàâãéêíóôõúç0-9\s\-]+?)(?:\s+no\s+|\s+na\s+|\s+em\s+|\?|$|,)",
        re.I,
    ),
    re.compile(
        r"coordenação\s+(?:do|da|de)\s+([a-záàâãéêíóôõúç0-9\s\-]+?)(?:\s+no\s+|\s+na\s+|\s+em\s+|\?|$|,)",
        re.I,
    ),
)


def _load_yaml() -> dict:
    if not CAMPUS_DATA_PATH.exists():
        return {"campi": [], "cargos_curso": []}
    with CAMPUS_DATA_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_campus_entries() -> list[dict]:
    return _load_yaml().get("campi", [])


def get_compound_centers() -> list[dict]:
    return _load_yaml().get("centros_por_cidade", [])


def _best_alias_match(question: str, entry: dict) -> tuple[int, str] | None:
    q = question.lower()
    nome = entry.get("nome", "")
    best: tuple[int, str] | None = None
    for alias in [nome.lower(), *[a.lower() for a in entry.get("aliases", [])]]:
        if alias and alias in q:
            if best is None or len(alias) > best[0]:
                best = (len(alias), nome)
    return best


def _compound_sigla_in_question(question: str, sigla: str) -> bool:
    s = sigla.lower()
    q = question.lower()
    if len(s) <= 5:
        return bool(re.search(rf"\b{re.escape(s)}\b", q))
    return s in q


def _extract_compound_campus(question: str) -> str | None:
    """Resolve siglas ambíguas (ex.: CIES) apenas quando a cidade também aparece."""
    best: tuple[int, str] | None = None
    entries_by_name = {e.get("nome", ""): e for e in get_campus_entries()}

    for group in get_compound_centers():
        siglas = group.get("siglas", [])
        campi_nomes = group.get("campi", [])
        if not any(_compound_sigla_in_question(question, s) for s in siglas):
            continue

        for campus_nome in campi_nomes:
            entry = entries_by_name.get(campus_nome)
            if not entry:
                continue
            matched = _best_alias_match(question, entry)
            if matched and (best is None or matched[0] > best[0]):
                best = matched

    return best[1] if best else None


def extract_campus(question: str) -> str | None:
    compound = _extract_compound_campus(question)
    if compound:
        return compound

    best: tuple[int, str] | None = None
    for entry in get_campus_entries():
        matched = _best_alias_match(question, entry)
        if matched and (best is None or matched[0] > best[0]):
            best = matched
    return best[1] if best else None


def get_course_staff_keywords() -> tuple[str, ...]:
    data = _load_yaml()
    defaults = (
        "coordenador",
        "coordenadora",
        "coordenação",
        "coordenacao",
        "vice-coordenador",
        "diretor do curso",
        "secretaria do curso",
    )
    extra = tuple(data.get("cargos_curso", []))
    return tuple(dict.fromkeys(defaults + extra))


def extract_course_hint(question: str) -> str | None:
    for pattern in _COURSE_PATTERNS:
        m = pattern.search(question)
        if m:
            hint = m.group(1).strip()
            if len(hint) >= 3:
                return hint
    return None


def parse_academic_staff_context(question: str) -> dict:
    """Contexto para busca: coordenador(a), curso e campus."""
    q = question.lower()
    keywords = get_course_staff_keywords()
    is_staff = any(k in q for k in keywords)
    campus = extract_campus(question)
    course = extract_course_hint(question)

    # "coordenador de computação no campus de Piripiri" sem "curso de"
    if is_staff and not course:
        m = re.search(
            r"coordenador(?:a)?\s+(?:do|da|de)\s+([a-záàâãéêíóôõúç0-9\s\-]+?)"
            r"(?:\s+no\s+|\s+na\s+|\s+em\s+|\?|$|,)",
            question,
            re.I,
        )
        if m:
            course = m.group(1).strip()

    return {
        "is_course_staff": is_staff,
        "campus": campus,
        "course": course,
    }
