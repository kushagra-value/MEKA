from __future__ import annotations

import json
import re
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI


VALIDATION_PROMPT = """You are a relevance validation agent. Given a query and a list of text chunks,
rate each chunk's relevance to the query on a scale of 1-5:
  5 = Directly answers the query
  4 = Highly relevant supporting evidence
  3 = Somewhat relevant context
  2 = Tangentially related
  1 = Not relevant

You MUST respond with ONLY a JSON array of integers, one per chunk, in the same order.
No explanation, no markdown, no extra text. Example: [5, 3, 1, 4, 2]

Query: {query}

Chunks:
{chunks}

JSON scores:"""


def _extract_scores(text: str) -> list[int]:
    """Extract integer scores array from LLM output."""
    text = text.strip()

    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    bracket_match = re.search(r"\[[\d\s,]+\]", text)
    if bracket_match:
        text = bracket_match.group(0)

    return json.loads(text)


class ValidatorAgent:
    def __init__(self, llm: ChatGoogleGenerativeAI) -> None:
        self.llm = llm

    def execute(self, state: dict) -> dict:
        query = state["query"]
        chunks = state.get("reranked_chunks", [])

        trace = {
            "agent": "Validator",
            "action": "Validating chunk relevance",
            "input_summary": f"Validating {len(chunks)} chunks",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {},
        }

        if not chunks:
            trace["output_summary"] = "No chunks to validate"
            return {
                "validated_chunks": [],
                "agent_trace": [trace],
                "status": "validating",
            }

        chunks_text = "\n---\n".join(
            f"[Chunk {i}] (source: {c['source']})\n{c['content'][:500]}"
            for i, c in enumerate(chunks)
        )

        try:
            response = self.llm.invoke(
                VALIDATION_PROMPT.format(query=query, chunks=chunks_text)
            )
            scores = _extract_scores(response.content)

            validated = []
            for chunk, score in zip(chunks, scores):
                if isinstance(score, (int, float)) and score >= 3:
                    chunk["relevance_score"] = score
                    validated.append(chunk)

            trace["output_summary"] = (
                f"Kept {len(validated)}/{len(chunks)} relevant chunks"
            )
            trace["details"] = {
                "scores": scores[:len(chunks)],
                "kept": len(validated),
                "filtered": len(chunks) - len(validated),
            }

        except Exception as e:
            validated = chunks
            trace["output_summary"] = f"Validation fallback (kept all): {e}"

        return {
            "validated_chunks": validated,
            "agent_trace": [trace],
            "status": "validating",
        }
