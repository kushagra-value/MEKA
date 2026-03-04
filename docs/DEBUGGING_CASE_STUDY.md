# MEKA Debugging Case Study

A chronological record of the issues encountered during development and testing of the MEKA system, how each was diagnosed, and the fix applied. This serves as both a development log and a reference for understanding the design decisions behind the current implementation.

---

## Issue 1: Orchestrator Failing to Decompose Queries (Gemini JSON Parsing)

### Symptom

Every query fell back to a single "Direct search for query" task instead of being decomposed into 2-4 focused sub-tasks. The agent trace showed:

```
"output_summary": "Fallback to single task: '\"description\"'"
```

This was a `KeyError` -- the JSON was parsed successfully, but the expected key `"description"` was missing from the objects Gemini returned.

### Diagnosis

The root cause was in `orchestrator.py`. The original code assumed Gemini would return JSON with exactly the keys `"description"` and `"query"`:

```python
sub_tasks.append({
    "description": task["description"],  # KeyError here
    "query": task["query"],
})
```

Gemini wraps JSON responses differently than OpenAI -- sometimes in markdown fences, sometimes with different key names (e.g., `"task_description"`, `"search_query"`), and sometimes with explanatory text before/after the JSON block.

### Impact

Without query decomposition, MEKA ran as a single-pass RAG system instead of a multi-agent workflow. For simple queries (like OAuth token leakage) results were acceptable because a single broad search found relevant documents. For complex queries (like GDPR Article 32 compliance comparison), the system completely missed breach incident data because there was no separate sub-task to search for it.

### Fix

Three changes to `orchestrator.py`:

1. **Robust JSON extraction** (`_extract_json_array`): Uses regex to find JSON arrays regardless of surrounding markdown fences or text. Handles ```` ```json ``` ````, bare JSON, and JSON embedded in prose.

2. **Flexible key normalization** (`_normalize_task`): Accepts multiple key name variants for both description (`description`, `task_description`, `task`, `name`, `title`) and query (`query`, `search_query`, `search`, `search_term`). Falls back to using the first long string value if no known keys match.

3. **Stronger prompt**: Explicitly instructs Gemini to return raw JSON with no markdown fences and uses double-brace escaping for the example.

### Verification

After the fix, the same GDPR query decomposed into 4 sub-tasks:
- "Understand GDPR Article 32 requirements"
- "Identify internal policies for data security measures"
- "Review past breach incident reports"
- "Analyze alignment and gaps"

This directly led to finding breach incident data that was completely missed before.

---

## Issue 2: Duplicate Chunks Across Sub-Tasks

### Symptom

After fixing the Orchestrator, the reranked results contained identical chunks occupying multiple of the top-5 slots. For example, the GDPR query showed the same `incident_response_policy.md` chunk repeated 3 times in the top 5.

### Diagnosis

The `RetrieverAgent.execute()` method had a deduplication set (`seen_contents`) that was local to each sub-task loop iteration:

```python
for task in sub_tasks:
    seen_contents: set[str] = set()  # Reset every iteration!
    ...
```

Each sub-task retrieved 20 chunks independently, and many of the same documents were relevant to multiple sub-tasks. Since deduplication reset between sub-tasks, the same chunk could appear 3-4 times in the combined results.

### Impact

With 4 sub-tasks retrieving 20 chunks each, the reranker received 80 chunks but many were duplicates. The top-5 slots were wasted on repeated content, crowding out diverse evidence. The GDPR query's top 5 had only 2 unique chunks.

### Fix

Lifted the deduplication set outside the loop as `global_seen`:

```python
global_seen: set[str] = set()
for task in sub_tasks:
    for chunk in local_results:
        key = chunk["content"][:200]
        if key not in global_seen:
            global_seen.add(key)
            all_chunks.append(chunk)
```

### Verification

After the fix, the same query went from 80 chunks to 25 unique chunks for reranking. All 5 reranked slots contained distinct documents from different sources, and the Kubernetes query found both RBAC incidents AND secrets management incidents (previously it only found one type).

---

## Issue 3: DuckDuckGo Rate Limiting (Web Search Returning 0 Results)

### Symptom

Initial queries returned 3 web results from DuckDuckGo successfully. All subsequent queries returned 0 web results. The terminal showed:

```
Web search attempt 1 failed: https://lite.duckduckgo.com/lite/ 202 Ratelimit
Web search attempt 2 failed: https://lite.duckduckgo.com/lite/ 202 Ratelimit
Web search attempt 3 failed: https://html.duckduckgo.com/html 202 Ratelimit
```

### Diagnosis

DuckDuckGo aggressively rate-limits automated requests. The original implementation made one web search per sub-task (3-4 calls in quick succession), which quickly triggered IP-based rate limiting. Even with retry logic and exponential backoff, the rate limit window persisted.

An intermediate fix using `googlesearch-python` (Google scraping) also failed silently -- likely blocked or returning empty results.

### Fix

Switched to **Serper.dev API** (Google Search API) which provides reliable, authenticated access:

```python
resp = requests.post(
    "https://google.serper.dev/search",
    headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
    json={"q": query, "num": max_results},
)
```

Also restructured the retrieval flow: instead of one web search per sub-task, the system now makes a **single web search** using the original user query, then only local hybrid searches per sub-task. This minimizes API calls while still supplementing local results with web knowledge.

### Verification

After switching to Serper, web search consistently returns 5 results. The GDPR query now includes evidence from academic papers (ScienceDirect) and compliance guides (Kiteworks) alongside internal documents.

---

## Issue 4: Negative Cross-Encoder Scores (Confusing Display)

### Symptom

The reranked chunks displayed negative scores like `-0.07`, `-1.05`, `-2.56`. While the ranking was correct (higher = better), negative scores appeared broken in the UI and made it hard to judge quality.

### Diagnosis

The `ms-marco-MiniLM-L-6-v2` cross-encoder outputs raw logits that range from roughly -11 to +11. A score near 0 indicates moderate relevance. The scores were functionally correct for ranking purposes, but unintuitive for display.

### Fix

Applied sigmoid normalization to convert logits to a 0-1 probability range:

```python
def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))
```

Score mapping examples:
- Raw `-2.56` becomes `0.07` (low relevance)
- Raw `-0.07` becomes `0.48` (moderate relevance)
- Raw `2.72` becomes `0.94` (high relevance)

The ranking order is preserved since sigmoid is monotonic.

### Verification

After normalization, the GDPR query shows intuitive scores: `0.94`, `0.80`, `0.64`, `0.54`, `0.50`. These are immediately interpretable -- higher is better, 1.0 is a perfect match.

---

## Issue 5: .env Changes Not Triggering Backend Reload

### Symptom

After adding `SERPER_API_KEY` to `.env`, the backend still showed "Web search skipped: SERPER_API_KEY not set" despite the key being present in the file.

### Diagnosis

Uvicorn's `--reload` flag watches for changes to Python files in the backend directory. The `.env` file is at the project root and is not in the watch path. Config values are loaded at module import time via `python-dotenv`, so they are only re-read when uvicorn reloads the process.

### Fix

Touching a backend Python file (e.g., `config.py`) forces uvicorn to reload and re-read the `.env`:

```powershell
(Get-Item "backend\app\config.py").LastWriteTime = Get-Date
```

For future development: changes to `.env` always require a server restart or a touch of any `.py` file to take effect.

---

## Issue 6: Validator JSON Parsing (Same Pattern as Orchestrator)

### Symptom

Not directly observed as a failure because the fallback (keeping all chunks) masked the issue, but the same fragile JSON parsing pattern from the Orchestrator existed in the Validator agent.

### Diagnosis

The Validator expected Gemini to return a bare JSON array like `[5, 3, 1, 4, 2]`, but Gemini sometimes wraps responses in markdown code fences. The original code only handled the `startswith("```")` case.

### Fix

Applied the same robust regex-based extraction pattern:

```python
def _extract_scores(text: str) -> list[int]:
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    bracket_match = re.search(r"\[[\d\s,]+\]", text)
    if bracket_match:
        text = bracket_match.group(0)
    return json.loads(text)
```

---

## Summary of Evolution

| Version | Orchestrator | Retriever | Reranker | Web Search | Result Quality |
|---------|-------------|-----------|----------|------------|----------------|
| v1 (initial) | Broken (fallback to single task) | No cross-task dedup | Raw negative logits | DuckDuckGo (worked initially) | Single-pass RAG, missed cross-domain evidence |
| v2 (orchestrator fix) | Working (3-4 sub-tasks) | Duplicates in results | Raw negative logits | DuckDuckGo (rate-limited) | Multi-agent but duplicate-heavy |
| v3 (dedup fix) | Working | Cross-task dedup | Raw negative logits | DuckDuckGo (rate-limited) | Diverse evidence, no web |
| v4 (final) | Working | Cross-task dedup | Sigmoid-normalized 0-1 | Serper.dev (reliable) | Full multi-agent with web + local |
