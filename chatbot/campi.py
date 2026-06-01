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


def extract_campus(question: str) -> str | None:
    q = question.lower()
    best: tuple[int, str] | None = None
    for entry in get_campus_entries():
        nome = entry.get("nome", "")
        for alias in [nome.lower(), *[a.lower() for a in entry.get("aliases", [])]]:
            if alias and alias in q:
                if best is None or len(alias) > best[0]:
                    best = (len(alias), nome)
    return best[1] if best else None


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
