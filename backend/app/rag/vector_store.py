import hashlib
import threading

import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from sentence_transformers import SentenceTransformer

from app.config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL

COLLECTION_NAME = "rag_documents"


class _SentenceTransformerEF(EmbeddingFunction):
    def __init__(self, model_name: str) -> None:
        self._model = SentenceTransformer(model_name)

    def __call__(self, input: Documents) -> Embeddings:
        return self._model.encode(input, show_progress_bar=False).tolist()


class VectorStore:
    _instance: "VectorStore | None" = None
    _lock = threading.Lock()

    def __new__(
        cls,
        persist_dir: str = CHROMA_PERSIST_DIR,
        embedding_model: str = EMBEDDING_MODEL,
    ) -> "VectorStore":
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._init(persist_dir, embedding_model)
                cls._instance = instance
            return cls._instance

    def _init(self, persist_dir: str, embedding_model: str) -> None:
        self._ef = _SentenceTransformerEF(embedding_model)
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._ef,
        )

    def add_documents(self, documents: list[dict]) -> None:
        if not documents:
            return

        ids: list[str] = []
        docs: list[str] = []
        metadatas: list[dict] = []

        for doc in documents:
            content = doc["content"]
            source = doc["source"]
            meta = doc.get("metadata", {})

            raw_id = f"{source}::{meta.get('chunk_index', 0)}::{content[:64]}"
            doc_id = hashlib.sha256(raw_id.encode()).hexdigest()

            flat_meta = {"source": source}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    flat_meta[k] = v

            ids.append(doc_id)
            docs.append(content)
            metadatas.append(flat_meta)

        batch_size = 500
        for i in range(0, len(ids), batch_size):
            self._collection.upsert(
                ids=ids[i : i + batch_size],
                documents=docs[i : i + batch_size],
                metadatas=metadatas[i : i + batch_size],
            )

    def search(self, query: str, top_k: int) -> list[dict]:
        results = self._collection.query(query_texts=[query], n_results=top_k)
        output: list[dict] = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            source = meta.pop("source", "")
            output.append({
                "content": doc,
                "source": source,
                "score": 1.0 / (1.0 + dist),
                "metadata": meta,
            })
        return output

    def get_collection_count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        self._client.delete_collection(COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._ef,
        )
