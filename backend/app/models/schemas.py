from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
import uuid


class QueryStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RETRIEVING = "retrieving"
    RERANKING = "reranking"
    VALIDATING = "validating"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    web_search_enabled: bool = True
    user_id: str = "default_user"


class AgentStep(BaseModel):
    agent: str
    action: str
    input_summary: str = ""
    output_summary: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    details: dict[str, Any] = {}


class RetrievedChunk(BaseModel):
    content: str
    source: str
    score: float
    chunk_id: str = ""
    metadata: dict[str, Any] = {}


class SubTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str
    query: str
    status: str = "pending"
    result: str = ""


class QueryResponse(BaseModel):
    query_id: str
    status: QueryStatus
    message: str = ""


class QueryResult(BaseModel):
    query_id: str
    original_query: str
    status: QueryStatus
    sub_tasks: list[SubTask] = []
    agent_trace: list[AgentStep] = []
    reranked_chunks: list[RetrievedChunk] = []
    final_answer: str = ""
    reasoning: str = ""
    sources: list[str] = []
    created_at: str = ""
    completed_at: Optional[str] = None


class HistoryEntry(BaseModel):
    query_id: str
    query: str
    status: QueryStatus
    created_at: str
    final_answer: str = ""
