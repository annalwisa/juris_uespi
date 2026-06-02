"""Jubilação / cancelamento da matrícula institucional na UESPI.

O termo coloquial "jubilação" / "ser jubilado" não aparece literalmente no
Regimento da UESPI; a hipótese formal correspondente é o **Cancelamento da
Matrícula Institucional** (Regimento, Art. 46) — e, para pós-graduação,
regras equivalentes nas resoluções da CEPEX/Consun.

Este módulo:
1. Detecta perguntas sobre "jubilação" (e suas variações).
2. Enriquece a query do RAG com os termos formais usados nos PDFs, para que
   a busca vetorial recupere os artigos certos (Art. 46 do Regimento, etc.).
3. Injeta um bloco de orientação no prompt para que o modelo:
   - Explique que "jubilação" na UESPI = Cancelamento da Matrícula Institucional.
   - Cite as hipóteses do Art. 46 (integralização, faltas de matrícula, exclusão).
   - Aponte para a coordenação do curso quando o caso for específico.
"""

from __future__ import annotations

import re
import unicodedata

JUBILACAO_KEYWORDS = (
    "jubila",
    "jubilamento",
    "jubilação",
    "jubilacao",
    "jubilado",
    "jubilada",
    "jubilar",
    "ser jubilad",
    "fui jubilad",
    "vou jubilar",
    "cancelamento de matricula institucional",
    "cancelamento da matricula institucional",
    "cancelamento de matrícula institucional",
    "cancelamento da matrícula institucional",
    "perder a vaga no curso",
    "perder o vínculo com a universidade",
    "perder o vinculo com a universidade",
    "prazo maximo para terminar",
    "prazo máximo para terminar",
    "prazo maximo do curso",
    "prazo máximo do curso",
    "tempo máximo de curso",
    "tempo maximo de curso",
    "estouro de prazo",
    "estourar o prazo",
    "expulso da universidade",
    "expulsa da universidade",
    "exclusao do curso",
    "exclusão do curso",
)


def _normalize(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def _matches(text: str, phrases: tuple[str, ...]) -> bool:
    n = _normalize(text)
    return any(_normalize(p) in n for p in phrases)


def is_jubilacao_question(question: str, history: list | None = None) -> bool:
    if _matches(question, JUBILACAO_KEYWORDS):
        return True
    if history:
        from chatbot.history import _message_text

        for item in history[-4:]:
            parsed = _message_text(item)
            if parsed and parsed[1] and _matches(parsed[1], JUBILACAO_KEYWORDS):
                return True
    return False


JUBILACAO_KNOWLEDGE = """## Jubilação na UESPI — termo formal e fontes

### Mapeamento de terminologia
- O termo coloquial **"jubilação"** / **"ser jubilado"** **não consta** no Regimento da UESPI com esse nome.
- A hipótese **formal** equivalente é o **Cancelamento da Matrícula Institucional**, regulado pelo **Art. 46 do Regimento Geral da UESPI**. Use sempre esse nome ao explicar e cite o artigo.

### Hipóteses do Art. 46 do Regimento (graduação)
A matrícula institucional **será cancelada** por iniciativa da Universidade ou do estudante quando:
- **I —** o estudante solicitar por escrito;
- **II —** em processo disciplinar, em última instância, for aplicada pena de exclusão;
- **III —** houver **impossibilidade de integralização curricular no prazo previsto no Projeto Político-Pedagógico do Curso (PPC)**;
- **IV —** o estudante estiver matriculado em mais de um curso de graduação na própria instituição;
- **V —** o aluno **não se matricular por mais de dois semestres letivos consecutivos ou três intercalados**.

### Pós-graduação e especializações
- **Stricto sensu (mestrado/doutorado):** regras de prazo, trancamento e cancelamento na **Resolução CEPEX 005/2021** (cursos stricto sensu).
- **Lato sensu (especializações):** regras equivalentes (cancelamento de registro) na **Resolução Consun 004/2022 — Especializações** (Art. 46).
- Cite a resolução correspondente quando a pergunta envolver pós-graduação.

### Como responder
1. Diga, com clareza: "Na UESPI, 'jubilação' corresponde ao **Cancelamento da Matrícula Institucional** previsto no **Art. 46 do Regimento**."
2. **Liste as hipóteses** (I a V) com base no Regimento, citando o artigo.
3. **Não invente prazos** específicos de integralização — eles dependem do PPC do curso. Indique que o estudante deve verificar o **PPC** com a coordenação do curso.
4. Para pós-graduação, cite a resolução correta (CEPEX 005/2021 para stricto sensu; Consun 004/2022 para especialização).
5. Em casos individuais (já passou do prazo, ficou sem se matricular etc.), oriente a procurar **a coordenação do curso** e, se necessário, a **PREG**, com o protocolo formal."""


def get_jubilacao_context(question: str, history: list | None = None) -> str:
    if is_jubilacao_question(question, history):
        return JUBILACAO_KNOWLEDGE
    return "(Não se aplica a esta pergunta.)"


def enhance_jubilacao_query(question: str, base_query: str) -> str:
    """Traduz o termo coloquial para os termos formais usados nos PDFs."""
    if not is_jubilacao_question(question):
        return base_query
    extras = [
        "Cancelamento da Matrícula Institucional Art. 46 Regimento UESPI",
        "integralização curricular prazo PPC",
        "matrícula institucional cancelada UESPI",
        "exclusão processo disciplinar estudante",
        "não se matricular semestres consecutivos intercalados",
    ]
    return f"{base_query} {' '.join(extras)}"
