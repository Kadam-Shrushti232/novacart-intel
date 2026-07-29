# Design Decisions — Complete System (Phases 1–6)

This document consolidates architectural decisions, trade-offs, and production upgrade paths for the NovaCart Intelligence Layer.

---

## 1. EMBEDDING STRATEGY: Local Sentence-Transformers

### Choice
**Local sentence-transformers (all-MiniLM-L6-v2, 384 dimensions)** instead of OpenAI embeddings

### Why for This Project
- **No API quota limits** — Avoids billing/authentication issues during development and prototyping
- **Deterministic** — Same embeddings every run (no API variance or quota exhaustion)
- **Fast iteration** — No network latency, runs on CPU in milliseconds
- **Complete offline capability** — Entire pipeline works without external services
- **Cost** — Free; suitable for 22-document demo

### Technical Details
- Model: `all-MiniLM-L6-v2` (distilled BERT, 384 dimensions)
- Loading time: ~1 second (cached after first run)
- Embedding time per chunk: <5ms (22 chunks in <110ms)
- Storage: ~80MB model download, ~10MB per session in memory
- Output: 384-dimensional vectors for Chroma indexing

### Why NOT for Production
1. **Lower quality** — Designed for distillation/efficiency, not semantic depth
   - OpenAI embeddings: 1536 dimensions, trained on massive web corpus
   - MiniLM: 384 dimensions, prioritizes speed over quality
   - Production queries on domain-specific data (refunds, logistics) suffer

2. **Domain-specific degradation** — Not trained on enterprise/operational data
   - Tech support, shipping logistics, refund policies not in typical BERT corpus
   - Production would require fine-tuning or domain-specific models (e.g., SentenceTransformers fine-tuned on refund data)

3. **No enterprise SLA** — Local means you handle failures, caching, updates
   - OpenAI offers uptime SLA, rate limiting, usage monitoring
   - Production would want API monitoring and fallbacks

### Production Upgrade Path
```
For 1M+ documents:
1. Upgrade to OpenAI text-embedding-3-large (1536 dimensions) — 10× cost but 30% quality improvement
2. Cache embeddings in Redis/Memcached for reuse across instances
3. Use Pinecone or Weaviate for distributed search and replicas
4. Fine-tune embeddings on domain data (refunds, orders, tickets) via OpenAI fine-tuning API
   - Collect 100+ examples of "query, relevant_record" pairs
   - Run fine-tuning job; saves domain-optimized embedding model
   - Deploy fine-tuned model to production embedding service
```

---

## 2. REASONING LLM: OpenRouter with Fallback Array

### Choice
**OpenRouter (meta-llama/llama-3.3-70b-instruct + deepseek/deepseek-chat as fallback)**

### Why for This Project
- **Free-tier compatible** — OpenRouter free tier supports limited calls per day
- **Automatic fallback** — If primary model rate-limits, instantly try secondary model
- **No billing issues** — Avoids credit card blocks during demo development
- **Supports tool use** — Both models support function calling API for agent design
- **Fast** — Llama 3.3 and DeepSeek optimized for speed (good for interactive demo)

### Technical Implementation
- Primary model: `meta-llama/llama-3.3-70b-instruct` (reasoning + code)
- Fallback model: `deepseek/deepseek-chat` (backup for rate limits)
- Tool calling: Both support structured JSON function calls
- Response format: Extracts TOOL_CALL directives from plan phase, executes tools, synthesizes final answer

### Why NOT for Production
1. **Reasoning depth** — Llama 3.3 is good but Claude/GPT-4 are stronger at multi-step logic chains
   - Refund disputes need careful reasoning about policies, exceptions, precedent
   - Llama 3.3 sometimes confuses related-but-distinct records (REF-001 vs REF-002)
   - Claude 3.5 Sonnet has proven track record on business logic

2. **Reliability** — Free-tier models have rate limits and no SLA
   - Llama/DeepSeek on OpenRouter free: ~20 requests/day per account
   - Would hit limits immediately with production traffic
   - Production needs guaranteed availability

3. **Cost at scale** — Free tier has usage ceiling
   - 100K documents × 5 queries/day × 30 days = 15M API calls/month
   - Free tier provides ~600 requests/month (no buffer)
   - Paid OpenRouter pricing ~$0.003/1K tokens still 100× cheaper than OpenAI

4. **Fine-tuning** — Claude allows fine-tuning for domain adaptation
   - OpenRouter's free models don't expose fine-tuning APIs
   - Production would benefit from refund-specific system prompts + few-shot examples

### Production Upgrade Path
```
For production agent with complex multi-hop reasoning:

Option A (Recommended): Claude Route
1. Upgrade to Claude 3.5 Sonnet (paid, $3/1M input tokens)
   - Superior reasoning on business logic and edge cases
   - Proven track record on complex enterprise reasoning
2. Implement few-shot prompting with 5–10 example chains
   - "When refund reason = 'defective', check product_quality records"
   - "When refund_amount > $500, flag for manager approval"
3. Add task-specific system prompts for refund/order logic
4. Fine-tune on historical agent interactions (if OpenAI API used instead)
5. Add monitoring/guardrails for high-stakes decisions (large refunds, disputes)

Option B (Cost-Optimized): Multi-Model Tiering
1. Keep OpenRouter for simple queries ("Get order details")
2. Use Claude 3.5 for complex multi-hop ("Why did refunds spike?")
3. Implement heuristic router: if query_complexity > threshold, route to Claude
```

---

## 3. CHUNKING STRATEGY: One Chunk Per Record

### Decision
**One chunk = one database record** (not fixed-size, not document-level)

### Why This Works
1. **Data structure** — Records are atomic (order, refund, ticket, quality report, log)
   - Each record is a self-contained unit with all necessary context
   - No record depends on another to be understood

2. **Retrieval precision** — Phase 5 agent needs 1:1 mapping between chunks and sources to cite
   - Agent must cite "according to REF-002" — requires chunks to map cleanly to record IDs
   - If records were merged, agent would cite partial answers incorrectly

3. **Metadata granularity** — Each chunk has consistent, complete metadata
   - record_id, source_type, date, status, customer_id all present per record
   - No partial metadata or missing fields per chunk

4. **Multi-hop capability** — Clear boundaries enable reasoning across types
   - Agent can search orders, then search refunds, then synthesize difference
   - If documents were merged, agent loses ability to reason about document types separately

### Trade-offs Accepted
- **Records with missing fields** — Handled by converting None to empty string for Chroma
  - Allows filtering but loses some semantic information
- **Duplicate IDs** — Handled by suffix (REF-003#1, REF-003#2) to satisfy Chroma uniqueness
  - Visible in results but not in agent output (agent sees record_id only)
- **Large records** — No splitting of large records
  - None in current dataset exceed 400 characters
  - Would revisit if records grow to 1000+ tokens

### For Production
- **Same strategy if records stay short** (<500 tokens per record)
  - Most operational data (orders, tickets, logs) fit this constraint

- **Hybrid approach if records grow** (e.g., full ticket threads with 10+ messages):
  - Atomic chunking for short structured records (order, refund, single-message tickets)
  - Fixed-size (512-token) chunking with overlap for long documents (ticket threads, policies)
  - Metadata field to distinguish chunk type: `is_atomic: true/false`

- **Example production hybrid**:
  ```python
  if source_type == "support_ticket" and len(text) > 500:
      # Use fixed-size chunking
      chunks = split_into_chunks(text, chunk_size=512, overlap=50)
  else:
      # Use atomic chunking
      chunks = [chunk_record(record)]
  ```

---

## 4. VECTOR STORE: Chroma with SQLite Persistence

### Choice
**Chroma embedded (SQLite backend)** instead of Pinecone/Weaviate/Elasticsearch

### Why
- **Zero external dependencies** — Runs inside app container, no managed service required
- **Persistent** — SQLite survives container restarts (data not lost)
- **Complete package** — Includes semantic indexing, retrieval, filtering, all in-process
- **Suitable for demo** — 22 chunks query in <100ms, sufficient for interactive latency
- **Familiar API** — Chroma's where-clause syntax is well-documented and testable

### Trade-offs Accepted
- **Single-machine** — No distributed search/replication across servers
  - OK for demo; production needs multi-region failover
- **No scaling** — Performance degrades beyond 100K chunks
  - Vector similarity search becomes O(n) for large collections
- **Manual backups** — No SaaS disaster recovery; you own backup operations
  - SQLite files must be versioned/backed up manually

### Chroma Metadata Filtering Implementation
**Supported dimensions:**
- `source_type` (required) — one or multiple: "refund", "order", "support_ticket", etc.
- `date_range` (optional) — tuple (start_YYYY-MM-DD, end_YYYY-MM-DD), converted to integers for Chroma range operators

**Why date_int (YYYYMMDD integer)?**
- Chroma's `$gte` and `$lte` operators require numeric fields
- String comparisons don't work correctly for date ranges
- Convert "2024-01-15" → 20240115 at chunk creation time
- Query: `{"$and": [{"date_int": {"$gte": 20240101}}, {"date_int": {"$lte": 20240131}}]}`

**Filter composition in Chroma:**
- Single source_type: `{"source_type": "refund"}`
- Multiple source_types: `{"$or": [{"source_type": "refund"}, {"source_type": "order"}]}`
- Combined (source_type AND date_range): `{"$and": [{...source_type...}, {...date_range...}]}`

### Production Upgrade Path
```
For 100K documents:
1. Migrate to Pinecone (managed, scales horizontally, $0.04 per 1M vectors/month)
   - Upload vectors with metadata (source_type, date_int, customer_id, amount)
   - Use Pinecone's metadata filtering for same query patterns
2. Keep Chroma as local cache for frequent queries (10% of corpus)
3. Add Redis for metadata caching (customer_id → record_ids map)
4. Implement refresh job (nightly re-index from source database)

For 1M+ documents:
1. Use Elasticsearch with vector plugin (opensearch-neural-search)
   - Hybrid search: keyword + semantic
   - Better filtering with aggregations (faceted search)
2. Implement sharding across clusters (by source_type or date range)
3. Add replication for availability (3-node cluster, quorum reads)
4. Implement search cache layer (Redis) for top 1% of queries
```

---

## 5. METADATA FILTERING: source_type + date_range

### Supported Filters
**source_type** (required)
- Values: "order", "refund", "support_ticket", "supplier_report", "warehouse_log"
- Single or multiple via OR logic
- Use case: "Search only in refunds" or "Search in refunds OR warehouse logs"

**date_range** (optional)
- Format: tuple of (start_YYYY-MM-DD, end_YYYY-MM-DD), inclusive
- Use case: "Find all refunds issued in January 2024"
- Converted to integer range for Chroma: 20240101–20240131

### Why These Dimensions
**source_type:**
- Natural separation — 5 document types are independently meaningful
- Agent alignment — Phase 5 agent will have separate tools per type (search_orders, search_refunds, etc.)
- Zero ambiguity — Every chunk has source_type; no null cases

**date_range:**
- Operational queries — "Show me all refunds from last quarter" is common in business
- Scaffolded, not forced — Framework supports it even if not used in Phase 4
- Extensible — Easy to add department, status, customer_id filters later

### What's NOT Filtered (Out of Scope)
- **Reranking** — Semantic relevance is sufficient (not business metric reranking)
- **Hybrid search** — Pure semantic; no keyword fallback ("Wireless Mouse" must be found by embedding)
- **Faceted search** — No "show me counts per department"
- **Nested filters** — No "orders from customers who have pending refunds"
- **Custom scoring** — All results ranked by cosine similarity

---

## 6. AUTH: Single API Key Header

### Choice
**X-API-Key header with single hardcoded value per environment**

### Why
- **Simple** — No user database, session management, token refresh
- **Sufficient for demo** — Only internal team uses system during prototype
- **FastAPI native** — Dependency injection via `APIKeyHeader` built into framework
- **No infrastructure** — No Postgres, no Redis, no auth service to manage

### Implementation
```python
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

@app.post("/chat")
async def chat(request: ChatRequest, api_key: str = Depends(verify_api_key)):
    # api_key is validated; request is trusted
    ...
```

### What This Gives Up
- **No user isolation** — All queries attributed to single "user" (environment)
- **No audit trail per user** — Can't answer "Who asked about refunds on Jan 20?"
- **No rate limiting per user** — Single quota per environment (shared across all calls)
- **No fine-grained permissions** — Can't restrict access to sensitive refund queries

### Production Upgrade Path
```
For multi-user enterprise system:

1. OAuth 2.0 or OIDC (e.g., Auth0, Okta)
   - External identity provider handles login
   - Returns JWT token with user identity + scopes
2. JWT tokens with scopes (audience-specific)
   - Scope: "read:orders", "read:refunds", "write:refunds"
   - Token TTL: 1 hour (refresh token: 7 days)
3. Role-based access control (RBAC)
   - Roles: analyst, manager, executive
   - Analyst can read all; manager can also approve refunds >$500; executive can override
4. Audit logging per user action
   - Log: timestamp, user_id, action, question, result_summary
   - Store in immutable log (append-only)
5. Rate limiting per user/API key
   - 100 queries/day for analysts, 1000/day for managers
   - Implemented via token bucket algorithm (Redis)
```

---

## 7. CITATION STRATEGY: Explicit (source: X) Markers

### How It Works
1. **Synthesis prompt instructs** LLM to cite using explicit markers
2. **LLM outputs** `(source: REF-001)` or `(sources: ORD-001, REF-002)` inline with claims
3. **Regex extraction** finds all citations: `\(sources?:\s*([^)]+)\)`
4. **Parser deduplicates** and sorts: `["ORD-001", "REF-002"]`
5. **API returns** cited_records list alongside answer

### Why NOT Other Approaches
- **Implicit (no markers)** — No way to know if sources were used; hallucinations undetected
- **JSON output format** — Constrains LLM output format; reduces reasoning quality
- **Structured extraction** — Post-hoc parsing of answer to find "REF-003" can match incidental mentions ("Check record REF-003#2")

### Production Enhancements
```
1. Verify cited records exist in vector store
   - Before returning answer, cross-check citations against indexed chunks
   - If citation not found, flag to user: "Unable to verify source REF-999"

2. Citation confidence scores
   - Track token probability of claims containing citations
   - Flag low-confidence claims to user

3. Multi-citation validation
   - For claims citing 3+ sources, verify they're consistent
   - Flag contradictions: "REF-001 says defective; REF-002 says shipping_damage"

4. Source traceability
   - Embed full chunk text + retrieval metadata in API response
   - User can click citation to see exact text (e.g., "Refund REF-001 for order ORD-001... Reason: Defective product...")
```

---

## 8. TESTING STRATEGY: Pytest Unit + Manual Integration

### Current Coverage (46 Tests)
- **API Layer (13 tests):** Auth, endpoints, error handling, mocked agent
  - /chat requires API key → 401
  - /chat with valid key → 200 with real answer
  - /upload malformed record → 400 with field list
  - /health no auth required → 200

- **Agent (12 tests):** Citation extraction, prompt generation
  - `(source: REF-001)` extracts correctly
  - `(sources: ORD-001, REF-002)` deduplicates and sorts
  - Incidental mentions like "Check REF-001" NOT extracted
  - Deduplication: `(source: ORD-001)` + `(source: ORD-001)` → `["ORD-001"]`

- **Ingestion (5 tests):** Chunking, metadata, one-chunk-per-record
  - Chunking produces exactly 1 chunk per record (verified on 22 records)
  - Metadata includes date_int field (YYYYMMDD integer)
  - Missing fields handled gracefully (None → empty string)

- **Retrieval (8 tests):** Filtering by source_type, date range
  - Filter by single source_type: `{"source_type": "order"}`
  - Filter by multiple source_types: OR logic
  - Filter by date range: Chroma integer range operators
  - Combined filters: AND logic

- **Validation (8 tests):** All 5 source types, required fields
  - Order missing `date` → 400 with specific field name
  - Refund missing `order_id` → 400
  - Invalid source_type → 400

### Production Extensions
```
1. Agent reasoning tests
   - Multi-hop chains: Query A → refine query B → synthesize
   - Citation accuracy: All claims have exactly one citation
   - Hallucination detection: Cite records that don't contain claim text

2. Error handling tests
   - Missing documents: Query returns "No data found to verify"
   - API failures: Graceful fallback to secondary model
   - Timeout: Response within SLA (e.g., <10s) even if partial

3. Performance tests
   - Latency: P50 <2s, P99 <5s for /chat on 100K documents
   - Indexing: 1000 documents embedded + indexed in <60s
   - Memory: <2GB heap for 1M embeddings in cache

4. Integration tests
   - End-to-end: Ingest 5 documents → ask question → verify answer cites correct sources
   - Regression: Save golden outputs for 10 sample questions; alert on changes >5% similarity
   - Cross-version: Ensure embeddings stable across dependency updates
```

---

## 9. KNOWN LIMITATIONS (Demo Scope)

### Unavoidable Trade-offs
- **Free-tier model rate limits** — OpenRouter limits ~20 requests/day on free plan
- **Small dataset** — 22 synthetic records don't reflect real-world distribution
- **No reranking** — Results ranked by cosine similarity; no learned ranking
- **Single-agent** — No multi-agent debate or refinement loops
- **No temporal reasoning** — Date filtering exists but agent doesn't infer trends ("refunds increased by 20% YoY")

### Intentionally Out of Scope
- **Reranking** — Semantic relevance sufficient for demo (too expensive for MVP)
- **Hybrid search** — Keyword fallback not needed for synthetic data
- **Named entity recognition** — "John Smith" not linked to customer_id
- **Multi-language support** — English-only for prototype
- **Fine-tuning** — Domain-specific model training deferred to Phase 2+
- **Guardrails** — No checks for harmful outputs (e.g., "approve $1M refund")

---

## 10. PRODUCTION UPGRADE ROADMAP

### Phase 1 (Months 1–2): Embeddings & Reasoning
```
- Migrate to OpenAI text-embedding-3-large (1536-dim)
- Upgrade to Claude 3.5 Sonnet for reasoning
- Fine-tune embeddings on 200+ domain examples
- Add system prompts for refund policy compliance
```

### Phase 2 (Months 2–3): Scale & Reliability
```
- Migrate vector store to Pinecone
- Implement Redis caching for metadata
- Add nightly re-indexing pipeline
- Set up monitoring (latency, error rate, API costs)
```

### Phase 3 (Months 3–4): Multi-Agent & Reasoning
```
- Add debate/refinement loop (agent proposes → critic checks)
- Implement task-specific prompts (refund reasoning, policy compliance)
- Add guardrails for high-stakes decisions (refunds >$500)
- Build evaluation harness (sample 100 Q&A pairs, measure quality)
```

### Phase 4 (Months 4–6): Enterprise Auth & Compliance
```
- OAuth 2.0 + RBAC (Analyst, Manager, Executive roles)
- User-level audit logging (who asked what, when, result summary)
- Rate limiting per user (100 q/day for analysts, 1000 for managers)
- Compliance checks (PII masking, export controls)
```

### Phase 5+ (Ongoing): Continuous Improvement
```
- Active learning from user corrections
- A/B testing of model versions and prompts
- Business metric tracking (answer quality, citation accuracy, user satisfaction)
- Expand reasoning to cross-tenant analytics ("top refund reasons across all customers")
```

---

## Summary Table: Demo vs. Production

| Dimension | Demo Choice | Production Choice | Why Different | Upgrade Effort |
|-----------|-------------|-------------------|---------------|---------|
| **Embeddings** | sentence-transformers (384-dim) | OpenAI 3-large (1536-dim) | Quality | 1 week |
| **Reasoning** | OpenRouter (llama, free-tier) | Claude 3.5 Sonnet | Reliability | 1 day |
| **Vector Store** | Chroma SQLite | Pinecone | Scale | 2 weeks |
| **Auth** | Single API key | OAuth 2.0 + RBAC | Multi-user | 2 weeks |
| **Chunking** | Atomic only | Hybrid (atomic + fixed-size) | Scale | 1 week |
| **Citation** | Explicit (source: X) | Verified + confidence scores | Accuracy | 2 weeks |

---

## Appendix: Interview Defense Checklist

**Q: Why local embeddings instead of OpenAI?**  
A: "For demo prototyping, local embeddings avoid quota limits and billing issues. They're 30% lower quality but sufficient for 22 records. Production would upgrade to OpenAI 3-large (1536-dim) fine-tuned on domain data, gaining both semantic depth and enterprise SLA."

**Q: Why OpenRouter instead of Claude directly?**  
A: "OpenRouter free-tier gives us a working system without API keys. Production would use Claude 3.5 Sonnet directly for superior reasoning, but for rapid iteration on a budget, OpenRouter's auto-fallback (llama → deepseek on rate limit) keeps the demo alive."

**Q: Why one chunk per record?**  
A: "Atomic chunks map 1:1 to record IDs, so the agent can cite sources accurately ('according to REF-002'). For production with larger documents, we'd switch to hybrid chunking: atomic for short structured records, fixed-size for long transcripts."

**Q: How do you scale this to 100K documents?**  
A: "Pinecone replaces Chroma (distributed, managed, SaaS). Redis caches frequent metadata lookups. Embeddings stay frozen after fine-tuning, updated nightly. Vector similarity remains O(1) via hashing."

**Q: What are your biggest limitations?**  
A: "Three: free-tier rate limits (design choice to avoid cost), small synthetic dataset (scope constraint), and single-agent reasoning (multi-agent debate planned for Phase 3). All addressable with planned upgrades."

---

**Document Version:** 2.0 (Consolidated Phases 1–6)  
**Last Updated:** 2026-07-29  
**Author:** NovaCart Intelligence Layer Team
