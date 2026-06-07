"""Avaliação do RAG do JurisUESPI.

Implementa quatro métricas inspiradas no framework RAGAS (Es et al., 2023),
exatamente as descritas na Seção 2.4 do projeto:

- **Context Precision@K** — qualidade/ordenação dos trechos recuperados.
- **Context Recall** — cobertura dos trechos frente à resposta de referência.
- **Faithfulness (fidelidade)** — a resposta é sustentada pelos trechos?
- **Answer Relevancy** — a resposta responde à pergunta feita?

As três primeiras usam o modelo de chat como juiz (LLM-as-judge); a última usa
embeddings. Tudo reutiliza as chaves/modelos já configurados no projeto, sem
depender de bibliotecas externas de avaliação (o que evita problemas de versão
e mantém o cálculo auditável para o TCC).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from chatbot.config import CHAT_MODEL, EMBEDDING_MODEL, OPENAI_API_KEY

# Número de perguntas geradas a partir da resposta no cálculo de answer relevancy.
ANSWER_RELEVANCY_N = 3


# --------------------------------------------------------------------------- #
# Infraestrutura: juiz LLM, embeddings e parsing robusto de JSON
# --------------------------------------------------------------------------- #
def _judge_llm() -> ChatOpenAI:
    # Temperatura 0 para julgamentos determinísticos e reprodutíveis.
    return ChatOpenAI(model=CHAT_MODEL, api_key=OPENAI_API_KEY, temperature=0)


def _embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=OPENAI_API_KEY)


def _ask_json(prompt: str) -> dict | list:
    """Chama o LLM e devolve o JSON da resposta, tolerando texto ao redor."""
    raw = _judge_llm().invoke(prompt).content
    if isinstance(raw, list):  # alguns modelos retornam lista de partes
        raw = "".join(part if isinstance(part, str) else "" for part in raw)
    raw = str(raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Fallback: extrai o primeiro objeto/array JSON do texto.
    match = re.search(r"(\{.*\}|\[.*\])", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return {}


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _contexts_text(contexts: list[str]) -> str:
    return "\n\n".join(f"[{i}] {c}" for i, c in enumerate(contexts, start=1))


def _decompose_statements(text: str) -> list[str]:
    """Quebra um texto em afirmações atômicas (uma ideia verificável por item)."""
    if not text or not text.strip():
        return []
    prompt = (
        "Decomponha o TEXTO abaixo em afirmações atômicas, ou seja, frases curtas "
        "e independentes, cada uma contendo uma única informação verificável. "
        "Responda APENAS em JSON no formato {\"statements\": [\"...\", \"...\"]}.\n\n"
        f"TEXTO:\n{text}"
    )
    data = _ask_json(prompt)
    items = data.get("statements", []) if isinstance(data, dict) else []
    return [s.strip() for s in items if isinstance(s, str) and s.strip()]


# --------------------------------------------------------------------------- #
# Métricas
# --------------------------------------------------------------------------- #
def faithfulness(answer: str, contexts: list[str]) -> float:
    """Fração das afirmações da resposta que podem ser inferidas dos trechos."""
    statements = _decompose_statements(answer)
    if not statements:
        return 0.0
    if not contexts:
        return 0.0

    prompt = (
        "Você é um avaliador rigoroso. Dado o CONTEXTO e uma lista de AFIRMAÇÕES, "
        "decida, para cada afirmação, se ela pode ser inferida/sustentada DIRETAMENTE "
        "pelo contexto (1) ou não (0). Não use conhecimento externo.\n"
        "Responda APENAS em JSON: {\"verdicts\": [0 ou 1, ...]} na mesma ordem.\n\n"
        f"CONTEXTO:\n{_contexts_text(contexts)}\n\n"
        f"AFIRMAÇÕES:\n{json.dumps(statements, ensure_ascii=False)}"
    )
    data = _ask_json(prompt)
    verdicts = data.get("verdicts", []) if isinstance(data, dict) else []
    verdicts = [int(v) for v in verdicts if v in (0, 1, "0", "1")]
    if not verdicts:
        return 0.0
    return sum(verdicts) / len(statements)


def context_recall(ground_truth: str, contexts: list[str]) -> float:
    """Fração das afirmações da resposta de referência cobertas pelos trechos."""
    statements = _decompose_statements(ground_truth)
    if not statements:
        return 0.0
    if not contexts:
        return 0.0

    prompt = (
        "Dado o CONTEXTO e uma lista de AFIRMAÇÕES extraídas de uma resposta de "
        "referência, decida, para cada afirmação, se ela pode ser atribuída ao "
        "contexto (1) ou não (0). Não use conhecimento externo.\n"
        "Responda APENAS em JSON: {\"verdicts\": [0 ou 1, ...]} na mesma ordem.\n\n"
        f"CONTEXTO:\n{_contexts_text(contexts)}\n\n"
        f"AFIRMAÇÕES:\n{json.dumps(statements, ensure_ascii=False)}"
    )
    data = _ask_json(prompt)
    verdicts = data.get("verdicts", []) if isinstance(data, dict) else []
    verdicts = [int(v) for v in verdicts if v in (0, 1, "0", "1")]
    if not verdicts:
        return 0.0
    return sum(verdicts) / len(statements)


def context_precision(question: str, contexts: list[str], ground_truth: str) -> float:
    """Average Precision@K sobre a relevância de cada trecho na ordem recuperada.

    Mede se os trechos realmente úteis aparecem nas primeiras posições.
    """
    if not contexts:
        return 0.0

    prompt = (
        "Dada a PERGUNTA e a RESPOSTA DE REFERÊNCIA, avalie cada TRECHO recuperado "
        "e diga se ele é útil/relevante para responder à pergunta (1) ou não (0).\n"
        "Responda APENAS em JSON: {\"relevances\": [0 ou 1, ...]} na ordem dos trechos.\n\n"
        f"PERGUNTA: {question}\n\n"
        f"RESPOSTA DE REFERÊNCIA: {ground_truth}\n\n"
        f"TRECHOS:\n{_contexts_text(contexts)}"
    )
    data = _ask_json(prompt)
    rels = data.get("relevances", []) if isinstance(data, dict) else []
    rels = [1 if str(v) == "1" else 0 for v in rels][: len(contexts)]
    if not rels or sum(rels) == 0:
        return 0.0

    # Average Precision: média das precisões @k nas posições relevantes.
    hits = 0
    precision_sum = 0.0
    for k, rel in enumerate(rels, start=1):
        if rel:
            hits += 1
            precision_sum += hits / k
    return precision_sum / sum(rels)


def answer_relevancy(question: str, answer: str, n: int = ANSWER_RELEVANCY_N) -> float:
    """Similaridade média entre a pergunta original e perguntas geradas da resposta."""
    if not answer or not answer.strip():
        return 0.0
    prompt = (
        f"Gere {n} perguntas distintas que sejam plenamente respondidas pela "
        "RESPOSTA abaixo. As perguntas devem ser específicas e em português.\n"
        "Responda APENAS em JSON: {\"questions\": [\"...\"]}\n\n"
        f"RESPOSTA:\n{answer}"
    )
    data = _ask_json(prompt)
    generated = data.get("questions", []) if isinstance(data, dict) else []
    generated = [q.strip() for q in generated if isinstance(q, str) and q.strip()]
    if not generated:
        return 0.0

    emb = _embeddings()
    vectors = emb.embed_documents([question] + generated)
    q_vec, gen_vecs = vectors[0], vectors[1:]
    sims = [_cosine(q_vec, g) for g in gen_vecs]
    return sum(sims) / len(sims) if sims else 0.0


# --------------------------------------------------------------------------- #
# Execução sobre um dataset
# --------------------------------------------------------------------------- #
@dataclass
class SampleResult:
    question: str
    answer: str
    contexts: list[str]
    context_precision: float
    context_recall: float
    faithfulness: float
    answer_relevancy: float


@dataclass
class EvaluationReport:
    samples: list[SampleResult] = field(default_factory=list)

    def _mean(self, attr: str) -> float:
        if not self.samples:
            return 0.0
        return sum(getattr(s, attr) for s in self.samples) / len(self.samples)

    @property
    def averages(self) -> dict[str, float]:
        return {
            "context_precision": self._mean("context_precision"),
            "context_recall": self._mean("context_recall"),
            "faithfulness": self._mean("faithfulness"),
            "answer_relevancy": self._mean("answer_relevancy"),
        }


def evaluate_sample(
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str,
) -> SampleResult:
    return SampleResult(
        question=question,
        answer=answer,
        contexts=contexts,
        context_precision=context_precision(question, contexts, ground_truth),
        context_recall=context_recall(ground_truth, contexts),
        faithfulness=faithfulness(answer, contexts),
        answer_relevancy=answer_relevancy(question, answer),
    )


def contexts_from_docs(docs: list[Document]) -> list[str]:
    return [d.page_content for d in docs if getattr(d, "page_content", "").strip()]
