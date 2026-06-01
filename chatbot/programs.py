"""Programas de bolsas e iniciação (PIBIC, PIBIT, PIBEU) na UESPI."""

from __future__ import annotations

import re
import unicodedata

from chatbot.config import PROP_NOME, SIGPROP_PESQUISA_URL

PROGRAM_KEYWORDS = (
    "pibic",
    "pibit",
    "pibiti",
    "pibeu",
    "sigprop",
    "prop ",
    "iniciação científica",
    "iniciacao cientifica",
    "iniciação tecnológica",
    "iniciacao tecnologica",
    "iniciação em desenvolvimento tecnológico",
    "iniciação em extensão",
    "iniciacao em extensao",
    "bolsa de iniciação",
    "bolsa de iniciacao",
    "bolsas de iniciação",
    "valor da bolsa",
    "valor bolsa",
    "vigência",
    "vigencia",
    "edital pibic",
    "edital pibit",
    "edital pibeu",
    "programa institucional de bolsas",
)

PROGRAMS_KNOWLEDGE = f"""## Programas PIBIC, PIBIT e PIBEU na UESPI

### Diferença entre os programas
| Programa | Eixo principal |
|----------|----------------|
| **PIBIC** | Iniciação à **pesquisa científica** (projeto com orientador pesquisador) |
| **PIBIT** (ou PIBITI no edital) | Iniciação em **desenvolvimento tecnológico e inovação** |
| **PIBEU** | Iniciação em **extensão universitária** (projetos com a sociedade) |

### Onde estão valor da bolsa, vigência e condições
- **PIBIC e PIBIT:** edital indexado `Edital_009_2026_PROP_UESPI-PIBIC-PIBITI.pdf` (PROP/UESPI, 2026).
- **PIBEU:** edital indexado `SEI_GOV-PI-017643752-EditalPIBEU.pdf`.
- Para **valores, prazos de vigência, requisitos e cronograma**, cite o trecho do edital correspondente nos documentos recuperados — não invente valores.

### Sistema e responsabilidade institucional
- **{PROP_NOME}** é a pró-reitoria responsável pelos programas de pesquisa e pelos editais PIBIC/PIBIT.
- **SIGPROP (módulo pesquisa):** {SIGPROP_PESQUISA_URL}  
  Use este sistema para cadastro/submissão de projetos de **pesquisa** conforme orientações da PROP e do edital vigente.
- Dúvidas operacionais: contate a **PROP** da UESPI e consulte o edital do programa.

### Como responder
1. Explique a diferença entre os programas se o usuário perguntar.
2. Para **valor, vigência e condições**, priorize os PDFs dos editais acima.
3. Indique o **SIGPROP** quando a pergunta envolver envio ou modelo de projeto de pesquisa.
4. Se o edital indexado não trouxer o dado, diga que não encontrou no documento e oriente a PROP/site oficial."""


def _normalize(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def is_programs_question(question: str, history: list | None = None) -> bool:
    blob = _normalize(question)
    if any(k in blob for k in PROGRAM_KEYWORDS):
        return True
    if history:
        from chatbot.history import _message_text

        for item in history[-6:]:
            parsed = _message_text(item)
            if parsed and parsed[1]:
                h = _normalize(parsed[1])
                if any(k in h for k in PROGRAM_KEYWORDS):
                    return True
    return False


def enhance_retrieval_query(question: str, base_query: str) -> str:
    """Enriquece busca nos PDFs dos editais PIBIC/PIBIT/PIBEU."""
    if not is_programs_question(question):
        return base_query
    return (
        f"{base_query} Edital_009_2026 PIBIC PIBIT PIBEU bolsa valor vigência "
        f"condições PROP edital extensão"
    )


def get_programs_context(question: str, history: list | None = None) -> str:
    if is_programs_question(question, history):
        return PROGRAMS_KNOWLEDGE
    return "(Não se aplica a esta pergunta.)"
