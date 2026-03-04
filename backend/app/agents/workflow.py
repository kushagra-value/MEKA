from __future__ import annotations

import operator
import uuid
from datetime import datetime
from typing import Annotated, Any, TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph

from app.agents.orchestrator import OrchestratorAgent
from app.agents.reranker import RerankerAgent
from app.agents.retriever import RetrieverAgent
from app.agents.summarizer import SummarizerAgent
from app.agents.validator import ValidatorAgent
from app.config import GEMINI_MODEL, GOOGLE_API_KEY
from app.rag.hybrid_search import HybridSearch


class WorkflowState(TypedDict):
    query: str
    query_id: str
    web_search_enabled: bool
    sub_tasks: list[dict[str, Any]]
    all_retrieved_chunks: list[dict[str, Any]]
    reranked_chunks: list[dict[str, Any]]
    validated_chunks: list[dict[str, Any]]
    final_answer: str
    reasoning: str
    sources: list[str]
    agent_trace: Annotated[list[dict[str, Any]], operator.add]
    status: str
    error: str


class MEKAWorkflow:
    def __init__(self, hybrid_search: HybridSearch) -> None:
        self.llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.1,
        )
        self.orchestrator = OrchestratorAgent(self.llm)
        self.retriever = RetrieverAgent(hybrid_search)
        self.reranker = RerankerAgent()
        self.summarizer = SummarizerAgent(self.llm)
        self.validator = ValidatorAgent(self.llm)
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        graph = StateGraph(WorkflowState)

        graph.add_node("plan", self.orchestrator.execute)
        graph.add_node("retrieve", self.retriever.execute)
        graph.add_node("rerank", self.reranker.execute)
        graph.add_node("validate", self.validator.execute)
        graph.add_node("summarize", self.summarizer.execute)

        graph.set_entry_point("plan")
        graph.add_edge("plan", "retrieve")
        graph.add_edge("retrieve", "rerank")
        graph.add_edge("rerank", "validate")
        graph.add_edge("validate", "summarize")
        graph.add_edge("summarize", END)

        return graph.compile()

    def run(self, query: str, web_search_enabled: bool = True) -> dict:
        query_id = str(uuid.uuid4())
        initial_state: WorkflowState = {
            "query": query,
            "query_id": query_id,
            "web_search_enabled": web_search_enabled,
            "sub_tasks": [],
            "all_retrieved_chunks": [],
            "reranked_chunks": [],
            "validated_chunks": [],
            "final_answer": "",
            "reasoning": "",
            "sources": [],
            "agent_trace": [],
            "status": "pending",
            "error": "",
        }

        result = self.graph.invoke(initial_state)

        return {
            "query_id": query_id,
            "original_query": query,
            "status": result.get("status", "completed"),
            "sub_tasks": result.get("sub_tasks", []),
            "agent_trace": result.get("agent_trace", []),
            "reranked_chunks": [
                {
                    "content": c["content"],
                    "source": c["source"],
                    "score": c.get("rerank_score", c.get("score", 0)),
                    "metadata": c.get("metadata", {}),
                }
                for c in result.get("reranked_chunks", [])
            ],
            "final_answer": result.get("final_answer", ""),
            "reasoning": result.get("reasoning", ""),
            "sources": list(set(result.get("sources", []))),
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
        }
