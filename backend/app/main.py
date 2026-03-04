from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import init_dependencies, router
from app.config import CHUNK_OVERLAP, CHUNK_SIZE, DATA_DIR
from app.rag.hybrid_search import HybridSearch
from app.rag.ingest import ingest_directory
from app.rag.vector_store import VectorStore
from app.storage.history import QueryHistory


workflow_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global workflow_instance

    print("=" * 60)
    print("MEKA - Multi-Agent Expert Knowledge Assistant")
    print("Security Incident & Compliance Domain")
    print("=" * 60)

    print("\n[1/4] Initializing vector store...")
    vector_store = VectorStore()
    existing_count = vector_store.get_collection_count()

    print(f"\n[2/4] Ingesting documents (existing: {existing_count} chunks)...")
    if existing_count == 0:
        doc_count, all_chunks = ingest_directory(
            DATA_DIR, vector_store, CHUNK_SIZE, CHUNK_OVERLAP
        )
    else:
        print(f"  Using existing index with {existing_count} chunks")
        from app.rag.ingest import load_and_chunk_directory
        all_chunks = load_and_chunk_directory(DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP)
        print(f"  Loaded {len(all_chunks)} chunks for BM25 index")

    print("\n[3/4] Building hybrid search index...")
    hybrid_search = HybridSearch(vector_store)
    if all_chunks:
        hybrid_search.build_bm25_index(all_chunks)
        print(f"  BM25 index built with {len(all_chunks)} chunks")
    else:
        print("  Warning: No chunks available for BM25 index")

    print("\n[4/4] Initializing agent workflow...")
    from app.agents.workflow import MEKAWorkflow
    workflow_instance = MEKAWorkflow(hybrid_search)

    history = QueryHistory()
    init_dependencies(workflow_instance, history)

    print("\n" + "=" * 60)
    print("MEKA is ready! API available at http://localhost:8000")
    print("=" * 60 + "\n")

    yield

    print("Shutting down MEKA...")


app = FastAPI(
    title="MEKA - Multi-Agent Expert Knowledge Assistant",
    description=(
        "A multi-agent system for security incident and compliance knowledge retrieval. "
        "Uses hybrid search (semantic + BM25), cross-encoder reranking, and collaborative "
        "agent orchestration via LangGraph."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
