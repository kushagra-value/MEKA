from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.config import CHUNK_SIZE, CHUNK_OVERLAP


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    return splitter.split_text(text)


def chunk_document(text: str, source: str, metadata: dict | None = None) -> list[dict]:
    metadata = metadata or {}
    chunks = chunk_text(text)
    return [
        {
            "content": chunk,
            "source": source,
            "metadata": {**metadata, "chunk_index": i},
        }
        for i, chunk in enumerate(chunks)
    ]
