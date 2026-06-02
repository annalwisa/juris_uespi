"""Estágio supervisionado na UESPI: normas, convênio e empresas conveniadas.

Agrupa as fontes oficiais que o modelo deve usar para responder perguntas sobre
estágio (Lei 11.788/2008, Resolução CEPEX 004/2021, Portaria 329/2020 e o
procedimento de abertura de convênio do DAP/DES), além das URLs públicas da
DES e da planilha de instituições conveniadas pela UESPI.
"""

from __future__ import annotations

import re
import unicodedata

from chatbot.config import (
    DES_NOME,
    ESTAGIO_CONVENIADAS_PLANILHA_URL,
    ESTAGIO_CONVENIO_EMAIL,
    ESTAGIO_DAP_EMAIL,
    ESTAGIO_DAP_TELEFONE,
    ESTAGIO_DES_URL,
    PREG_NOME,
)

ESTAGIO_KEYWORDS = (
    "estagio",
    "estágio",
    "estagios",
    "estágios",
    "estagiar",
    "estagiário",
    "estagiaria",
    "estagiária",
    "estagiarios",
    "estagiários",
    "estagiarias",
    "estagiárias",
    "supervisionado",
    "supervisionada",
    "convenio",
    "convênio",
    "convenios",
    "convênios",
    "conveniada",
    "conveniadas",
    "conveniado",
    "conveniados",
    "termo de compromisso",
    "parte concedente",
    "concedente",
    "lei do estagio",
    "lei do estágio",
    "lei 11.788",
    "lei 11788",
    "11.788",
    "residencia pedagogica",
    "residência pedagógica",
    "preg",
    "dap",
    "des ",
    " des",
    "preg-dap-des",
    "abrir convenio",
    "abrir convênio",
    "empresa conveniada",
    "instituicao conveniada",
    "instituição conveniada",
    "instituicoes conveniadas",
    "instituições conveniadas",
)

CONVENIO_KEYWORDS = (
    "convenio",
    "convênio",
    "conveniad",
    "abrir convenio",
    "abrir convênio",
    "como conveniar",
    "se conveniar",
    "termo de convenio",
    "termo de convênio",
    "empresa conveniada",
    "instituicao conveniada",
    "instituição conveniada",
    "instituicoes conveniadas",
    "instituições conveniadas",
)


def _normalize(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def _matches(text: str, phrases: tuple[str, ...]) -> bool:
    n = _normalize(text)
    return any(_normalize(p) in n for p in phrases)


def is_estagio_question(question: str, history: list | None = None) -> bool:
    if _matches(question, ESTAGIO_KEYWORDS):
        return True
    if history:
        from chatbot.history import _message_text

        for item in history[-6:]:
            parsed = _message_text(item)
            if parsed and parsed[1] and _matches(parsed[1], ESTAGIO_KEYWORDS):
                return True
    return False


def is_convenio_question(question: str, history: list | None = None) -> bool:
    if _matches(question, CONVENIO_KEYWORDS):
        return True
    if history:
        from chatbot.history import _message_text

        for item in history[-4:]:
            parsed = _message_text(item)
            if parsed and parsed[1] and _matches(parsed[1], CONVENIO_KEYWORDS):
                return True
    return False


ESTAGIO_KNOWLEDGE = f"""## Estágio supervisionado na UESPI

### Fontes oficiais a citar nas respostas
- **Lei nº 11.788/2008** — Lei Federal do Estágio (define estágio obrigatório/não obrigatório, jornada, termo de compromisso, seguro, recesso). PDF indexado: `LEI_11788-Lei-do-Estagio.pdf`.
- **Resolução CEPEX 004/2021 (UESPI)** — regulamenta os estágios dos cursos de **graduação** da UESPI (objetivos, modalidades, coordenação, avaliação). PDF indexado: `RESOLUCAO-ESTAGIO.pdf`.
- **Portaria 329/2020 (PREG/UESPI)** — aproveitamento da carga horária da **Residência Pedagógica (CAPES)** como Estágio Curricular Obrigatório, conforme Edital CAPES 001/2020. PDF indexado: `PORTARIA.pdf`.
- **Procedimento para abertura de convênio (PREG/DAP/DES)** — passo a passo para empresas/órgãos que querem firmar convênio de estágio com a UESPI. PDF indexado: `Procedimentos-para-Abertura-de-Convenio2.pdf`.

### Página oficial e setores responsáveis
- **{PREG_NOME}** — política de ensino de graduação.
- **{DES_NOME}** — operacionaliza convênios, termos de compromisso e acompanhamento.
- **Página oficial da DES:** {ESTAGIO_DES_URL}
- **E-mail para abrir convênio:** {ESTAGIO_CONVENIO_EMAIL}
- **E-mail DAP:** {ESTAGIO_DAP_EMAIL}
- **Telefone DAP:** {ESTAGIO_DAP_TELEFONE}

### Instituições conveniadas (lista oficial)
- **Planilha pública mantida pela PREG** com todas as instituições/empresas conveniadas, ano de abertura, validade, situação (vigente/vencido), município e contato:
  {ESTAGIO_CONVENIADAS_PLANILHA_URL}
- Quando o usuário perguntar se uma empresa específica é conveniada, **oriente a consultar essa planilha** (não cite nomes específicos de empresas sem a fonte). Se a planilha não estiver acessível na conversa, peça que o usuário a abra ou entre em contato com a DES.

### Como responder
1. Para perguntas sobre **regras** (jornada, carga horária, obrigatoriedade, seguro, recesso, termo de compromisso): use a **Lei 11.788/2008** + a **Resolução CEPEX 004/2021**; cite o artigo quando possível.
2. Para perguntas sobre **abrir convênio** (empresa/órgão querendo receber estagiário): siga o procedimento do PDF `Procedimentos-para-Abertura-de-Convenio2.pdf` e indique o e-mail {ESTAGIO_CONVENIO_EMAIL} e a página {ESTAGIO_DES_URL}.
3. Para perguntas sobre **Residência Pedagógica e aproveitamento de carga horária**: use a Portaria 329/2020.
4. Para perguntas sobre **instituições já conveniadas**: indique a planilha oficial e oriente filtrar pelo município/situação.
5. Se a pergunta envolver caso específico (curso, situação acadêmica do aluno, valor da bolsa do estagiário), oriente contato com a **coordenação do curso** e com a **DES** ({ESTAGIO_DAP_EMAIL}).
6. Não invente nomes de empresas, datas de validade ou contatos — sempre remeta à planilha oficial."""


def get_estagio_context(question: str, history: list | None = None) -> str:
    """Bloco de contexto sobre estágio para o RAG_PROMPT.

    Retorna o conhecimento completo quando a pergunta é sobre estágio/convênio;
    caso contrário retorna uma marca neutra.
    """
    if is_estagio_question(question, history):
        return ESTAGIO_KNOWLEDGE
    return "(Não se aplica a esta pergunta.)"


def enhance_estagio_query(question: str, base_query: str) -> str:
    """Enriquece a busca nos PDFs de estágio quando o tema é detectado."""
    if not is_estagio_question(question):
        return base_query

    extras = [
        "Lei 11.788 estágio",
        "Resolução CEPEX 004 2021 UESPI estágio",
        "estágio supervisionado obrigatório não obrigatório",
        "termo de compromisso parte concedente",
    ]
    if is_convenio_question(question):
        extras.extend(
            [
                "convênio empresa UESPI DAP DES procedimento",
                "abrir convênio Termo de Convênio assinatura",
                "Procedimentos-para-Abertura-de-Convenio",
                "instituições conveniadas planilha PREG",
            ]
        )
    return f"{base_query} {' '.join(extras)}"
