# NovaCart Intelligence Layer — Multi-Hop Business Question Answering

A self-contained AI system that answers complex business questions about orders, refunds, support tickets, supplier quality, and warehouse operations by retrieving and synthesizing evidence from a multi-source vector database.

## What This System Does

Given a business question like *"Why did refunds spike in January 2024?"* or *"What warehouse and supplier issues affected order fulfillment?"*, the system autonomously:

1. **Plans** which data sources to query (orders, refunds, tickets, suppliers, warehouse logs)
2. **Retrieves** relevant records using semantic search with metadata filtering
3. **Chains evidence** across multiple sources to synthesize a complete answer
4. **Cites sources** with record IDs so every claim is traceable
5. **Reports limitations** when evidence is insufficient

The system is designed for interactive demo and prototype validation, with a clear upgrade path to production scale.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI + X-API-Key Auth                     │
├─────────────────────────────────────────────────────────────────┤
│  POST /chat          POST /documents/upload      GET /health    │
├─────────────────────────────────────────────────────────────────┤
│         RetrievalAgent (OpenRouter + Tool Calling)              │
│                                                                   │
│  Phase 1: Planning (LLM decides which tools to call)            │
│  Phase 2: Tool Execution (search_orders, search_refunds, etc.)  │
│  Phase 3: Synthesis (LLM chains evidence + cites sources)       │
├─────────────────────────────────────────────────────────────────┤
│         Retrieval Layer (Semantic Search + Filtering)           │
│  - Query embedding via local sentence-transformers              │
│  - Metadata filters: source_type, date_range                    │
│  - Returns: record_id, source_type, text, distance, metadata    │
├─────────────────────────────────────────────────────────────────┤
│    Chroma Vector Store (SQLite Persistence)                     │
│    - 22 indexed records across 5 types                          │
│    - One chunk per atomic record                                │
│    - Indexed with date_int (YYYYMMDD) for range filtering       │
├─────────────────────────────────────────────────────────────────┤
│  Ingestion Pipeline (Load → Chunk → Embed → Index)              │
│  - Loader: reads 5 JSON files                                   │
│  - Chunker: one chunk per record, text + metadata               │
│  - Embedding: sentence-transformers all-MiniLM-L6-v2 (384-dim)  │
│  - Indexing: persist to ./chroma_data                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) | Local, no quota limits, fast iteration. *Production: OpenAI text-embedding-3-large for better semantic quality.* |
| **Vector Store** | Chroma (SQLite backend) | Embedded, persistent, zero external deps. *Production: Pinecone/Elasticsearch for scale + SaaS reliability.* |
| **Reasoning LLM** | OpenRouter with fallback array | Free-tier compatible (meta-llama/llama-3.3-70b + deepseek/deepseek-chat). Auto-fallback on rate limit. *Production: Claude 3.5 Sonnet or GPT-4o for deeper reasoning.* |
| **API Framework** | FastAPI | Type-safe, fast, built-in dependency injection for auth. |
| **Auth** | X-API-Key header | Simple, sufficient for demo. *Production: OAuth 2.0 + RBAC.* |
| **Testing** | pytest (46 tests) | Unit tests for ingestion, retrieval, API, agent citation. |

---

## Quick Start

### Prerequisites
- Python 3.14+
- 2GB disk (for embeddings model cache + Chroma data)
- OpenRouter API key (free tier works)

### Installation

```bash
# Clone repo
git clone <repo-url>
cd NovaCart-Horrazon\ AI

# Copy .env template
cp .env.example .env

# Fill in your API keys
# OPENROUTER_API_KEY=sk-or-v1-...
# API_KEY=your-demo-api-key-here

# Install dependencies
pip install -r requirements.txt

# (Optional) Ingest sample data
python3 -m app.ingestion.pipeline
# Output: "Indexed 22 chunks total"

# Start server
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker Compose (Recommended)

```bash
docker-compose up
# Server available at http://localhost:8000
```

---

## API Examples

### POST /chat — Answer a Question

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-demo-api-key-here" \
  -d '{"question": "Why did refunds spike in January 2024?"}'
```

**Response:**
```json
{
  "answer": "The refunds in January 2024 spiked due to a combination of reasons...",
  "citations": ["REF-001", "REF-002", "REF-003"],
  "tool_calls": [...],
  "model_used": "meta-llama/llama-3.3-70b-instruct"
}
```

### POST /documents/upload — Ingest a Record

```bash
curl -X POST http://localhost:8000/documents/upload \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-demo-api-key-here" \
  -d '{
    "source_type": "order",
    "data": {
      "id": "ORD-999",
      "date": "2024-02-01",
      "customer_id": "CUST-NEW",
      "items": [{"name": "Laptop", "quantity": 1}],
      "total": 1299.99,
      "status": "pending",
      "shipping_address": "999 Future St",
      "warehouse": "SEA-02"
    }
  }'
```

### GET /health — Service Status

```bash
curl http://localhost:8000/health
# Response: {"status": "ok"}
```

---

## Environment Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `OPENROUTER_API_KEY` | Yes | — | OpenRouter API key (free tier at openrouter.ai) |
| `API_KEY` | Yes | — | Single API key for demo (e.g., `my-secret-key`) |
| `CHROMA_PERSIST_DIRECTORY` | No | `./chroma_data` | Path for SQLite vector store |
| `DEBUG` | No | `False` | Enable debug logging |

**.env.example:**
```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
API_KEY=demo-secret-key
CHROMA_PERSIST_DIRECTORY=./chroma_data
DEBUG=False
```

---

## Project Structure

```
.
├── app/
│   ├── main.py                 # FastAPI app + endpoints
│   ├── core/
│   │   ├── config.py          # Settings (Pydantic)
│   │   ├── auth.py            # X-API-Key validation
│   │   ├── models.py          # Request/response dataclasses
│   │   └── validation.py      # Document field validation
│   ├── agent/
│   │   ├── agent.py           # RetrievalAgent (planning + synthesis)
│   │   └── tools.py           # Tool definitions (5 retrieval tools)
│   ├── retrieval/
│   │   └── search.py          # Semantic search + filtering
│   └── ingestion/
│       ├── loader.py          # Load JSON records
│       ├── chunker.py         # Convert record → text + metadata
│       ├── embedding.py       # Embed text (local or API)
│       ├── index.py           # Index chunks into Chroma
│       └── pipeline.py        # Orchestrate full pipeline
├── tests/
│   ├── test_api.py            # FastAPI endpoint tests
│   ├── test_agent.py          # Citation + reasoning tests
│   ├── test_chunker.py        # Ingestion tests
│   ├── test_retrieval.py      # Filtering tests
│   └── test_validation.py     # Input validation tests
├── docs/
│   ├── DESIGN_DECISIONS.md    # Architecture + trade-offs
│   └── architecture-diagram.md # Mermaid diagrams
├── data/
│   ├── orders.json            # 6 synthetic order records
│   ├── refunds.json           # 4 synthetic refund records
│   ├── support_tickets.json   # 4 synthetic ticket records
│   ├── supplier_reports.json  # 3 synthetic quality reports
│   └── warehouse_logs.json    # 5 synthetic warehouse events
├── chroma_data/               # SQLite vector store (auto-created)
├── .env                       # API keys (git-ignored)
├── .env.example               # Template
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container image
├── docker-compose.yml         # Multi-container orchestration
└── README.md                  # This file
```

---

## Testing

```bash
# Run all 46 tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

**Test Coverage:**
- **API Layer (13 tests):** Auth, endpoints, error handling, mocked agent
- **Agent (12 tests):** Citation extraction, prompt generation
- **Ingestion (5 tests):** Chunking, metadata, one-chunk-per-record
- **Retrieval (8 tests):** Filtering by source_type, date range
- **Validation (8 tests):** All 5 source types, required fields

---

## Known Limitations

### Demo Scope
- **Free-tier models** — OpenRouter fallback array has rate limits; production needs paid tier
- **Small dataset** — 22 synthetic records; no real-world data distribution
- **No reranking** — Results ranked by cosine similarity only
- **Single-agent** — No multi-agent debate or refinement loops
- **No frontend** — API and CLI only

### Technical Trade-offs
- **Local embeddings** — Lower quality than OpenAI; no domain fine-tuning
- **Chroma SQLite** — Single-machine only; degrades at 100K+ documents
- **One chunk per record** — Atomic but not suited to large documents
- **No temporal reasoning** — Date filtering exists but limited analytics

---

## Production Upgrade Path

See `docs/DESIGN_DECISIONS.md` for detailed trade-offs and scaling strategies.

**High-level roadmap:**
1. Better embeddings (OpenAI 3-large) + Claude 3.5 Sonnet
2. Pinecone/Weaviate for distributed search
3. Multi-agent debate + task-specific prompts
4. OAuth 2.0 + audit logging
5. Active learning from user feedback

---

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start local server
python3 -m uvicorn app.main:app --reload

# Ingest data
python3 -m app.ingestion.pipeline
```

---

## How to Evaluate This System

**For a demo:**
- Try multi-hop questions: "Why did refunds spike in January 2024?"
- Check citations — every claim should have a record ID
- See source-type filtering in action

**For production readiness:**
- Measure latency: /chat <5s with real data
- Measure accuracy: spot-check answers for correctness
- Identify failure modes: what questions break it?

---

## Support

- **Architecture:** `docs/DESIGN_DECISIONS.md`
- **API docs:** `curl http://localhost:8000/docs` (Swagger UI)
- **Code walkthrough:** See `app/agent/agent.py` (Phase 1–3 loop)

---

**Version:** Phase 6 (API + Auth) + Phase 7 (Docs)  
**Status:** ✅ Demo-ready  
**Last Updated:** 2026-07-29
