from rank_bm25 import BM25Okapi

from app.rag.vector_store import VectorStore


class HybridSearch:
    def __init__(self, vector_store: VectorStore) -> None:
        self._vector_store = vector_store
        self._bm25: BM25Okapi | None = None
        self._documents: list[dict] = []

    def build_bm25_index(self, documents: list[dict]) -> None:
        self._documents = documents
        tokenized = [doc["content"].lower().split() for doc in documents]
        self._bm25 = BM25Okapi(tokenized)

    def _bm25_search(self, query: str, top_k: int) -> list[dict]:
        if self._bm25 is None or not self._documents:
            return []

        tokens = query.lower().split()
        scores = self._bm25.get_scores(tokens)

        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        results: list[dict] = []
        for idx, score in ranked:
            if score <= 0:
                continue
            doc = self._documents[idx]
            results.append({
                "content": doc["content"],
                "source": doc["source"],
                "score": float(score),
                "metadata": doc.get("metadata", {}),
            })
        return results

    def search(self, query: str, top_k: int, alpha: float = 0.5) -> list[dict]:
        expanded_k = top_k * 2

        vector_results = self._vector_store.search(query, expanded_k)
        bm25_results = self._bm25_search(query, expanded_k)

        scores: dict[str, float] = {}
        doc_map: dict[str, dict] = {}

        for rank, result in enumerate(vector_results):
            key = f"{result['source']}::{result['content'][:128]}"
            rrf = 1.0 / (60 + rank + 1)
            scores[key] = scores.get(key, 0.0) + alpha * rrf
            doc_map[key] = result

        for rank, result in enumerate(bm25_results):
            key = f"{result['source']}::{result['content'][:128]}"
            rrf = 1.0 / (60 + rank + 1)
            scores[key] = scores.get(key, 0.0) + (1 - alpha) * rrf
            if key not in doc_map:
                doc_map[key] = result

        ranked_keys = sorted(scores, key=scores.__getitem__, reverse=True)[:top_k]
        return [
            {**doc_map[k], "score": scores[k]}
            for k in ranked_keys
        ]
