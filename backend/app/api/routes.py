from __future__ import annotations

import asyncio
import traceback
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models.schemas import QueryRequest, QueryResponse, QueryStatus

router = APIRouter()

_workflow = None
_history = None


def init_dependencies(workflow: Any, history: Any) -> None:
    global _workflow, _history
    _workflow = workflow
    _history = history


def _run_query(query_id: str, query: str, user_id: str, web_search_enabled: bool) -> None:
    try:
        _history.store_query(query_id, user_id, {
            "original_query": query,
            "status": "processing",
            "created_at": "",
            "agent_trace": [],
        })

        result = _workflow.run(query=query, web_search_enabled=web_search_enabled)
        result["query_id"] = query_id
        _history.store_query(query_id, user_id, result)

    except Exception as e:
        _history.store_query(query_id, user_id, {
            "original_query": query,
            "status": "failed",
            "error": traceback.format_exc(),
            "final_answer": f"Processing failed: {e}",
        })


@router.post("/query", response_model=QueryResponse)
async def submit_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
) -> QueryResponse:
    if _workflow is None:
        raise HTTPException(status_code=503, detail="System not initialized")

    import uuid
    query_id = str(uuid.uuid4())

    background_tasks.add_task(
        _run_query,
        query_id,
        request.query,
        request.user_id,
        request.web_search_enabled,
    )

    return QueryResponse(
        query_id=query_id,
        status=QueryStatus.PENDING,
        message="Query submitted for processing",
    )


@router.post("/query/sync")
async def submit_query_sync(request: QueryRequest) -> dict:
    if _workflow is None:
        raise HTTPException(status_code=503, detail="System not initialized")

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _workflow.run(
            query=request.query,
            web_search_enabled=request.web_search_enabled,
        ),
    )

    _history.store_query(result["query_id"], request.user_id, result)
    return result


@router.get("/status/{query_id}")
async def get_query_status(query_id: str) -> dict:
    if _history is None:
        raise HTTPException(status_code=503, detail="System not initialized")

    entry = _history.get_query(query_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Query not found")

    return entry


@router.get("/history/{user_id}")
async def get_user_history(user_id: str) -> list[dict]:
    if _history is None:
        raise HTTPException(status_code=503, detail="System not initialized")

    return _history.get_user_history(user_id)


@router.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "initialized": _workflow is not None}
