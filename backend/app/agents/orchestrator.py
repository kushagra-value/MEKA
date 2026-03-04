from __future__ import annotations

import json
import re
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI


PLANNING_PROMPT = """You are a task planning agent for a security & compliance knowledge assistant.
Given a complex query, decompose it into 2-4 focused sub-tasks. Each sub-task should be a specific
search query that can independently retrieve relevant information.

Guidelines:
- Each sub-task should target a different aspect of the question
- Sub-tasks should be specific enough for effective retrieval
- Include sub-tasks for both finding evidence and performing analysis

You MUST respond with ONLY a valid JSON array. No explanation, no markdown fences, no extra text.
Each object MUST have exactly two keys: "description" and "query".

Example response:
[{{"description": "Find OAuth token leakage incidents", "query": "OAuth token leakage security incidents"}}, {{"description": "Identify root causes of token leakage", "query": "root cause analysis OAuth token vulnerability"}}, {{"description": "Find mitigation strategies", "query": "OAuth token security mitigation best practices"}}]

User query: {query}

JSON array:"""


def _extract_json_array(text: str) -> list[dict]:
    """Extract a JSON array from LLM output, handling markdown fences and surrounding text."""
    text = text.strip()

    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    bracket_match = re.search(r"\[.*\]", text, re.DOTALL)
    if bracket_match:
        text = bracket_match.group(0)

    return json.loads(text)


def _normalize_task(task: dict) -> tuple[str, str]:
    """Extract description and query from a task dict regardless of key naming."""
    desc_keys = ("description", "task_description", "task", "name", "title", "sub_task")
    query_keys = ("query", "search_query", "search", "search_term", "retrieval_query")

    description = ""
    for k in desc_keys:
        if k in task:
            description = str(task[k])
            break
    if not description:
        for v in task.values():
            if isinstance(v, str) and len(v) > 10:
                description = v
                break

    query = ""
    for k in query_keys:
        if k in task:
            query = str(task[k])
            break
    if not query:
        query = description

    return description, query


class OrchestratorAgent:
    def __init__(self, llm: ChatGoogleGenerativeAI) -> None:
        self.llm = llm

    def execute(self, state: dict) -> dict:
        query = state["query"]
        trace_entry = {
            "agent": "Orchestrator",
            "action": "Planning sub-tasks",
            "input_summary": query,
            "timestamp": datetime.utcnow().isoformat(),
            "details": {},
        }

        try:
            response = self.llm.invoke(PLANNING_PROMPT.format(query=query))
            content = response.content.strip()

            sub_tasks_raw = _extract_json_array(content)

            if not isinstance(sub_tasks_raw, list) or len(sub_tasks_raw) == 0:
                raise ValueError("LLM did not return a non-empty JSON array")

            sub_tasks = []
            for i, task in enumerate(sub_tasks_raw[:4]):
                description, task_query = _normalize_task(task)
                if not description:
                    continue
                sub_tasks.append({
                    "id": f"st-{i}",
                    "description": description,
                    "query": task_query,
                    "status": "pending",
                    "result": "",
                })

            if not sub_tasks:
                raise ValueError("No valid sub-tasks extracted from LLM response")

            trace_entry["output_summary"] = f"Created {len(sub_tasks)} sub-tasks"
            trace_entry["details"] = {"sub_tasks": [t["description"] for t in sub_tasks]}

            return {
                "sub_tasks": sub_tasks,
                "agent_trace": [trace_entry],
                "status": "planning",
            }

        except Exception as e:
            sub_tasks = [{
                "id": "st-0",
                "description": "Direct search for query",
                "query": query,
                "status": "pending",
                "result": "",
            }]
            trace_entry["output_summary"] = f"Fallback to single task: {e}"
            return {
                "sub_tasks": sub_tasks,
                "agent_trace": [trace_entry],
                "status": "planning",
            }
