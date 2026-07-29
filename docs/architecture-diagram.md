# Architecture Diagram — NovaCart Intelligence Layer (Phase 6)

## System Overview

```mermaid
graph TB
    User["👤 User (CLI/API Client)"]
    Auth["🔐 Auth Layer<br/>X-API-Key Header"]
    FastAPI["⚡ FastAPI Server<br/>main.py"]
    
    ChatEP["POST /chat<br/>Answer Question"]
    UploadEP["POST /documents/upload<br/>Ingest Record"]
    HealthEP["GET /health<br/>Service Status"]
    
    RetrievalAgent["🤖 RetrievalAgent<br/>3-Phase Loop"]
    
    Phase1["Phase 1: Planning<br/>LLM decides which tools to call"]
    Phase2["Phase 2: Tool Execution<br/>Execute search tools"]
    Phase3["Phase 3: Synthesis<br/>LLM chains evidence + cites"]
    
    SearchOrders["search_orders<br/>Semantic Search"]
    SearchRefunds["search_refunds<br/>Semantic Search"]
    SearchTickets["search_tickets<br/>Semantic Search"]
    SearchSuppliers["search_suppliers<br/>Semantic Search"]
    SearchLogs["search_warehouse_logs<br/>Semantic Search"]
    
    RetrieverModule["📊 Retrieval Layer<br/>app/retrieval/search.py"]
    
    QueryEmbed["Query Embedding<br/>sentence-transformers"]
    Filter["Metadata Filter<br/>source_type + date_range"]
    ChromaQuery["Chroma Query<br/>Cosine Similarity"]
    
    ChromaStore["🗄️ Chroma Vector Store<br/>SQLite Backend"]
    Vectors["22 Indexed Chunks<br/>384-dim vectors"]
    Metadata["Metadata Index<br/>source_type, date_int, status"]
    
    Ingestion["📥 Ingestion Pipeline<br/>app/ingestion/"]
    
    Loader["Loader<br/>Read JSON"]
    DataFiles["📄 Data Files<br/>5 source types"]
    
    Chunker["Chunker<br/>1 chunk/record"]
    Embedding["Embedding<br/>sentence-transformers"]
    Indexer["Indexer<br/>Persist to Chroma"]
    
    Config["⚙️ Config<br/>app/core/"]
    Settings["Pydantic Settings<br/>Load from .env"]
    EnvFile[".env<br/>API Keys"]
    
    User -->|API Call| Auth
    Auth -->|Validated| FastAPI
    
    FastAPI --> ChatEP
    FastAPI --> UploadEP
    FastAPI --> HealthEP
    
    ChatEP --> RetrievalAgent
    
    RetrievalAgent --> Phase1
    Phase1 -->|Plan| Phase2
    Phase2 --> SearchOrders
    Phase2 --> SearchRefunds
    Phase2 --> SearchTickets
    Phase2 --> SearchSuppliers
    Phase2 --> SearchLogs
    
    SearchOrders --> RetrieverModule
    SearchRefunds --> RetrieverModule
    SearchTickets --> RetrieverModule
    SearchSuppliers --> RetrieverModule
    SearchLogs --> RetrieverModule
    
    RetrieverModule --> QueryEmbed
    RetrieverModule --> Filter
    QueryEmbed --> ChromaQuery
    Filter --> ChromaQuery
    
    ChromaQuery --> ChromaStore
    ChromaStore --> Vectors
    ChromaStore --> Metadata
    
    Phase2 -->|Results| Phase3
    Phase3 -->|Answer + Citations| ChatEP
    
    UploadEP --> Ingestion
    Ingestion --> Loader
    Ingestion --> Chunker
    Ingestion --> Embedding
    Ingestion --> Indexer
    
    DataFiles --> Loader
    Loader --> Chunker
    Chunker -->|text + metadata| Embedding
    Embedding -->|embedding vector| Indexer
    Indexer --> ChromaStore
    
    Settings -->|Load| EnvFile
    Settings ---|Used by| RetrievalAgent
    Settings ---|Used by| FastAPI
    
    style User fill:#e1f5ff
    style Auth fill:#fff3e0
    style FastAPI fill:#f3e5f5
    style RetrievalAgent fill:#e8f5e9
    style Phase1 fill:#fff9c4
    style Phase2 fill:#fff9c4
    style Phase3 fill:#fff9c4
    style RetrieverModule fill:#e0f2f1
    style ChromaStore fill:#fce4ec
    style Ingestion fill:#f1f8e9
    style Config fill:#ede7f6
```

---

## Request/Response Flow

### POST /chat (Answer Question)

```mermaid
sequenceDiagram
    participant User
    participant FastAPI
    participant RetrievalAgent
    participant OpenRouter LLM
    participant ChromaVectorStore
    participant Tools
    
    User->>FastAPI: POST /chat<br/>{"question": "Why did refunds spike?"}
    Note over FastAPI: Validate X-API-Key header
    FastAPI->>RetrievalAgent: ask(question)
    
    RetrievalAgent->>OpenRouter LLM: Planning Prompt<br/>(which tools to call?)
    OpenRouter LLM->>RetrievalAgent: TOOL_CALL: search_refunds<br/>TOOL_CALL: search_orders
    
    RetrievalAgent->>Tools: execute search_refunds
    Tools->>ChromaVectorStore: semantic_search(query, filter)
    ChromaVectorStore->>Tools: [REF-001, REF-002, REF-003, ...]
    Tools->>RetrievalAgent: [raw results]
    
    RetrievalAgent->>Tools: execute search_orders
    Tools->>ChromaVectorStore: semantic_search(query, filter)
    ChromaVectorStore->>Tools: [ORD-001, ORD-002, ...]
    Tools->>RetrievalAgent: [raw results]
    
    RetrievalAgent->>OpenRouter LLM: Synthesis Prompt<br/>(chain evidence + cite sources)
    OpenRouter LLM->>RetrievalAgent: "The refunds spiked due to...<br/>(source: REF-001) (source: REF-002)..."
    
    RetrievalAgent->>RetrievalAgent: Extract citations<br/>Regex: \(sources?:\s*([^)]+)\)
    RetrievalAgent->>FastAPI: AgentResponse<br/>{answer, citations, tool_calls, model}
    FastAPI->>User: 200 OK<br/>{"answer": "...", "citations": ["REF-001"], ...}
```

### POST /documents/upload (Ingest Record)

```mermaid
sequenceDiagram
    participant User
    participant FastAPI
    participant Validator
    participant Chunker
    participant Embedding
    participant ChromaIndex
    
    User->>FastAPI: POST /documents/upload<br/>{"source_type": "order", "data": {...}}
    Note over FastAPI: Validate X-API-Key header
    FastAPI->>Validator: Validate fields for source_type
    
    alt Validation Success
        Validator->>FastAPI: ✓ All required fields present
        FastAPI->>Chunker: chunk_record(LoadedRecord)
        Chunker->>Chunker: Convert data to text<br/>Extract metadata (record_id, date_int, etc.)
        Chunker->>Embedding: embed_text(chunk.text)
        Embedding->>Embedding: sentence-transformers<br/>all-MiniLM-L6-v2
        Embedding->>Chunker: [384-dim vector]
        Chunker->>ChromaIndex: index_chunks([chunk with embedding])
        ChromaIndex->>ChromaIndex: Add to Chroma collection<br/>persist to SQLite
        ChromaIndex->>FastAPI: ✓ Indexed 1 chunk
        FastAPI->>User: 201 Created<br/>{"status": "success", "record_id": "ORD-001"}
    else Validation Failure
        Validator->>FastAPI: ✗ Missing fields: date, warehouse, ...
        FastAPI->>User: 400 Bad Request<br/>{"detail": "Missing required fields..."}
    end
```

---

## Component Details

### 1. FastAPI Layer (main.py)

**Endpoints:**
- `GET /health` — No auth, returns `{"status": "ok"}`
- `POST /chat` — Requires X-API-Key, accepts `{"question": "..."}`, returns answer + citations
- `POST /documents/upload` — Requires X-API-Key, accepts document record, ingests to Chroma
- `GET /docs` — Auto-generated Swagger UI

**Error Handling:**
- 401 Unauthorized → Missing X-API-Key header
- 403 Forbidden → Invalid X-API-Key value
- 400 Bad Request → Malformed document (missing required fields)
- 500 Internal Server Error → Embedding/indexing failure
- 502 Bad Gateway → LLM provider unavailable
- 503 Service Unavailable → LLM rate limited or API key not configured

### 2. RetrievalAgent (agent.py)

**Three-Phase Loop:**

1. **Phase 1: Planning**
   - Prompt: "Which tools to call for this question?"
   - LLM output: TOOL_CALL directives (search_orders, search_refunds, etc.)
   - Extracted via regex: `TOOL_CALL: {...json...}`

2. **Phase 2: Tool Execution**
   - Execute each tool call sequentially
   - Tool returns formatted results: `RECORD_ID | SOURCE_TYPE | DATE | DISTANCE | TEXT`
   - Accumulate all results

3. **Phase 3: Synthesis**
   - Prompt: "Chain evidence + cite sources"
   - LLM output: Final answer with (source: X) markers inline
   - Citation extraction via regex: `\(sources?:\s*([^)]+)\)`
   - Return: {answer, citations[], tool_calls[], model_used}

**Model Fallback:**
- Primary: `meta-llama/llama-3.3-70b-instruct`
- Fallback: `deepseek/deepseek-chat`
- If primary rate-limits, automatically retry with secondary model

### 3. Retrieval Layer (search.py)

**semantic_search(query, collection_name, n_results, source_types, date_range):**

1. **Embed query** using local sentence-transformers
2. **Build metadata filter** from source_types + date_range
   - source_type: `{"source_type": "refund"}` or `{"$or": [...]}`
   - date_range: `{"$and": [{"date_int": {"$gte": 20240101}}, ...]}`
3. **Query Chroma** with cosine similarity + where clause
4. **Format results** with record_id, source_type, document text, distance, metadata

**Result Format:**
```python
{
    "id": "REF-001",
    "record_id": "REF-001",
    "source_type": "refund",
    "document": "Refund REF-001 for order ORD-001...",
    "distance": 0.523,  # Cosine similarity (lower = more relevant)
    "metadata": {
        "date": "2024-01-22",
        "date_int": 20240122,
        "customer_id": "CUST-A123",
        "status": "processed",
        ...
    }
}
```

### 4. Chroma Vector Store

**Collection:** `novacart_docs`
- **Vectors:** 22 chunks × 384 dimensions (local embeddings)
- **Documents:** Full chunk text
- **Metadata:** source_type, record_id, date, date_int, status, customer_id, + type-specific fields
- **Storage:** SQLite at `./chroma_data/`

**Filtering Support:**
- Metadata $and, $or, $gte, $lte operators
- date_int field indexed for fast range queries (20240101–20240131)

### 5. Ingestion Pipeline

**End-to-End:** Load → Chunk → Embed → Index

```
app/ingestion/
├── loader.py        Reads 5 JSON files, yields LoadedRecord(data, source_type)
├── chunker.py       Converts record → text (readable format) + metadata
├── embedding.py     Embeds text using sentence-transformers (local, cached)
├── index.py         Indexes chunks into Chroma with metadata
└── pipeline.py      Orchestrates full pipeline (load 22 records, chunk, embed, index)
```

**Metadata Extraction (per source_type):**
- All types: record_id, date, source_type, status, category
- Order: warehouse, customer_id
- Refund: order_id, reason, customer_id, policy_version
- Ticket: category, priority, customer_id
- Supplier: supplier_name, product_sku, batch_id, defect_rate
- Warehouse: warehouse_id, order_id, event_type

### 6. Configuration (config.py)

**Pydantic BaseSettings:**
- Loads environment variables from `.env` file
- Supports case-insensitive field names
- Fields: `api_key`, `openrouter_api_key`, `chroma_persist_directory`, `debug`

**Usage:**
```python
from app.core.config import get_settings
settings = get_settings()
api_key = settings.openrouter_api_key  # From .env or environment
```

---

## Data Flow: Question → Answer

```
User Question
    ↓
1. Pydantic validation (question not empty)
    ↓
2. RetrievalAgent.ask() entry point
    ↓
3. Phase 1: Planning LLM prompt
   "Which tools to call?" → TOOL_CALL directives
    ↓
4. Phase 2: Execute tools (search_orders, search_refunds, etc.)
   For each tool:
   a) Execute tool with query + filters
   b) Chroma: embed query → cosine similarity → return top-5 results
   c) Format results as text
    ↓
5. Phase 3: Synthesis LLM prompt
   "Chain evidence + cite sources" → Answer with (source: X) markers
    ↓
6. Citation extraction
   Regex: \(sources?:\s*([^)]+)\) → List of record IDs
    ↓
7. Return AgentResponse
   {answer, citations[], tool_calls[], model_used}
    ↓
8. FastAPI serializes to JSON
    ↓
User sees answer + citations
```

---

## Deployment Topology

### Development (Local)

```
Laptop (macOS/Linux/Windows)
├── Python 3.14
├── FastAPI uvicorn (port 8000)
├── Chroma SQLite (./chroma_data/)
├── sentence-transformers cache (~80MB)
└── .env (API keys)
```

### Docker (Production-Ready)

```
Docker Host
└── docker-compose up
    ├── novacart_api (Port 8000)
    │   ├── Python 3.14
    │   ├── FastAPI + uvicorn
    │   ├── /app (code mounted)
    │   └── /data (chroma_data mounted)
    ├── Volume: chroma_data (Persists between restarts)
    └── Network: novacart-net
```

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - API_KEY=${API_KEY}
      - CHROMA_PERSIST_DIRECTORY=/data/chroma_data
    volumes:
      - ./data:/app/data
      - chroma_data:/data/chroma_data
    command: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

volumes:
  chroma_data:
```

---

## Testing Architecture

```mermaid
graph TB
    Tests["pytest tests/"]
    
    APITests["test_api.py<br/>13 tests"]
    APITests --> HealthCheck["GET /health<br/>200 no auth"]
    APITests --> ChatAuth["POST /chat<br/>Auth tests"]
    APITests --> ChatErrors["POST /chat<br/>Error handling"]
    APITests --> UploadValidation["POST /upload<br/>Field validation"]
    
    AgentTests["test_agent.py<br/>12 tests"]
    AgentTests --> CitationExtract["Citation regex<br/>source: X parsing"]
    AgentTests --> PromptGen["Prompt generation<br/>Planning + Synthesis"]
    
    IngestionTests["test_chunker.py<br/>5 tests"]
    IngestionTests --> ChunkCount["1 chunk/record<br/>verified on 22"]
    IngestionTests --> Metadata["Metadata schema<br/>consistent"]
    
    RetrievelTests["test_retrieval.py<br/>8 tests"]
    RetrievelTests --> SourceFilter["Filter by<br/>source_type"]
    RetrievelTests --> DateFilter["Filter by<br/>date_range"]
    
    ValidationTests["test_validation.py<br/>8 tests"]
    ValidationTests --> OrderValidation["Order fields<br/>required"]
    ValidationTests --> RefundValidation["Refund fields<br/>required"]
    
    AllTests["46 tests<br/>All pass ✓"]
    
    APITests --> AllTests
    AgentTests --> AllTests
    IngestionTests --> AllTests
    RetrievelTests --> AllTests
    ValidationTests --> AllTests
```

---

**Diagram Version:** 1.0 (Phase 6 Final)  
**Last Updated:** 2026-07-29
