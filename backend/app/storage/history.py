from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from app.config import BASE_DIR


HISTORY_FILE = BASE_DIR / "query_history.json"


class QueryHistory:
    _instance: QueryHistory | None = None
    _lock = threading.Lock()

    def __new__(cls) -> QueryHistory:
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._init()
                cls._instance = instance
            return cls._instance

    def _init(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._user_index: dict[str, list[str]] = {}
        self._load()

    def _load(self) -> None:
        if HISTORY_FILE.exists():
            try:
                data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
                self._store = data.get("queries", {})
                self._user_index = data.get("user_index", {})
            except Exception:
                pass

    def _save(self) -> None:
        try:
            HISTORY_FILE.write_text(
                json.dumps(
                    {"queries": self._store, "user_index": self._user_index},
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

    def store_query(self, query_id: str, user_id: str, result: dict) -> None:
        with self._lock:
            self._store[query_id] = {**result, "user_id": user_id}
            self._user_index.setdefault(user_id, []).append(query_id)
            self._save()

    def get_query(self, query_id: str) -> dict | None:
        return self._store.get(query_id)

    def get_user_history(self, user_id: str) -> list[dict]:
        query_ids = self._user_index.get(user_id, [])
        results = []
        for qid in reversed(query_ids):
            entry = self._store.get(qid)
            if entry:
                results.append({
                    "query_id": qid,
                    "query": entry.get("original_query", ""),
                    "status": entry.get("status", "unknown"),
                    "created_at": entry.get("created_at", ""),
                    "final_answer": entry.get("final_answer", "")[:200],
                })
        return results
