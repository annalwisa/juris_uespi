"""Metadados de vigência dos documentos (ano, status, substituição)."""

from __future__ import annotations

import re

import yaml
from langchain_core.documents import Document

from chatbot.config import DOCS_DIR

MANIFEST_PATH = DOCS_DIR / "manifest.yaml"
YEAR_RE = re.compile(r"(19|20)\d{2}")

STATUS_VIGENTE = "vigente"
STATUS_DESATUALIZADO = "desatualizado"
STATUS_REVOGADO = "revogado"

_STATUS_RANK = {
    STATUS_VIGENTE: 0,
    STATUS_DESATUALIZADO: 1,
    STATUS_REVOGADO: 2,
}


def extract_year_from_filename(filename: str) -> int | None:
    years = [int(m.group()) for m in YEAR_RE.finditer(filename)]
    return max(years) if years else None


def load_manifest() -> dict[str, dict]:
    if not MANIFEST_PATH.exists():
        return {}
    with MANIFEST_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("documents", {}) or {}


def get_doc_entry(filename: str, manifest: dict[str, dict] | None = None) -> dict:
    manifest = manifest if manifest is not None else load_manifest()
    entry = dict(manifest.get(filename, {}))
    if "year" not in entry:
        entry["year"] = extract_year_from_filename(filename)
    entry.setdefault("status", STATUS_VIGENTE)
    return entry


def enrich_document(doc: Document, manifest: dict[str, dict] | None = None) -> Document:
    source = doc.metadata.get("source", "")
    entry = get_doc_entry(source, manifest)

    doc.metadata["source"] = source
    if entry.get("year"):
        doc.metadata["year"] = int(entry["year"])
    if entry.get("status"):
        doc.metadata["status"] = entry["status"]
    if entry.get("tipo"):
        doc.metadata["tipo"] = entry["tipo"]
    if entry.get("substituido_por"):
        doc.metadata["substituido_por"] = entry["substituido_por"]
    if entry.get("nota"):
        doc.metadata["nota"] = entry["nota"]
    return doc


def enrich_chunks(chunks: list[Document]) -> list[Document]:
    manifest = load_manifest()
    return [enrich_document(c, manifest) for c in chunks]


def status_rank(status: str | None) -> int:
    return _STATUS_RANK.get(status or STATUS_VIGENTE, 1)


def year_value(metadata: dict) -> int:
    y = metadata.get("year")
    return int(y) if y else 0
