# Design Decisions — Phase 3 & Beyond

## Embedding Strategy: Local Sentence-Transformers

### Choice
**Local sentence-transformers (all-MiniLM-L6-v2)** instead of OpenAI text-embedding-3-small

### Why for This Project
- **No API quota limits** — Avoids billing/authentication issues during development
- **Deterministic** — Same embeddings every run (no API variance)
- **Fast iteration** — No network latency, runs on CPU in milliseconds
- **Complete offline capability** — Entire pipeline works without external services

### Technical Details
- Model: `all-MiniLM-L6-v2` (distilled BERT, 384 dimensions)
- Loading time: ~1 second (cached after first run)
- Embedding time per chunk: <5ms (22 chunks in <110ms)
- Storage: ~80MB downloaded, ~10MB per session in memory

### Why NOT for Production
1. **Lower quality** — Designed for distillation/efficiency, not semantic depth
   - OpenAI embeddings: 1536 dims, trained on massive web corpus
   - MiniLM: 384 dims, designed to be small
   
2. **Domain-specific degradation** — Not trained on enterprise/operational data
   - Tech support, shipping logistics, refund policies are not in typical BERT corpus
   - Production would fine-tune or use domain-specific models
   
3. **No enterprise SLA** — Local means you handle failures, caching, updates
   - OpenAI offers uptime SLA, rate limiting, usage monitoring
   - Production would want API monitoring and fallbacks

### Production Upgrade Path
For production deployment with 100K+ documents:
```
1. Upgrade to OpenAI text-embedding-3-large (1536 dims)
2. Cache embeddings in Redis/similar for reuse
3. Use Pinecone or Weaviate for distributed search
4. Fine-tune embeddings on domain data (refunds, orders, etc.)
```

---

## Reasoning LLM: Google Gemini Free Tier (Future)

### Choice
**Google Gemini 2.0 Flash (or 1.5 Flash) free tier** instead of Anthropic Claude

### Why for This Project
- **No billing concerns** — Free tier sufficient for demonstration
- **Supports tool use** — Function calling API compatible with our agent design
- **Fast** — Flash models prioritize latency (good for interactive demo)
- **Available now** — No API key quota issues

### Technical Details (Phase 5 implementation)
- Model: `gemini-2.0-flash` or fallback to `gemini-1.5-flash`
- Tool calling: Supported via `tools` parameter in API
- Response format: Structured function calls with arguments

### Why NOT for Production
1. **Reasoning depth** — Claude is stronger at multi-step logic chains
   - Refund disputes need careful reasoning about policies, exceptions, precedent
   - Gemini Flash is optimized for speed, not reasoning depth
   
2. **Reliability** — Claude has longer track record for enterprise reasoning
   - Claude 3+ family > Gemini for complex business logic
   
3. **Cost at scale** — Free tier has usage limits
   - 100K documents × 5 queries/day × 30 days = 15M API calls/month
   - Would hit free tier quota immediately
   
4. **Fine-tuning** — Claude allows fine-tuning for domain adaptation
   - Gemini fine-tuning less mature

### Production Upgrade Path
For production agent with complex multi-hop reasoning:
```
1. Upgrade to Claude 3.5 Sonnet or Claude 4
2. Implement few-shot prompting with example chains
3. Add task-specific system prompts for refund/order logic
4. Fine-tune on historical agent interactions
5. Add monitoring/guardrails for high-stakes decisions (large refunds, disputes)
```

---

## Chunking Strategy: One Chunk Per Record

### Decision
**One chunk = one database record** (not fixed-size, not document-level)

### Why
1. **Data structure** — Records are atomic (order, refund, ticket, quality report, log)
2. **Retrieval precision** — Phase 5 agent needs 1:1 mapping between chunks and sources to cite
3. **Metadata granularity** — Each chunk has consistent, complete metadata
4. **Multi-hop capability** — Clear boundaries enable reasoning across types

### Trade-offs Accepted
- Records with missing fields (None → empty string for Chroma)
- Duplicate IDs handled by suffix (REF-003#1) to satisfy Chroma uniqueness constraint
- No splitting of large records (none exceed 400 chars, so no issue here)

### For Production
- Same strategy if records stay short (<500 tokens)
- If records grow (e.g., full ticket threads), revisit to fixed-size + overlap
- Hybrid approach: fixed-size for large docs, atomic for small structured records

---

## Vector Store: Chroma with SQLite Persistence

### Choice
**Chroma embedded (SQLite backend)** instead of Pinecone/Weaviate/Elasticsearch

### Why
- **Zero external dependencies** — Runs inside app container
- **Persistent** — SQLite survives container restarts
- **Complete package** — Includes indexing, retrieval, filtering
- **Suitable for demo** — 22 chunks query in <100ms

### Trade-offs
- **Single-machine** — No distributed search/replication
- **No scaling** — Performance degrades >100K chunks
- **Manual backups** — No SaaS reliability

### Production Upgrade Path
```
For 100K+ documents:
1. Migrate to Pinecone (managed, scales horizontally)
2. Keep Chroma as local cache for frequent queries
3. Add Redis for metadata/filtering layer
4. Implement refresh job (nightly re-index)

For 1M+ documents:
1. Use Elasticsearch + custom vector plugin
2. Implement sharding across clusters
3. Add replication for availability
```

---

## Auth: Single API Key

### Choice
**Hardcoded API key** (one per environment) checked via header

### Why
- **Simple** — No user database, session management
- **Sufficient for demo** — Only developer uses it
- **FastAPI native** — Dependency injection handles it

### What This Gives Up
- No user isolation (all queries attributed to same "user")
- No audit trail per user
- No rate limiting per user
- No fine-grained permissions

### Production Upgrade Path
```
1. OAuth 2.0 or OIDC (external identity provider)
2. JWT tokens with scopes (read orders, write refunds, etc.)
3. Role-based access control (RBAC)
4. Audit logging per user action
5. Rate limiting per user/API key
```

---

## Testing: Pytest Unit + Manual Integration

### Phase 3 Coverage
- ✓ Chunker (metadata extraction, text conversion)
- ✓ Semantic search (query against real index)
- ✓ Persistence (index survives restart)
- ✓ Inconsistency detection (duplicate IDs, missing fields, outdated policies visible in results)

### Phase 5 + Production
- Add agent reasoning tests (multi-hop chains, citation accuracy)
- Add error handling tests (missing docs, API failures)
- Add performance tests (query latency, indexing time)
- Add integration tests (end-to-end questions with expected sources)

---

## Known Limitations

### Phase 3
- No reranking (all results equally weighted by cosine similarity)
- No metadata-based filtering UI (can filter in code, not exposed to user)
- No multi-language support (assumes English)

### Phase 4 & Beyond
- No hybrid search (keyword + semantic)
- No named entity recognition (e.g., "John Smith" not linked to customer_id)
- No cross-record joins (e.g., "all orders from customer X")
- No temporal reasoning (e.g., "refunds after X policy change")

---

## Summary Table

| Component | Demo Choice | Production Choice | Why Different |
|-----------|-------------|-------------------|---------------|
| Embeddings | Local sentence-transformers (384-dim) | OpenAI 3-large (1536-dim) + fine-tuning | Quality & domain fit |
| Reasoning LLM | Gemini Flash (free) | Claude 3.5 Sonnet or GPT-4 | Reasoning depth & reliability |
| Vector Store | Chroma SQLite | Pinecone or Elasticsearch | Scale & reliability |
| Auth | Single hardcoded key | OAuth 2.0 + RBAC + audit | Multi-user, security, compliance |
| Chunking | One per record | Hybrid: atomic small + fixed-size large | Scalability |

---

## Future Research

1. **Domain-specific embeddings** — Fine-tune on refund policies, order data
2. **Retrieval-augmented generation (RAG)** — Let agent generate new policies from precedent
3. **Temporal reasoning** — Track policy evolution, refund trend analysis
4. **Multi-modal** — Include images (receipts, damage photos) in search
5. **Active learning** — Improve embeddings/agent from user corrections
