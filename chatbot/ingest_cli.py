"""CLI: python -m chatbot.ingest_cli [--reset]"""

import argparse

from chatbot.config import VECTOR_STORE
from chatbot.ingest import index_documents, load_documents
from chatbot.vectorstore import store_label, vector_store_count


def main():
    parser = argparse.ArgumentParser(
        description="Indexa documentos da UESPI (Pinecone ou Chroma)."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Apaga os vetores existentes antes de reindexar.",
    )
    args = parser.parse_args()

    docs = load_documents()
    print(f"Arquivos carregados: {len(docs)} documento(s) (páginas/blocos brutos).")
    print(f"Destino: {store_label()} (VECTOR_STORE={VECTOR_STORE})")

    store = index_documents(reset=args.reset)
    count = vector_store_count(store)
    print(f"Indexação concluída: {count} trechos no banco vetorial.")


if __name__ == "__main__":
    main()
