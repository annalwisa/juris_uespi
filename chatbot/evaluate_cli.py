"""CLI de avaliação do RAG.

Uso:
    python -m chatbot.evaluate_cli                 # usa data/eval/golden_qa.yaml
    python -m chatbot.evaluate_cli --limit 3       # avalia só as 3 primeiras
    python -m chatbot.evaluate_cli --out results.csv

Para cada pergunta do conjunto, executa o pipeline do chatbot (recuperação +
geração), coleta os trechos usados e calcula as quatro métricas (Context
Precision, Context Recall, Faithfulness, Answer Relevancy). Ao final, imprime
uma tabela e a média geral, e opcionalmente salva CSV e JSON.
"""

import argparse
import csv
import json
import os
from pathlib import Path

import yaml

from chatbot.config import OPENAI_API_KEY, ROOT
from chatbot.evaluation import (
    EvaluationReport,
    contexts_from_docs,
    evaluate_sample,
)

DEFAULT_DATASET = ROOT / "data" / "eval" / "golden_qa.yaml"

# Perfis para comparar baseline vs. melhorias no TCC.
_PROFILES = {
    "baseline": {
        "RAG_RERANKER_ENABLED": "false",
        "RAG_HYBRID_ENABLED": "false",
        "RAG_MULTI_QUERY_ENABLED": "false",
    },
    "full": {
        "RAG_RERANKER_ENABLED": "true",
        "RAG_HYBRID_ENABLED": "true",
        "RAG_MULTI_QUERY_ENABLED": "true",
    },
}


def apply_profile(name: str) -> None:
    for key, value in _PROFILES[name].items():
        os.environ[key] = value
    # Recarrega flags em chatbot.config (já importado indiretamente depois).
    import chatbot.config as cfg

    cfg.RERANKER_ENABLED = _PROFILES[name]["RAG_RERANKER_ENABLED"] == "true"
    cfg.HYBRID_ENABLED = _PROFILES[name]["RAG_HYBRID_ENABLED"] == "true"
    cfg.MULTI_QUERY_ENABLED = _PROFILES[name]["RAG_MULTI_QUERY_ENABLED"] == "true"


def load_dataset(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    samples = data.get("samples", [])
    return [s for s in samples if s.get("question") and s.get("ground_truth")]


def _fmt(v: float) -> str:
    return f"{v:0.3f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Avalia o RAG do JurisUESPI.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="Arquivo YAML com 'samples' (question/ground_truth).",
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Avalia apenas os N primeiros itens."
    )
    parser.add_argument(
        "--out", type=Path, default=None, help="Salva os resultados em CSV (e JSON)."
    )
    parser.add_argument(
        "--profile",
        choices=sorted(_PROFILES.keys()),
        default="full",
        help="baseline = só busca densa; full = rerank + híbrido + multi-query.",
    )
    parser.add_argument(
        "--rag-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Avalia só o pipeline RAG (ignora FAQ/respostas fixas). Padrão: ligado.",
    )
    args = parser.parse_args()

    apply_profile(args.profile)
    print(f"Perfil de recuperação: {args.profile}")
    print(f"Modo: {'RAG apenas' if args.rag_only else 'chatbot completo (com FAQ)'}\n")

    if not OPENAI_API_KEY:
        raise SystemExit(
            "OPENAI_API_KEY não definida no .env. A avaliação usa o modelo como juiz "
            "e embeddings, portanto requer a chave da OpenAI."
        )

    # Import tardio: evita carregar a stack de RAG quando só se quer --help.
    from chatbot.chain import answer_with_rag_details, get_answer_details
    from chatbot.vectorstore import get_vector_store

    samples = load_dataset(args.dataset)
    if args.limit > 0:
        samples = samples[: args.limit]
    if not samples:
        raise SystemExit(f"Nenhum item válido em {args.dataset}.")

    print(f"Avaliando {len(samples)} pergunta(s) de {args.dataset}...\n")

    vector_store = None
    if args.rag_only:
        vector_store = get_vector_store()
        if vector_store is None:
            raise SystemExit(
                "Banco vetorial vazio ou indisponível. Rode antes:\n"
                "  python -m chatbot.ingest_cli --reset"
            )

    report = EvaluationReport()
    for i, item in enumerate(samples, start=1):
        question = item["question"].strip()
        ground_truth = item["ground_truth"].strip()
        print(f"[{i}/{len(samples)}] {question}")

        if args.rag_only:
            answer, docs = answer_with_rag_details(vector_store, question)
        else:
            answer, docs = get_answer_details(question)
        contexts = contexts_from_docs(docs)
        result = evaluate_sample(question, answer, contexts, ground_truth)
        report.samples.append(result)

        print(
            f"    precision={_fmt(result.context_precision)} "
            f"recall={_fmt(result.context_recall)} "
            f"faithfulness={_fmt(result.faithfulness)} "
            f"answer_relevancy={_fmt(result.answer_relevancy)}\n"
        )

    avg = report.averages
    print("=" * 60)
    print("MÉDIAS GERAIS")
    print(f"  Context Precision : {_fmt(avg['context_precision'])}")
    print(f"  Context Recall    : {_fmt(avg['context_recall'])}")
    print(f"  Faithfulness      : {_fmt(avg['faithfulness'])}")
    print(f"  Answer Relevancy  : {_fmt(avg['answer_relevancy'])}")
    print("=" * 60)

    if args.out:
        _save_results(args.out, report)
        print(f"\nResultados salvos em {args.out} e {args.out.with_suffix('.json')}")


def _save_results(out: Path, report: EvaluationReport) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "question",
                "context_precision",
                "context_recall",
                "faithfulness",
                "answer_relevancy",
            ]
        )
        for s in report.samples:
            writer.writerow(
                [
                    s.question,
                    f"{s.context_precision:0.4f}",
                    f"{s.context_recall:0.4f}",
                    f"{s.faithfulness:0.4f}",
                    f"{s.answer_relevancy:0.4f}",
                ]
            )

    payload = {
        "averages": report.averages,
        "samples": [
            {
                "question": s.question,
                "answer": s.answer,
                "context_precision": s.context_precision,
                "context_recall": s.context_recall,
                "faithfulness": s.faithfulness,
                "answer_relevancy": s.answer_relevancy,
            }
            for s in report.samples
        ],
    }
    out.with_suffix(".json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
