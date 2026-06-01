"""Respostas fixas para perguntas frequentes (sem chamar o modelo — resposta rápida)."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import yaml

from chatbot.alerts import ABSENCE_ALERT
from chatbot.citations import regimento_link_markdown
from chatbot.config import PROP_NOME, ROOT, SIGPROP_PESQUISA_URL

FAQ_CONFIG_PATH = ROOT / "data" / "faq_respostas.yaml"

_DEFAULTS = {
    "bolsa_pesquisa_monitoria_reais": 700,
    "faltas_percentual_maximo": 25,
    "frequencia_minima_percentual": 75,
}


def _load_config() -> dict:
    if not FAQ_CONFIG_PATH.exists():
        return {"faqs": {}, **_DEFAULTS}
    with FAQ_CONFIG_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    for key, val in _DEFAULTS.items():
        data.setdefault(key, val)
    data.setdefault("faqs", {})
    return data


def _normalize(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def _matches_any(text: str, phrases: list[str]) -> bool:
    n = _normalize(text)
    return any(_normalize(p) in n for p in phrases)


def _counts_in_days(question: str) -> bool:
    """Usuário falou em dias de ausência, não em faltas do boletim."""
    return bool(re.search(r"\bdias?\b", _normalize(question)))


def is_faltas_scenario_question(question: str) -> bool:
    """Pergunta com quantidade ou hipótese — não repetir FAQ genérico."""
    n = _normalize(question)
    topic = (
        "falta",
        "faltar",
        "frequencia",
        "frequência",
        "presenca",
        "presença",
        "ausencia",
        "ausência",
        "comparec",
    )
    if not any(k in n for k in topic) and not re.search(r"\bdias?\b", n):
        return False
    if re.search(r"\b\d{1,3}\b", n):
        return True
    if re.search(r"\be se\b", n):
        return True
    return any(
        p in n
        for p in (
            "quantas vezes",
            "ja faltei",
            "já faltei",
            "vou reprovar",
            "passo de",
            "estou no limite",
        )
    )


def _extract_absence_count(question: str) -> int | None:
    m = re.search(r"\b(\d{1,3})\b", _normalize(question))
    return int(m.group(1)) if m else None


def _status_for_count(count: int, max_f: int) -> str:
    if count <= max_f:
        return "dentro do limite (em regra, não reprova só por essa contagem)"
    return "acima do limite — risco de reprovação por falta"


def _examples_table(counts: list[int], pct: int) -> str:
    lines: list[str] = []
    for ch in (80, 60, 40, 32):
        max_f = int(ch * pct / 100)
        parts = [f"- CH **{ch} h** → até **~{max_f}** faltas no registro:"]
        for c in counts:
            parts.append(f"**{c}** faltas → **{_status_for_count(c, max_f)}**")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def _response_faltas_scenario_days(days: int, cfg: dict) -> str:
    pct = cfg["faltas_percentual_maximo"]
    freq = cfg["frequencia_minima_percentual"]
    reg = regimento_link_markdown()
    reg_min, reg_max = days, days * 2

    return f"""Você perguntou sobre **{days} dias** sem comparecer. O limite do Regimento da UESPI é calculado sobre as **faltas registradas no SIGAA** (em geral, até **{pct}%** da carga horária da disciplina — mínimo **{freq}%** de frequência), **não sobre o número de dias** que você faltou.

**{days} dias** podem equivaler a:
- **~{reg_min} faltas** no boletim, se a disciplina tem **uma aula** por dia de encontro;
- **até ~{reg_max} faltas**, se há **duas aulas no mesmo dia** e cada ausência gera dois registros.

**O que fazer:** abra o registro da disciplina no SIGAA, some as **faltas lançadas** e compare com **{pct}% × CH** (não use só a contagem de dias).

**Exemplos** (substitua pela CH real da sua disciplina):

{_examples_table([reg_min, reg_max], pct)}

{ABSENCE_ALERT}

Artigos e exceções: {reg} ou a coordenação do seu curso."""


def _response_faltas_scenario_registered(count: int, cfg: dict) -> str:
    pct = cfg["faltas_percentual_maximo"]
    freq = cfg["frequencia_minima_percentual"]
    reg = regimento_link_markdown()

    return f"""Com **{count} faltas** no registro acadêmico (como aparecem no SIGAA), **não dá para afirmar** se você reprova sem a **carga horária (CH)** da disciplina. Pelo Regimento da UESPI, em geral é preciso **no mínimo {freq}%** de frequência (até **{pct}%** de faltas sobre a CH).

**Como calcular:** máximo de faltas permitidas ≈ **{pct}% × CH** da disciplina (confira no SIGAA ou com a coordenação).

**Exemplos** (substitua pela CH real da sua disciplina):

{_examples_table([count], pct)}

{ABSENCE_ALERT}

Artigos e exceções: {reg} ou a coordenação do seu curso."""


def _response_faltas_scenario(question: str, cfg: dict) -> str | None:
    count = _extract_absence_count(question)
    if count is None:
        return None

    if _counts_in_days(question):
        return _response_faltas_scenario_days(count, cfg)
    return _response_faltas_scenario_registered(count, cfg)


def _response_faltas(cfg: dict) -> str:
    pct = cfg["faltas_percentual_maximo"]
    freq = cfg["frequencia_minima_percentual"]
    return f"""O **número máximo de faltas** para não ser reprovado por frequência é de **{pct}%** da carga horária da disciplina — ou seja, é necessário ter no mínimo **{freq}%** de frequência (conforme Regimento da UESPI).

{ABSENCE_ALERT}

Para o artigo exato e exceções, consulte o {regimento_link_markdown()} ou a coordenação do seu curso."""


def _response_bolsa(cfg: dict) -> str:
    valor = cfg["bolsa_pesquisa_monitoria_reais"]
    return f"""O valor da bolsa de **pesquisa** (programas como PIBIC/PIBIT, conforme edital vigente) e de **monitoria** na UESPI é de **R$ {valor},00** mensais, salvo disposição diferente em edital específico.

- **Editais PIBIC/PIBIT:** `Edital_009_2026_PROP_UESPI-PIBIC-PIBITI.pdf`
- **Edital PIBEU:** `SEI_GOV-PI-017643752-EditalPIBEU.pdf`
- **Edital de monitorias:** `Edita-de-Monitorias.pdf`
- **Cadastro de projetos de pesquisa (SIGPROP):** {SIGPROP_PESQUISA_URL} — {PROP_NOME}

Para vigência, cronograma e requisitos detalhados, consulte o edital do programa."""


_FAQ_HANDLERS = {
    "faltas": _response_faltas,
    "bolsa_valor": _response_bolsa,
}


def is_monitoria_detail_question(question: str) -> bool:
    """Perguntas sobre monitoria que precisam do edital (não só valor fixo no FAQ)."""
    n = _normalize(question)
    if "monitoria" not in n:
        return False
    valor_only = any(
        p in n
        for p in (
            "valor",
            "quanto paga",
            "quanto e",
            "quanto é",
            "700",
            "remuneracao",
            "remuneração",
        )
    )
    detail = any(
        p in n
        for p in (
            "edital",
            "inscricao",
            "inscrição",
            "requisito",
            "prazo",
            "vigencia",
            "vigência",
            "como funciona",
            "selecao",
            "seleção",
            "carga horaria",
            "carga horária",
        )
    )
    return detail or not valor_only


def get_faq_response(question: str, history: list | None = None) -> str | None:
    """
    Retorna resposta fixa se a pergunta corresponder a um FAQ configurado.
    Histórico é considerado apenas para follow-ups curtos sobre o mesmo tema.
    """
    cfg = _load_config()
    faqs = cfg.get("faqs", {})

    if is_faltas_scenario_question(question):
        scenario = _response_faltas_scenario(question, cfg)
        if scenario:
            return scenario
        return None

    blob = question
    if history and not is_faltas_scenario_question(question):
        from chatbot.history import _message_text

        recent_user = []
        for item in history[-4:]:
            parsed = _message_text(item)
            if parsed and parsed[0] == "user" and parsed[1]:
                recent_user.append(parsed[1])
        # Só enriquece follow-ups muito curtos («e o valor?»), não cenários com número
        if recent_user and len(_normalize(question).split()) <= 4:
            blob = f"{' '.join(recent_user[-2:])} {question}"

    # Ordem: faltas antes de bolsa se ambos puderem coincidir
    for faq_id in ("faltas", "bolsa_valor"):
        phrases = faqs.get(faq_id, [])
        if phrases and _matches_any(blob, phrases):
            handler = _FAQ_HANDLERS.get(faq_id)
            if handler:
                return handler(cfg)

    return None
