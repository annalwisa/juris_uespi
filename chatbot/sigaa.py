"""Consulta cursos de graduação no SIGAA público da UESPI (dados atualizados)."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

from chatbot.campi import extract_campus, extract_course_hint, parse_academic_staff_context
from chatbot.config import (
    ROOT,
    SIGAA_CACHE_HOURS,
    SIGAA_CURSOS_URL,
    SIGAA_SSL_VERIFY,
)

CACHE_DIR = ROOT / "data" / "cache"
CACHE_FILE = CACHE_DIR / "sigaa_graduacao.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; UESPI-Chatbot/1.0; +https://uespi.br) "
        "Educational assistant"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


@dataclass
class SigaaCourse:
    nome: str
    sede: str
    modalidade: str
    coordenador: str
    campus_secao: str | None = None
    fonte: str = SIGAA_CURSOS_URL


def _normalize(text: str) -> str:
    if not text:
        return ""
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def _fetch_html() -> str:
    response = requests.get(
        SIGAA_CURSOS_URL,
        headers=HEADERS,
        timeout=60,
        verify=SIGAA_SSL_VERIFY,
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def parse_courses_html(html: str) -> list[SigaaCourse]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="listagem")
    if not table:
        raise ValueError("Tabela de cursos não encontrada na página do SIGAA.")

    tbody = table.find("tbody")
    if not tbody:
        return []

    courses: list[SigaaCourse] = []
    campus_secao: str | None = None

    for tr in tbody.find_all("tr"):
        sub = tr.find("td", class_="subFormulario")
        if sub:
            campus_secao = sub.get_text(strip=True)
            continue

        tds = tr.find_all("td")
        if len(tds) < 4:
            continue

        nome = tds[0].get_text(" ", strip=True)
        if not nome:
            continue

        courses.append(
            SigaaCourse(
                nome=nome,
                sede=tds[1].get_text(" ", strip=True),
                modalidade=tds[2].get_text(" ", strip=True),
                coordenador=tds[3].get_text(" ", strip=True),
                campus_secao=campus_secao,
            )
        )

    return courses


def load_courses(*, force_refresh: bool = False) -> list[SigaaCourse]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if not force_refresh and CACHE_FILE.exists():
        try:
            payload = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            fetched = datetime.fromisoformat(payload["fetched_at"])
            if datetime.now(timezone.utc) - fetched < timedelta(hours=SIGAA_CACHE_HOURS):
                return [SigaaCourse(**c) for c in payload["courses"]]
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass

    courses = parse_courses_html(_fetch_html())
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "url": SIGAA_CURSOS_URL,
        "count": len(courses),
        "courses": [asdict(c) for c in courses],
    }
    CACHE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return courses


def _matches_course(course: SigaaCourse, course_hint: str | None) -> bool:
    if not course_hint:
        return True
    hint = _normalize(course_hint)
    nome = _normalize(course.nome)
    if hint in nome or nome in hint:
        return True
    # palavras-chave (ex.: "computacao" ~ "ciencia da computacao")
    hint_tokens = [t for t in re.split(r"[\s\-]+", hint) if len(t) >= 4]
    return bool(hint_tokens) and all(t in nome for t in hint_tokens)


def _matches_campus(course: SigaaCourse, campus: str | None) -> bool:
    if not campus:
        return True
    c = _normalize(campus)
    sede = _normalize(course.sede)
    secao = _normalize(course.campus_secao or "")
    return c in sede or c in secao or sede in c


def _course_filters(course_hint: str | None, campus: str | None):
    """Filtros em ordem de prioridade: estrito (curso E campus) → curso → campus."""
    yield lambda c: _matches_course(c, course_hint) and _matches_campus(c, campus)
    if course_hint:
        yield lambda c: _matches_course(c, course_hint)
    if campus:
        yield lambda c: _matches_campus(c, campus)


def search_courses(
    *,
    course_hint: str | None = None,
    campus: str | None = None,
    limit: int = 15,
) -> list[SigaaCourse]:
    courses = load_courses()
    matched: list[SigaaCourse] = []
    for predicate in _course_filters(course_hint, campus):
        matched = [c for c in courses if predicate(c)]
        if matched:
            break

    return matched[:limit]


def format_sigaa_context(courses: list[SigaaCourse], question: str = "") -> str:
    if not courses:
        return (
            "(SIGAA: nenhum curso encontrado com os filtros informados. "
            f"Lista completa: {SIGAA_CURSOS_URL})"
        )

    lines = [
        f"Fonte oficial SIGAA (graduação), atualizada periodicamente: {SIGAA_CURSOS_URL}",
        f"Registros encontrados: {len(courses)}",
        "",
    ]
    for i, c in enumerate(courses, start=1):
        block = (
            f"[SIGAA {i}] {c.nome}\n"
            f"  Sede: {c.sede}\n"
            f"  Modalidade: {c.modalidade}\n"
            f"  Coordenador(a): {c.coordenador}"
        )
        if c.campus_secao:
            block += f"\n  Unidade: {c.campus_secao}"
        lines.append(block)

    lines.append(
        "\nUse estes dados como fonte principal para coordenador, sede e modalidade."
    )
    return "\n".join(lines)


def get_sigaa_context_for_question(question: str) -> str | None:
    ctx = parse_academic_staff_context(question)
    q = question.lower()

    needs_sigaa = (
        ctx["is_course_staff"]
        or "curso" in q
        or "modalidade" in q
        or "sede" in q
        or "sigaa" in q
        or extract_course_hint(question)
        or extract_campus(question)
    )
    if not needs_sigaa:
        return None

    courses = search_courses(
        course_hint=ctx.get("course") or extract_course_hint(question),
        campus=ctx.get("campus") or extract_campus(question),
    )
    return format_sigaa_context(courses, question)


def refresh_cache() -> int:
    return len(load_courses(force_refresh=True))
