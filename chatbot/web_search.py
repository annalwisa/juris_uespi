"""Busca externa (web) para dados atuais: reitoria, coordenação por campus, gestão."""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass

from langchain_core.documents import Document

from chatbot.campi import parse_academic_staff_context
from chatbot.gestao import parse_gestao_context
from chatbot.config import (
    TAVILY_API_KEY,
    UESPI_SITE,
    WEB_SEARCH_MAX_RESULTS,
    WEB_SEARCH_MODE,
)
from chatbot.metadata import STATUS_DESATUALIZADO

logger = logging.getLogger(__name__)

CURRENT_INFO_KEYWORDS = (
    "reitor",
    "reitoria",
    "pró-reitor",
    "pro-reitor",
    "proreitor",
    "vice-reitor",
    "gestão",
    "gestao",
    "diretor geral",
    "quem é o",
    "quem e o",
    "quem é a",
    "quem e a",
    "quem está",
    "nome do",
    "nome da",
    "atual",
    "hoje",
    "mandato",
    "exerce",
    "dirigente",
    "diretor",
    "diretora",
    "direção",
    "direcao",
    "chefe",
    "presidente",
    "contato do",
    "contato da",
    "e-mail do",
    "email do",
    "telefone do",
    "telefone da",
)

NORM_KEYWORDS = (
    "artigo",
    "art.",
    "resolução",
    "resolucao",
    "regimento",
    "lei ",
    "falta",
    "nota",
    "crédito",
    "credito",
    "estágio",
    "estagio",
    "tcc",
    "matrícula",
    "matricula",
    "aprovação",
    "reprovação",
    "carga horária",
    "stricto sensu",
    "lato sensu",
)

UESPI_DOMAIN = "uespi.br"


@dataclass
class WebResult:
    title: str
    snippet: str
    url: str


def web_search_enabled() -> bool:
    return WEB_SEARCH_MODE != "off"


def _normalize(text: str) -> str:
    return text.lower().strip()


def is_course_staff_question(question: str) -> bool:
    return parse_academic_staff_context(question)["is_course_staff"]


def is_leadership_or_current_info_question(question: str) -> bool:
    q = _normalize(question)
    if any(k in q for k in CURRENT_INFO_KEYWORDS):
        return True
    return is_course_staff_question(question)


def is_mostly_normative_question(question: str) -> bool:
    q = _normalize(question)
    if is_course_staff_question(question):
        return False
    return any(k in q for k in NORM_KEYWORDS) and not is_leadership_or_current_info_question(
        q
    )


def has_outdated_sources(docs: list[Document]) -> bool:
    return any(d.metadata.get("status") == STATUS_DESATUALIZADO for d in docs)


def should_search_web(question: str, rag_docs: list[Document]) -> bool:
    if not web_search_enabled():
        return False
    if WEB_SEARCH_MODE == "always":
        return True
    if is_leadership_or_current_info_question(question):
        return True
    if has_outdated_sources(rag_docs) and not is_mostly_normative_question(question):
        return True
    return False


def _course_staff_queries(
    course: str | None, campus: str | None
) -> tuple[str, list[str]]:
    """Query principal (prepend) + queries complementares (append)."""
    parts = ["UESPI", f"coordenador curso {course}" if course else "coordenador curso"]
    if campus:
        parts.append(f"campus {campus}")
    primary = " ".join(parts)

    if course and campus:
        extra = [
            f"UESPI {course} coordenação campus {campus} site:uespi.br",
            f"UESPI coordenador {course} {campus}",
        ]
    elif course:
        extra = [f"UESPI coordenação curso {course} site:uespi.br"]
    elif campus:
        extra = [
            f"UESPI cursos campus {campus} coordenador site:uespi.br",
            f"UESPI campus {campus} coordenação cursos",
        ]
    else:
        extra = []
    return primary, extra


def _leadership_queries(question: str) -> tuple[list[str], list[str]]:
    """(prepend, append) para perguntas sobre direção/reitoria."""
    gestao = parse_gestao_context(question)
    if gestao.get("centro"):
        centro = gestao["centro"]
        sigla = centro.get("sigla", "")
        nome = centro.get("nome", "")
        return [
            f"UESPI {sigla} {nome} diretor diretora site:uespi.br",
            f"UESPI {sigla} direção centro site:uespi.br",
        ], []
    if gestao.get("campus"):
        cidade = gestao["campus"].get("cidade", "")
        return [f"UESPI campus {cidade} diretor diretora site:uespi.br"], []
    return [], ["UESPI reitor atual", "UESPI reitoria pró-reitor"]


def _dedupe_preserving_order(queries: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for query in queries:
        key = query.lower()
        if key not in seen:
            seen.add(key)
            unique.append(query)
    return unique


def build_queries(question: str) -> list[str]:
    q = question.strip()
    base = [f"UESPI {q}", f"Universidade Estadual do Piauí {q}"]

    ctx = parse_academic_staff_context(question)
    if ctx["is_course_staff"]:
        primary, append = _course_staff_queries(ctx.get("course"), ctx.get("campus"))
        prepend = [primary]
    elif is_leadership_or_current_info_question(question):
        prepend, append = _leadership_queries(question)
    else:
        prepend, append = [], []

    return _dedupe_preserving_order(prepend + base + append)


def _prioritize_official(results: list[WebResult]) -> list[WebResult]:
    official = [r for r in results if UESPI_DOMAIN in r.url.lower()]
    other = [r for r in results if UESPI_DOMAIN not in r.url.lower()]
    return official + other


def _ddgs_client():
    try:
        from ddgs import DDGS

        return DDGS
    except ImportError:
        from duckduckgo_search import DDGS

        return DDGS


def _is_uespi_relevant(result: WebResult) -> bool:
    blob = f"{result.title} {result.snippet} {result.url}".lower()
    return UESPI_DOMAIN in result.url.lower() or "uespi" in blob


def _run_duckduckgo(query: str, max_results: int) -> list[WebResult]:
    DDGS = _ddgs_client()
    results: list[WebResult] = []
    seen_urls: set[str] = set()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        with DDGS(timeout=25) as ddgs:
            items = list(
                ddgs.text(
                    query,
                    region="br-pt",
                    safesearch="moderate",
                    max_results=max_results,
                )
            )

    for item in items:
        url = (item.get("href") or item.get("link") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        results.append(
            WebResult(
                title=(item.get("title") or "").strip(),
                snippet=(item.get("body") or item.get("snippet") or "").strip(),
                url=url,
            )
        )
    return results


def _run_tavily(question: str, max_results: int) -> list[WebResult]:
    try:
        from tavily import TavilyClient
    except ImportError as e:
        raise ImportError("Instale tavily-python: pip install tavily-python") from e

    ctx = parse_academic_staff_context(question)
    query = f"UESPI {question}"
    if ctx["is_course_staff"] and ctx.get("campus"):
        query = f"UESPI coordenador curso {ctx.get('course') or ''} campus {ctx['campus']}"

    client = TavilyClient(api_key=TAVILY_API_KEY)
    response = client.search(
        query=query.strip(),
        search_depth="basic",
        max_results=max_results,
        include_domains=[UESPI_DOMAIN, "www.uespi.br"],
    )
    results: list[WebResult] = []
    for item in response.get("results", []):
        results.append(
            WebResult(
                title=item.get("title", ""),
                snippet=item.get("content", ""),
                url=item.get("url", ""),
            )
        )
    return results


def _add_unique(
    results: list[WebResult],
    combined: list[WebResult],
    seen: set[str],
    cap: int | None = None,
) -> bool:
    """Acrescenta resultados inéditos (por URL). True quando atinge ``cap``."""
    for r in results:
        if r.url not in seen:
            seen.add(r.url)
            combined.append(r)
        if cap is not None and len(combined) >= cap:
            return True
    return False


def _finalize_results(combined: list[WebResult], max_results: int) -> list[WebResult]:
    combined = _prioritize_official(combined)
    relevant = [r for r in combined if _is_uespi_relevant(r)]
    if relevant:
        combined = relevant
    return combined[:max_results]


def _tavily_results(question: str, max_results: int) -> list[WebResult] | None:
    """Resultados do Tavily, ou ``None`` se indisponível/falho/vazio (faz fallback)."""
    if not TAVILY_API_KEY:
        return None
    try:
        batch = _run_tavily(question, max_results)
    except Exception:
        logger.warning(
            "Busca Tavily falhou; usando DuckDuckGo como fallback.", exc_info=True
        )
        return None

    combined: list[WebResult] = []
    _add_unique(batch, combined, seen=set())
    if not combined:
        return None
    return _finalize_results(combined, max_results)


def _duckduckgo_results(
    question: str, max_results: int, per_query: int
) -> list[WebResult]:
    combined: list[WebResult] = []
    seen: set[str] = set()
    for query in build_queries(question):
        try:
            batch = _run_duckduckgo(query, per_query)
        except Exception:
            logger.debug(
                "Busca DuckDuckGo falhou para a query %r.", query, exc_info=True
            )
            continue
        _add_unique(batch, combined, seen, cap=max_results * 2)
        if len(combined) >= max_results:
            break
    return _finalize_results(combined, max_results)


def search_uespi_web(question: str) -> list[WebResult]:
    ctx = parse_academic_staff_context(question)
    max_results = WEB_SEARCH_MAX_RESULTS + (2 if ctx["is_course_staff"] else 0)
    per_query = max(2, max_results // 2)

    tavily = _tavily_results(question, max_results)
    if tavily is not None:
        return tavily

    return _duckduckgo_results(question, max_results, per_query)


def format_web_context(results: list[WebResult], question: str = "") -> str:
    if not results:
        ctx = parse_academic_staff_context(question) if question else {}
        hint = ""
        if ctx.get("is_course_staff"):
            hint = (
                " Para coordenadores por campus, veja a página do curso ou campus em "
                f"{UESPI_SITE} (menu Cursos / Unidades)."
            )
        return (
            "(Nenhum resultado de busca web obtido."
            f"{hint} PDFs antigos podem listar nomes desatualizados.)"
        )

    parts = []
    for i, r in enumerate(results, start=1):
        tag = "oficial UESPI" if UESPI_DOMAIN in r.url.lower() else "web"
        parts.append(f"[{tag} {i}] {r.title}\nURL: {r.url}\n{r.snippet}")
    return "\n\n---\n\n".join(parts)
