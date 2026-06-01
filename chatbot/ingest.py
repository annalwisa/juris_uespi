"""Carrega documentos de data/docs e indexa no banco vetorial."""

from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from chatbot.config import CHUNK_OVERLAP, CHUNK_SIZE, DOCS_DIR
from chatbot.metadata import enrich_chunks
from chatbot.vectorstore import build_vector_store

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md"}


def _load_pdf(path: Path) -> list[Document]:
    if fitz is not None:
        docs: list[Document] = []
        with fitz.open(path) as pdf:
            for i, page in enumerate(pdf):
                text = page.get_text() or ""
                if text.strip():
                    docs.append(
                        Document(
                            page_content=text,
                            metadata={"source": path.name, "page": i + 1},
                        )
                    )
        if docs:
            return docs
    return PyPDFLoader(str(path)).load()


def _load_file(path: Path) -> list[Document]:
    if path.suffix.lower() == ".pdf":
        return _load_pdf(path)
    return TextLoader(str(path), encoding="utf-8").load()


def load_documents(docs_dir: Path | None = None) -> list[Document]:
    docs_dir = docs_dir or DOCS_DIR
    if not docs_dir.exists():
        docs_dir.mkdir(parents=True, exist_ok=True)
        return []

    documents: list[Document] = []
    for path in sorted(docs_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if path.name.upper().startswith("README"):
            continue
        for doc in _load_file(path):
            doc.metadata["source"] = path.name
            documents.append(doc)
    return documents


def index_documents(*, reset: bool = False) -> VectorStore:
    documents = load_documents()

    if not documents:
        raise FileNotFoundError(
            f"Nenhum documento encontrado em {DOCS_DIR}. "
            "Adicione arquivos .pdf, .txt ou .md (regulamentos, editais, manuais) e tente novamente."
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    chunks = [c for c in chunks if c.page_content and c.page_content.strip()]
    chunks = enrich_chunks(chunks)

    if not chunks:
        raise ValueError(
            "Nenhum texto extraído dos PDFs em data/docs. "
            "Se o arquivo for escaneado (só imagem), use PDF com texto selecionável ou OCR."
        )

    return build_vector_store(chunks, reset=reset)


# Compatibilidade com imports antigos
def build_vector_store_from_docs(*, reset: bool = False) -> VectorStore:
    return index_documents(reset=reset)


def get_vector_store():
    from chatbot.vectorstore import get_vector_store as _get

    return _get()
