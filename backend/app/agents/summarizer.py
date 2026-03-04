from __future__ import annotations

from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI


SUMMARIZATION_PROMPT = """You are an expert knowledge assistant specializing in security and compliance analysis.
Given a user's query, the planned sub-tasks, and validated evidence chunks, produce a comprehensive
structured answer.

Your response MUST follow this exact format:

## Answer
[Provide a detailed, well-structured answer addressing every aspect of the query.
Use bullet points and clear organization. Reference specific evidence.]

## Reasoning
[Explain your reasoning chain: how you connected evidence from different sources,
what sub-tasks contributed to the answer, and any inferences made.]

## Sources
[List the source documents/tickets that contributed to this answer, one per line.]

## Confidence
[Rate your confidence: High / Medium / Low, with a brief justification.]

---

Query: {query}

Sub-tasks completed:
{sub_tasks}

Evidence (ranked by relevance):
{evidence}
"""


class SummarizerAgent:
    def __init__(self, llm: ChatGoogleGenerativeAI) -> None:
        self.llm = llm

    def execute(self, state: dict) -> dict:
        query = state["query"]
        sub_tasks = state.get("sub_tasks", [])
        chunks = state.get("validated_chunks", [])

        trace = {
            "agent": "Summarizer",
            "action": "Generating structured answer",
            "input_summary": f"Synthesizing from {len(chunks)} evidence chunks",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {},
        }

        if not chunks:
            trace["output_summary"] = "No evidence available"
            return {
                "final_answer": "No relevant evidence was found to answer this query.",
                "reasoning": "The retrieval and validation pipeline returned no relevant chunks.",
                "sources": [],
                "agent_trace": [trace],
                "status": "completed",
            }

        sub_tasks_text = "\n".join(
            f"- [{t.get('status', 'done')}] {t['description']}" for t in sub_tasks
        )

        evidence_text = "\n\n---\n\n".join(
            f"[Source: {c['source']}] (relevance: {c.get('relevance_score', 'N/A')})\n{c['content']}"
            for c in chunks
        )

        try:
            response = self.llm.invoke(
                SUMMARIZATION_PROMPT.format(
                    query=query,
                    sub_tasks=sub_tasks_text,
                    evidence=evidence_text,
                )
            )
            answer_text = response.content.strip()

            final_answer, reasoning, sources = self._parse_response(answer_text)
            unique_sources = list({c["source"] for c in chunks})

            trace["output_summary"] = f"Generated answer ({len(final_answer)} chars)"
            trace["details"] = {
                "answer_length": len(final_answer),
                "source_count": len(unique_sources),
            }

            return {
                "final_answer": final_answer,
                "reasoning": reasoning,
                "sources": unique_sources + sources,
                "agent_trace": [trace],
                "status": "completed",
            }

        except Exception as e:
            trace["output_summary"] = f"Summarization failed: {e}"
            return {
                "final_answer": f"Error generating summary: {e}",
                "reasoning": "",
                "sources": [],
                "agent_trace": [trace],
                "status": "failed",
                "error": str(e),
            }

    @staticmethod
    def _parse_response(text: str) -> tuple[str, str, list[str]]:
        sections = {"answer": "", "reasoning": "", "sources": ""}
        current = None

        for line in text.split("\n"):
            stripped = line.strip().lower()
            if stripped.startswith("## answer"):
                current = "answer"
                continue
            elif stripped.startswith("## reasoning"):
                current = "reasoning"
                continue
            elif stripped.startswith("## sources"):
                current = "sources"
                continue
            elif stripped.startswith("## confidence"):
                current = "confidence"
                continue

            if current and current in sections:
                sections[current] += line + "\n"

        sources = [
            s.strip().lstrip("- ").strip()
            for s in sections["sources"].strip().split("\n")
            if s.strip() and s.strip() != "-"
        ]

        return (
            sections["answer"].strip() or text,
            sections["reasoning"].strip(),
            sources,
        )
