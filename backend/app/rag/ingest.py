import csv
import json
import os

import docx2txt
from PyPDF2 import PdfReader

from app.rag.chunking import chunk_document
from app.rag.vector_store import VectorStore

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".json", ".csv"}


def load_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_json_file(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return [data]


def load_csv_file(path: str) -> list[dict]:
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def load_pdf_file(path: str) -> str:
    reader = PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def load_docx_file(path: str) -> str:
    return docx2txt.process(path)


def _rows_to_text(rows: list[dict], source: str) -> str:
    lines: list[str] = []
    for i, row in enumerate(rows):
        parts = [f"{k}: {v}" for k, v in row.items() if v]
        lines.append(f"[{source} row {i}] " + " | ".join(parts))
    return "\n".join(lines)


def ingest_directory(
    data_dir: str,
    vector_store: VectorStore,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[int, list[dict]]:
    all_chunks: list[dict] = []
    doc_count = 0

    for root, _, files in os.walk(data_dir):
        for filename in sorted(files):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, data_dir)
            print(f"Ingesting: {rel_path}")

            try:
                if ext in (".txt", ".md"):
                    text = load_text_file(filepath)
                elif ext == ".pdf":
                    text = load_pdf_file(filepath)
                elif ext == ".docx":
                    text = load_docx_file(filepath)
                elif ext == ".json":
                    rows = load_json_file(filepath)
                    text = _rows_to_text(rows, rel_path)
                elif ext == ".csv":
                    rows = load_csv_file(filepath)
                    text = _rows_to_text(rows, rel_path)
                else:
                    continue

                if not text.strip():
                    print(f"  Skipped (empty): {rel_path}")
                    continue

                chunks = chunk_document(
                    text,
                    source=rel_path,
                    metadata={"file_type": ext},
                )
                all_chunks.extend(chunks)
                doc_count += 1
                print(f"  Created {len(chunks)} chunks")

            except Exception as e:
                print(f"  Error processing {rel_path}: {e}")

    if all_chunks:
        vector_store.add_documents(all_chunks)
        print(f"Ingestion complete: {doc_count} files, {len(all_chunks)} total chunks")

    return doc_count, all_chunks


def load_and_chunk_directory(
    data_dir: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict]:
    """Load and chunk all documents without adding to vector store (for BM25 index)."""
    all_chunks: list[dict] = []

    for root, _, files in os.walk(data_dir):
        for filename in sorted(files):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, data_dir)

            try:
                if ext in (".txt", ".md"):
                    text = load_text_file(filepath)
                elif ext == ".pdf":
                    text = load_pdf_file(filepath)
                elif ext == ".docx":
                    text = load_docx_file(filepath)
                elif ext == ".json":
                    rows = load_json_file(filepath)
                    text = _rows_to_text(rows, rel_path)
                elif ext == ".csv":
                    rows = load_csv_file(filepath)
                    text = _rows_to_text(rows, rel_path)
                else:
                    continue

                if not text.strip():
                    continue

                chunks = chunk_document(
                    text, source=rel_path, metadata={"file_type": ext},
                )
                all_chunks.extend(chunks)

            except Exception:
                pass

    return all_chunks
