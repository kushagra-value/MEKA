from __future__ import annotations

import requests
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.rag.hybrid_search import HybridSearch

from app.config import TOP_K_RETRIEVAL, WEB_SEARCH_ENABLED, SERPER_API_KEY

SERPER_URL = "https://google.serper.dev/search"


class RetrieverAgent:
    def __init__(self, hybrid_search: HybridSearch) -> None:
        self.hybrid_search = hybrid_search

    @staticmethod
    def _web_search(query: str, max_results: int = 5) -> list[dict]:
        if not SERPER_API_KEY:
            print("  Web search skipped: SERPER_API_KEY not set")
            return []

        try:
            resp = requests.post(
                SERPER_URL,
                headers={
                    "X-API-KEY": SERPER_API_KEY,
                    "Content-Type": "application/json",
                },
                json={"q": query, "num": max_results},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            results: list[dict] = []
            for item in data.get("organic", [])[:max_results]:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                results.append({
                    "content": f"{title}\n{snippet}",
                    "source": f"web:{link}",
                    "score": 0.5,
                    "metadata": {"type": "web_search", "url": link},
                })
            return results

        except Exception as e:
            print(f"  Serper web search failed: {e}")
            return []

    def execute(self, state: dict) -> dict:
        sub_tasks = state.get("sub_tasks", [])
        original_query = state.get("query", "")
        web_search_enabled = state.get("web_search_enabled", WEB_SEARCH_ENABLED)
        all_chunks: list[dict] = []
        trace_entries: list[dict] = []
        global_seen: set[str] = set()

        if web_search_enabled:
            web_results = self._web_search(original_query)
            for chunk in web_results:
                key = chunk["content"][:200]
                if key not in global_seen:
                    global_seen.add(key)
                    all_chunks.append(chunk)

            trace_entries.append({
                "agent": "Retriever",
                "action": "Web search (Serper)",
                "input_summary": original_query,
                "timestamp": datetime.utcnow().isoformat(),
                "details": {"web_count": len(web_results)},
                "output_summary": f"Found {len(web_results)} web results",
            })

        for task in sub_tasks:
            task_query = task["query"]
            trace = {
                "agent": "Retriever",
                "action": f"Searching for: {task['description']}",
                "input_summary": task_query,
                "timestamp": datetime.utcnow().isoformat(),
                "details": {},
            }

            local_results = self.hybrid_search.search(task_query, TOP_K_RETRIEVAL)

            new_chunks = 0
            for chunk in local_results:
                key = chunk["content"][:200]
                if key not in global_seen:
                    global_seen.add(key)
                    all_chunks.append(chunk)
                    new_chunks += 1

            task["status"] = "retrieved"

            trace["output_summary"] = (
                f"Found {len(local_results)} local results ({new_chunks} new unique)"
            )
            trace["details"] = {
                "local_count": len(local_results),
                "new_unique_count": new_chunks,
            }
            trace_entries.append(trace)

        return {
            "all_retrieved_chunks": all_chunks,
            "sub_tasks": sub_tasks,
            "agent_trace": trace_entries,
            "status": "retrieving",
        }
