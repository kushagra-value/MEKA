from __future__ import annotations

import math
from datetime import datetime

from sentence_transformers import CrossEncoder

from app.config import RERANKER_MODEL, TOP_K_RERANK


def _sigmoid(x: float) -> float:
    """Convert raw logit to 0-1 probability."""
    return 1.0 / (1.0 + math.exp(-x))


class RerankerAgent:
    _model: CrossEncoder | None = None

    def __init__(self, model_name: str = RERANKER_MODEL) -> None:
        self._model_name = model_name

    @property
    def model(self) -> CrossEncoder:
        if RerankerAgent._model is None:
            RerankerAgent._model = CrossEncoder(self._model_name)
        return RerankerAgent._model

    def execute(self, state: dict) -> dict:
        query = state["query"]
        chunks = state.get("all_retrieved_chunks", [])

        trace = {
            "agent": "Reranker",
            "action": "Cross-encoder reranking",
            "input_summary": f"Reranking {len(chunks)} chunks",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {},
        }

        if not chunks:
            trace["output_summary"] = "No chunks to rerank"
            return {
                "reranked_chunks": [],
                "agent_trace": [trace],
                "status": "reranking",
            }

        pairs = [[query, chunk["content"]] for chunk in chunks]
        raw_scores = self.model.predict(pairs).tolist()

        for chunk, raw in zip(chunks, raw_scores):
            chunk["rerank_score"] = round(_sigmoid(raw), 4)

        ranked = sorted(chunks, key=lambda c: c["rerank_score"], reverse=True)
        top_chunks = ranked[:TOP_K_RERANK]

        trace["output_summary"] = (
            f"Selected top {len(top_chunks)} from {len(chunks)} chunks"
        )
        trace["details"] = {
            "input_count": len(chunks),
            "output_count": len(top_chunks),
            "top_score": top_chunks[0]["rerank_score"] if top_chunks else 0,
        }

        return {
            "reranked_chunks": top_chunks,
            "agent_trace": [trace],
            "status": "reranking",
        }
