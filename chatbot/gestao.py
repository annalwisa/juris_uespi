"""Diretores(as) de centros acadêmicos e campi da UESPI (scrape da agenda telefônica oficial)."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import requests
from bs4 import BeautifulSoup

from chatbot.config import (
    GESTAO_AGENDA_URL,
    GESTAO_CACHE_HOURS,
    ROOT,
    SIGAA_SSL_VERIFY,
)

CACHE_DIR = ROOT / "data" / "cache"
CACHE_FILE = CACHE_DIR / "gestao_agenda.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; UESPI-Chatbot/1.0; +https://uespi.br) "
        "Educational assistant"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}

_GESTAO_KEYWORDS = (
    "diretor",
    "diretora",
    "direção",
    "direcao",
    "dirigente",
    "quem é o diretor",
    "quem e o diretor",
    "quem é a diretora",
    "quem e a diretora",
    "quem dirige",
    "nome do diretor",
    "nome da diretora",
)

_EXCLUDE_KEYWORDS = (
    "coordenador",
    "coordenadora",
    "coordenação",
    "coordenacao",
    "reitor",
    "reitoria",
    "pró-reitor",
    "pro-reitor",
    "proreitor",
    "vice-reitor",
    "diretor geral",
    "diretoria de",
    "diretoria do",
)

_CENTER_SIGLAS = ("cceca", "cchl", "ccn", "ccs", "ccsa", "ctu", "cca", "cies")

_COORD_KEYWORDS = ("coordenador", "coordenadora", "coordenacao", "coordenação")
_DIRETOR_KEYWORDS = ("diretor", "diretora", "direcao", "direção", "quem")

_CENTRO_SIGLA_RE = re.compile(r"^([A-Z]{2,5})\s*[-–—]\s*(.+)$", re.IGNORECASE)
_CARGO_RE = re.compile(
    r"^(Diretor(?:a)?|Coordenador(?:a)?)\s*:\s*(.+)$",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"([\w.+-]+@[\w.-]*uespi\.br)", re.IGNORECASE)
_PROF_PREFIX_RE = re.compile(
    r"^(?:Prof\.?|Profª\.?|Profº\.?|Dr\.?|Dra\.?|Esp\.?|Ms\.?|Me\.?)\s+",
    re.IGNORECASE,
)

# Metadados estáveis por subdomínio do e-mail direcao@ (nomes vêm do scrape).
_CAMPUS_BY_DOMAIN: dict[str, dict] = {
    "ccm": {
        "nome": "Campus Clóvis Moura",
        "cidade": "Teresina",
        "aliases": ["clovis moura", "ccm"],
    },
    "phb": {
        "nome": "Campus Prof. Alexandre Alves de Oliveira",
        "cidade": "Parnaíba",
        "aliases": ["parnaiba", "parnaíba", "phb"],
    },
    "prp": {
        "nome": "Campus Prof. Antônio Giovani Alves de Sousa",
        "cidade": "Piripiri",
        "aliases": ["piripiri", "prp"],
    },
    "cpm": {
        "nome": "Campus Heróis do Jenipapo",
        "cidade": "Campo Maior",
        "aliases": ["campo maior", "cpm", "herois do jenipapo", "heróis do jenipapo"],
    },
    "pcs": {
        "nome": "Campus Prof. Barros Araújo",
        "cidade": "Picos",
        "aliases": ["picos", "pcs"],
    },
    "ors": {
        "nome": "Campus Possidônio Queiroz",
        "cidade": "Oeiras",
        "aliases": ["oeiras", "ors"],
    },
    "frn": {
        "nome": "Campus Dra. Josefina Demes",
        "cidade": "Floriano",
        "aliases": ["floriano", "frn", "josefina demes"],
    },
    "srn": {
        "nome": "Campus Prof. Ariston Dias Lima",
        "cidade": "São Raimundo Nonato",
        "aliases": ["sao raimundo nonato", "são raimundo nonato", "srn"],
    },
    "urc": {
        "nome": "Campus Uruçuí",
        "cidade": "Uruçuí",
        "aliases": ["urucui", "uruçuí", "urc"],
    },
    "bjs": {
        "nome": "Campus Dom José Vasquez Dias",
        "cidade": "Bom Jesus",
        "aliases": ["bom jesus", "bjs"],
    },
    "cte": {
        "nome": "Campus Dep. Jesualdo Cavalcante",
        "cidade": "Corrente",
        "aliases": ["corrente", "cte"],
    },
}

_NUCLEO_META: dict[str, dict] = {
    "barras": {
        "cidade": "Barras",
        "campus_vinculado": "Campus Heróis do Jenipapo",
        "aliases": ["barras", "nucleo barras", "núcleo barras"],
    },
}

_CENTRO_CAMPUS = "Campus Poeta Torquato Neto"
_CENTRO_CIDADE = "Teresina"


@dataclass
class GestaoEntry:
    tipo: str
    nome: str = ""
    sigla: str = ""
    campus: str = ""
    cidade: str = ""
    cargo: str = ""
    nome_pessoa: str = ""
    email: str = ""
    telefone: str = ""
    campus_vinculado: str = ""
    aliases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _normalize(text: str) -> str:
    if not text:
        return ""
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def _clean_person_name(name: str) -> str:
    cleaned = _PROF_PREFIX_RE.sub("", name.strip())
    return re.sub(r"\s+", " ", cleaned).strip(" :.")


def _primary_email(text: str) -> str:
    emails = _EMAIL_RE.findall(text)
    for email in emails:
        if email.lower().startswith("direcao@"):
            return email
    return emails[0] if emails else ""


def _domain_key(email: str) -> str:
    if "@" not in email:
        return ""
    host = email.split("@", 1)[1].lower()
    return host.split(".", 1)[0]


def _centro_aliases(sigla: str, nome: str) -> list[str]:
    aliases = [sigla.lower(), _normalize(nome)]
    tokens = [t for t in re.split(r"[\s,]+", _normalize(nome)) if len(t) >= 5]
    aliases.extend(tokens[:4])
    return list(dict.fromkeys(a for a in aliases if a))


def _entry_dict(entry: GestaoEntry) -> dict:
    return entry.to_dict()


def _build_centro(sigla: str, nome: str, cargo: str, nome_pessoa: str, email: str) -> dict:
    entry = GestaoEntry(
        tipo="centro",
        sigla=sigla.upper(),
        nome=nome.strip(),
        campus=_CENTRO_CAMPUS,
        cidade=_CENTRO_CIDADE,
        cargo=cargo,
        nome_pessoa=nome_pessoa,
        email=email,
        aliases=_centro_aliases(sigla, nome),
    )
    return _entry_dict(entry)


def _build_campus(cargo: str, nome_pessoa: str, email: str) -> dict | None:
    key = _domain_key(email)
    meta = _CAMPUS_BY_DOMAIN.get(key)
    if not meta:
        return None
    entry = GestaoEntry(
        tipo="campus",
        nome=meta["nome"],
        cidade=meta["cidade"],
        cargo=cargo,
        nome_pessoa=nome_pessoa,
        email=email,
        aliases=list(meta.get("aliases", [])),
    )
    return _entry_dict(entry)


def _build_nucleo(
    titulo: str, cargo: str, nome_pessoa: str, email: str
) -> dict | None:
    key = _normalize(titulo)
    meta = _NUCLEO_META.get(key)
    if not meta:
        return None
    entry = GestaoEntry(
        tipo="nucleo",
        nome=f"Núcleo de {meta['cidade']}",
        cidade=meta["cidade"],
        cargo=cargo,
        nome_pessoa=nome_pessoa,
        email=email,
        campus_vinculado=meta.get("campus_vinculado", ""),
        aliases=list(meta.get("aliases", [])),
    )
    return _entry_dict(entry)


def _find_direcoes_section(soup: BeautifulSoup) -> list:
    elements = soup.find_all(["h2", "h4", "p"])
    start = None
    for i, el in enumerate(elements):
        if el.name != "h2":
            continue
        blob = _normalize(el.get_text(" ", strip=True))
        if "direcoes" in blob and "campi" in blob:
            start = i
            break
    if start is None:
        raise ValueError('Seção "Direções de Campi" não encontrada na agenda telefônica.')

    section: list = []
    for el in elements[start + 1 :]:
        if el.name == "h2":
            break
        section.append(el)
    return section


def parse_agenda_html(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    section = _find_direcoes_section(soup)

    centros: list[dict] = []
    campi: list[dict] = []
    nucleos: list[dict] = []

    current_centro: dict | None = None
    current_nucleo_title: str | None = None
    pending: dict | None = None

    for el in section:
        text = el.get_text(" ", strip=True)
        if not text:
            continue

        if el.name == "h4":
            match = _CENTRO_SIGLA_RE.match(text)
            if match:
                current_centro = {
                    "sigla": match.group(1).upper(),
                    "nome": match.group(2).strip(),
                }
                current_nucleo_title = None
            else:
                current_centro = None
                current_nucleo_title = text.strip()
            pending = None
            continue

        cargo_match = _CARGO_RE.match(text)
        if cargo_match:
            pending = {
                "cargo": cargo_match.group(1).strip(),
                "nome_pessoa": _clean_person_name(cargo_match.group(2)),
            }
            continue

        if pending and _EMAIL_RE.search(text):
            email = _primary_email(text)
            if not email:
                continue
            cargo = pending["cargo"]
            nome_pessoa = pending["nome_pessoa"]

            if current_centro:
                centros.append(
                    _build_centro(
                        current_centro["sigla"],
                        current_centro["nome"],
                        cargo,
                        nome_pessoa,
                        email,
                    )
                )
                current_centro = None
            elif current_nucleo_title:
                nucleo = _build_nucleo(current_nucleo_title, cargo, nome_pessoa, email)
                if nucleo:
                    nucleos.append(nucleo)
                current_nucleo_title = None
            elif centros:
                campus = _build_campus(cargo, nome_pessoa, email)
                if campus:
                    campi.append(campus)

            pending = None

    return {
        "fonte_agenda": GESTAO_AGENDA_URL,
        "centros": centros,
        "campi": campi,
        "nucleos": nucleos,
    }


def _fetch_agenda_html() -> str:
    response = requests.get(
        GESTAO_AGENDA_URL,
        headers=HEADERS,
        timeout=60,
        verify=SIGAA_SSL_VERIFY,
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def load_gestao_data(*, force_refresh: bool = False) -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if not force_refresh and CACHE_FILE.exists():
        try:
            payload = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            fetched = datetime.fromisoformat(payload["fetched_at"])
            if datetime.now(timezone.utc) - fetched < timedelta(hours=GESTAO_CACHE_HOURS):
                return {
                    "fonte_agenda": payload.get("fonte_agenda", GESTAO_AGENDA_URL),
                    "centros": payload.get("centros", []),
                    "campi": payload.get("campi", []),
                    "nucleos": payload.get("nucleos", []),
                }
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass

    data = parse_agenda_html(_fetch_agenda_html())
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "url": GESTAO_AGENDA_URL,
        **data,
    }
    CACHE_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return data


def refresh_cache() -> int:
    data = load_gestao_data(force_refresh=True)
    return len(data["centros"]) + len(data["campi"]) + len(data["nucleos"])


@lru_cache(maxsize=1)
def _load_data() -> dict:
    return load_gestao_data()


def clear_data_cache() -> None:
    _load_data.cache_clear()


def _sigla_in_question(question: str, sigla: str) -> bool:
    s = sigla.lower()
    q = _normalize(question)
    if len(s) <= 5:
        return bool(re.search(rf"\b{re.escape(s)}\b", q))
    return s in q


def _best_alias_match(question: str, entry: dict) -> tuple[int, dict] | None:
    q = _normalize(question)
    sigla = entry.get("sigla", "")
    if sigla and _sigla_in_question(question, sigla):
        return (len(sigla) + 10, entry)

    best: tuple[int, dict] | None = None
    candidates = [entry.get("nome", ""), entry.get("cidade", "")] + list(
        entry.get("aliases", [])
    )
    for alias in candidates:
        norm = _normalize(alias)
        if norm and norm in q:
            if best is None or len(norm) > best[0]:
                best = (len(norm), entry)
    return best


def _has_norm_keyword(blob: str, keywords) -> bool:
    return any(_normalize(k) in blob for k in keywords)


def _gestao_history_match(history: list | None) -> bool:
    if not history:
        return False

    from chatbot.history import _message_text

    for item in history[-4:]:
        parsed = _message_text(item)
        if parsed and parsed[1] and is_gestao_question(parsed[1]):
            return True
    return False


def is_gestao_question(question: str, history: list | None = None) -> bool:
    """Pergunta sobre diretor(a) de centro, campus ou núcleo (não coordenação de curso)."""
    blob = _normalize(question)
    has_gestao_kw = _has_norm_keyword(blob, _GESTAO_KEYWORDS)

    if _has_norm_keyword(blob, _EXCLUDE_KEYWORDS):
        if not has_gestao_kw:
            return False
        if any(k in blob for k in _COORD_KEYWORDS):
            return False

    if has_gestao_kw:
        return True

    if any(_sigla_in_question(question, s) for s in _CENTER_SIGLAS) and any(
        k in blob for k in _DIRETOR_KEYWORDS
    ):
        return True

    return _gestao_history_match(history)


def _find_centro(question: str) -> dict | None:
    best: tuple[int, dict] | None = None
    for entry in _load_data().get("centros", []):
        matched = _best_alias_match(question, entry)
        if matched and (best is None or matched[0] > best[0]):
            best = matched
    return best[1] if best else None


def _find_campus(question: str) -> dict | None:
    best: tuple[int, dict] | None = None
    for entry in _load_data().get("campi", []):
        matched = _best_alias_match(question, entry)
        if matched and (best is None or matched[0] > best[0]):
            best = matched
    return best[1] if best else None


def _find_nucleo(question: str) -> dict | None:
    best: tuple[int, dict] | None = None
    for entry in _load_data().get("nucleos", []):
        matched = _best_alias_match(question, entry)
        if matched and (best is None or matched[0] > best[0]):
            best = matched
    return best[1] if best else None


def _format_entry(entry: dict, *, tipo: str) -> str:
    cargo = entry.get("cargo", "Diretor(a)")
    nome = entry.get("nome_pessoa", "")
    sigla = entry.get("sigla", "")
    nome_unidade = entry.get("nome", "")
    campus = entry.get("campus", "")
    cidade = entry.get("cidade", "")
    email = entry.get("email", "")
    telefone = entry.get("telefone", "")

    if tipo == "centro":
        label = f"**{sigla}** — {nome_unidade}"
        if campus:
            label += f" ({campus}, {cidade})"
    elif tipo == "nucleo":
        label = f"**{nome_unidade}** ({cidade})"
        vinc = entry.get("campus_vinculado")
        if vinc:
            label += f" — vinculado ao {vinc}"
    else:
        label = f"**{nome_unidade}** ({cidade})"

    lines = [f"- {label}", f"  - {cargo}: **{nome}**"]
    if email:
        lines.append(f"  - E-mail: {email}")
    if telefone:
        lines.append(f"  - Telefone: {telefone}")
    return "\n".join(lines)


def _format_targeted_gestao(
    centro: dict | None,
    campus: dict | None,
    nucleo: dict | None,
    fonte_agenda: str,
) -> str:
    lines = [
        "## Gestão de centros e campi da UESPI (agenda telefônica oficial)",
        f"Fonte: [{fonte_agenda}]({fonte_agenda}) — seção Direções de Campi",
        "Use EXATAMENTE estes nomes. Não invente nem use PDFs antigos para cargos atuais.",
        "",
    ]
    if centro:
        lines.append(_format_entry(centro, tipo="centro"))
    if campus:
        lines.append(_format_entry(campus, tipo="campus"))
    if nucleo:
        lines.append(_format_entry(nucleo, tipo="nucleo"))
    lines.append(
        "\nObs.: **diretor(a) de centro/campus** é diferente de **coordenador(a) de curso** "
        "(consulte o SIGAA para coordenação)."
    )
    return "\n".join(lines)


def _format_full_gestao(data: dict, fonte_agenda: str) -> str:
    lines = [
        "## Gestão de centros e campi da UESPI (agenda telefônica oficial)",
        f"Fonte: [{fonte_agenda}]({fonte_agenda}) — seção Direções de Campi",
        "",
        "### Centros — Campus Poeta Torquato Neto (Teresina)",
    ]
    lines += [_format_entry(e, tipo="centro") for e in data.get("centros", [])]
    lines += ["", "### Direções de campi"]
    lines += [_format_entry(e, tipo="campus") for e in data.get("campi", [])]
    nucleos = data.get("nucleos", [])
    if nucleos:
        lines += ["", "### Núcleos"]
        lines += [_format_entry(e, tipo="nucleo") for e in nucleos]
    lines.append(
        "\nUse EXATAMENTE estes nomes. Não invente nem use PDFs antigos para cargos atuais."
    )
    return "\n".join(lines)


def format_gestao_context(question: str = "") -> str:
    data = _load_data()
    fonte_agenda = data.get("fonte_agenda", GESTAO_AGENDA_URL)

    centro = _find_centro(question)
    campus = _find_campus(question)
    nucleo = _find_nucleo(question)

    if centro or campus or nucleo:
        return _format_targeted_gestao(centro, campus, nucleo, fonte_agenda)
    return _format_full_gestao(data, fonte_agenda)


def get_gestao_context(question: str, history: list | None = None) -> str:
    if is_gestao_question(question, history):
        try:
            return format_gestao_context(question)
        except Exception as exc:
            return (
                f"(Erro ao consultar agenda telefônica da UESPI: {exc}. "
                f"Consulte {GESTAO_AGENDA_URL})"
            )
    return "(Não se aplica a esta pergunta.)"


def parse_gestao_context(question: str) -> dict:
    """Contexto para busca web direcionada."""
    centro = _find_centro(question)
    campus = _find_campus(question)
    nucleo = _find_nucleo(question)
    return {
        "is_gestao": is_gestao_question(question),
        "centro": centro,
        "campus": campus,
        "nucleo": nucleo,
    }
