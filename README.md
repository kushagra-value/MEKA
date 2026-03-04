# MEKA — Multi-Agent Expert Knowledge Assistant

A multi-agent system that ingests heterogeneous knowledge sources and answers complex security & compliance queries through collaborative agent orchestration, hybrid retrieval, cross-encoder reranking, and structured reasoning.

## Use Case: Security Incident & Compliance Assistant

MEKA simulates **TechCorp**'s internal knowledge environment — a mid-size company managing security audit reports, incident tickets, compliance policies, and vulnerability advisories. Employees use MEKA to extract cross-domain insights that would otherwise require hours of manual searching across scattered documents.

### Why Multi-Agent Planning Is Required

Unlike simple Q&A retrieval, MEKA's target queries require:

- **Decomposition**: "Summarize all incidents related to OAuth token leakage *and* suggest mitigations" needs both evidence gathering and analytical synthesis.
- **Cross-source correlation**: Linking audit findings to incident tickets to policy documents.
- **Multi-step reasoning**: Finding data, validating relevance, ranking evidence, then producing actionable recommendations.

A single RAG call cannot handle this — it requires planning, delegation, and aggregation.

### Example Queries

| # | Query | What MEKA Does |
|---|-------|----------------|
| 1 | "Summarize all security incidents related to OAuth token leakage and suggest mitigations" | Decomposes into incident search + root cause analysis + mitigation lookup. Retrieves from audit reports, incident tickets, and OAuth guidelines. |
| 2 | "Compare GDPR Article 32 compliance evidence across our policies and past breach incidents" | Searches policy docs for Art. 32 references, finds related breach tickets, cross-references compliance status. |
| 3 | "List all incidents caused by Kubernetes misconfiguration and provide preventive action items" | Finds K8s incidents, correlates with K8s security guide, extracts specific misconfigurations and remediations. |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │Query Input│  │Agent Trace   │  │Result Display          │ │
│  │+ Web Toggle│ │Timeline      │  │Answer + Reasoning +    │ │
│  └──────────┘  └──────────────┘  │Evidence Chunks + Sources│ │
│                                   └────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP (Vite proxy)
┌───────────────────────────▼─────────────────────────────────┐
│                    FastAPI Backend                            │
│  POST /api/query/sync  GET /api/status/:id  GET /api/history │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                  LangGraph Workflow                       │ │
│  │                                                           │ │
│  │  ┌────────────┐    ┌───────────┐    ┌──────────┐        │ │
│  │  │Orchestrator│───▶│ Retriever │───▶│ Reranker │        │ │
│  │  │(Planner)   │    │(Hybrid    │    │(Cross-   │        │ │
│  │  │            │    │ Search)   │    │ Encoder) │        │ │
│  │  └────────────┘    └───────────┘    └────┬─────┘        │ │
│  │                                          │               │ │
│  │                    ┌───────────┐    ┌────▼─────┐        │ │
│  │                    │Summarizer │◀───│Validator │        │ │
│  │                    │(Synthesis)│    │(Relevance│        │ │
│  │                    └───────────┘    │ Filter)  │        │ │
│  │                                     └──────────┘        │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │   Query History   │  │        RAG Pipeline              │ │
│  │   (JSON store)    │  │  ChromaDB + BM25 + Ingest       │ │
│  └──────────────────┘  └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Agent Workflow Sequence

```
User Query
    │
    ▼
┌─────────────────┐
│  ORCHESTRATOR    │  Decomposes query into 2-4 focused sub-tasks
│  (LLM-powered)  │  using Gemini 2.0 Flash for task planning
└────────┬────────┘
         │  sub_tasks[]
         ▼
┌─────────────────┐
│   RETRIEVER      │  For each sub-task:
│                  │  1. Hybrid search (semantic + BM25 via RRF)
│                  │  2. Optional web search (DuckDuckGo)
└────────┬────────┘
         │  all_retrieved_chunks[]
         ▼
┌─────────────────┐
│   RERANKER       │  Cross-encoder (ms-marco-MiniLM-L-6-v2)
│                  │  reorders all chunks by query relevance
│                  │  Selects top-K most relevant
└────────┬────────┘
         │  reranked_chunks[]
         ▼
┌─────────────────┐
│   VALIDATOR      │  LLM scores each chunk's relevance (1-5)
│  (LLM-powered)  │  Filters out chunks scoring < 3
└────────┬────────┘
         │  validated_chunks[]
         ▼
┌─────────────────┐
│  SUMMARIZER      │  LLM synthesizes structured answer:
│  (LLM-powered)  │  Answer + Reasoning + Sources + Confidence
└─────────────────┘
```

---

## Tool Choices & Rationale

| Tool | Choice | Why |
|------|--------|-----|
| **Vector DB** | ChromaDB (persistent) | Lightweight, zero-config, built-in persistence. Sufficient for document-scale datasets without needing a separate service (vs. Qdrant/Milvus). |
| **Embeddings** | `all-MiniLM-L6-v2` (sentence-transformers) | Fast, high-quality 384-dim embeddings that run locally — no API cost for indexing. Strong performance on MS MARCO benchmarks. |
| **Cross-Encoder** | `ms-marco-MiniLM-L-6-v2` | Purpose-built for passage reranking. Significantly improves retrieval precision over bi-encoder scores alone. |
| **Keyword Search** | BM25 (rank_bm25) | Complements semantic search for exact-match terms like CVE IDs, policy numbers, incident IDs that embeddings may miss. |
| **Hybrid Fusion** | Reciprocal Rank Fusion (RRF) | Robust score-agnostic merging of vector and keyword results. Alpha parameter allows tuning semantic vs. keyword weight. |
| **LLM** | Google Gemini 2.0 Flash | Fast, capable model with generous API limits. Used for planning, validation, and summarization — not retrieval. |
| **Agent Framework** | LangGraph | Provides stateful, graph-based agent orchestration with clear node/edge semantics. Supports typed state passing and conditional routing (vs. raw LangChain agents). |
| **Web Search** | DuckDuckGo (duckduckgo-search) | Free, no API key required. Supplements internal knowledge with real-time web information. |
| **Backend** | FastAPI | Async-native, automatic OpenAPI docs, Pydantic validation. Background tasks for long-running queries. |
| **Frontend** | React + Vite | Fast dev experience, component-based UI. Vite proxy simplifies API integration. |

---

## Data Sources

| Source | Format | Description | Why Chosen |
|--------|--------|-------------|------------|
| Security Audit Reports | Markdown | Q1 & Q3 2024 audit findings with CVE references | Core evidence for vulnerability and incident queries |
| Incident Tickets | JSON (20 tickets) | Structured incident data with severity, root cause, resolution | Enables correlation between incidents and audit findings |
| Vulnerability Tracker | CSV (15 entries) | CVE tracking with status and remediation | Structured data demonstrating CSV ingestion and cross-referencing |
| Incident Response Policy | Markdown | P1-P4 classification, escalation procedures | Policy document for compliance queries |
| Data Protection Policy | Markdown | GDPR Article 32, encryption, breach notification | Key document for compliance/GDPR queries |
| K8s Security Guide | Markdown | RBAC, network policies, pod security | Technical reference for K8s-related incidents |
| OAuth Security Guidelines | Markdown | Token lifecycle, PKCE, known vulnerabilities | Technical reference for OAuth-related incidents |

All data is synthetic but cross-referenced (incident tickets reference audit CVEs, policies reference security controls mentioned in guides).

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Google Gemini API key

### Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Copy and edit environment variables
cp ../.env.example ../.env
# Edit .env and add your GOOGLE_API_KEY

# Start the backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

On first startup, MEKA will:
1. Load the sentence-transformer embedding model (~90MB download)
2. Ingest all documents from `data/` into ChromaDB
3. Build the BM25 keyword index
4. Initialize the LangGraph agent workflow

Subsequent startups reuse the persisted ChromaDB index.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

### API Documentation

Once the backend is running, visit http://localhost:8000/docs for interactive Swagger documentation.

---

## API Endpoints

### `POST /api/query/sync`

Synchronous query execution (waits for full result).

**Request:**
```json
{
  "query": "Summarize all OAuth token leakage incidents and suggest mitigations",
  "web_search_enabled": true,
  "user_id": "demo_user"
}
```

**Response:**
```json
{
  "query_id": "uuid",
  "original_query": "...",
  "status": "completed",
  "sub_tasks": [...],
  "agent_trace": [...],
  "reranked_chunks": [...],
  "final_answer": "## OAuth Token Leakage Summary\n...",
  "reasoning": "The analysis connected...",
  "sources": ["documents/security_audit_q1_2024.md", ...]
}
```

### `POST /api/query`

Async query submission (returns immediately, poll status).

### `GET /api/status/{query_id}`

Get full result for a completed query.

### `GET /api/history/{user_id}`

Get query history for a user.

### `GET /api/health`

Health check endpoint.

---

## Trade-offs & Limitations

| Aspect | Trade-off | Mitigation |
|--------|-----------|------------|
| **LLM Dependency** | Orchestrator, Validator, and Summarizer require Google Gemini API | Could swap for local models (Ollama) with config change |
| **ChromaDB Scale** | Not suited for millions of documents | Sufficient for organizational knowledge bases (thousands of docs). Swap to Qdrant/Milvus for production scale. |
| **Synchronous Reranking** | Cross-encoder runs sequentially on all chunks | Batch processing helps; could add GPU acceleration |
| **History Storage** | JSON file, not a database | Adequate for demo; swap to SQLite/PostgreSQL for production |
| **Web Search** | DuckDuckGo may be rate-limited | Graceful fallback — system works without web results |
| **Single-threaded BM25** | BM25 index rebuilt on startup | Fast for current data size; could persist with pickle for larger datasets |

---

## Testing Approach

1. **Unit Tests**: Each agent can be tested independently by mocking the LLM and RAG pipeline
2. **Integration Test**: Run sample queries end-to-end and verify:
   - Sub-tasks are created (Orchestrator works)
   - Chunks are retrieved (Retriever + HybridSearch works)
   - Reranking changes order (Reranker works)
   - Low-relevance chunks are filtered (Validator works)
   - Answer references evidence (Summarizer works)
3. **API Tests**: Use FastAPI TestClient to verify endpoint contracts
4. **Frontend**: Manual testing of query submission, agent trace display, and result rendering

---

## AI Tools Used

| Tool | Usage | Justification |
|------|-------|---------------|
| **Claude (Anthropic)** | Structured and Unstructured documents creation | Helped with data creation, documentation |
| **Google Gemini 2.0 Flash** | Runtime LLM for agents | Fast, capable model with generous free tier for task decomposition, validation, and summarization |

---

## Development Environment

- **IDE**: VS-Code
- **OS**: Windows 10
- **Python**: 3.10+
- **Node.js**: 18+
- **Key Libraries**: LangGraph, LangChain, ChromaDB, sentence-transformers, FastAPI, React

---
