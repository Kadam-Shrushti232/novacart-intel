# Phase 3: Ingestion Pipeline Strategy

## Overview

The ingestion pipeline converts the synthetic dataset (22 records across 5 types) into an indexed, searchable vector store suitable for semantic retrieval and citation in Phase 5.

## Architecture

```
Synthetic Dataset (JSON)
    ↓
Loader (load_records) — yields individual records, tagged by source_type
    ↓
Chunker (chunk_record) — one chunk per atomic record, text + metadata
    ↓
Embedding (embed_text) — OpenAI text-embedding-3-small with retry logic
    ↓
Indexing (index_chunks) — Chroma with persistent local storage
    ↓
Retrieval (semantic_search) — query with metadata filtering
```

## Chunking Strategy: One Chunk Per Record

### Why This Works

**Structured data, not free-text documents:**
- Each record is complete and atomic (order, refund, ticket, report, log)
- No record exceeds ~200 tokens; standard chunking (512-1024) is unnecessary
- Splitting a record would lose required context; merging would mix unrelated data

**Retrieval precision:**
- Multi-hop queries (Phase 5) need precise source citation
- One chunk = one record = one citable source
- Example: "Why did customer CUST-A123 request a refund?" must return only records tied to that customer, not 6 unrelated orders

**Metadata filtering at scale:**
- Each record has clear metadata: customer_id, date, warehouse, category, status
- Enables filtered search: "refunds from January" or "orders from PDX-01 warehouse"
- One chunk per record keeps this granular

## Expected Chunk Counts

| Source Type | Count |
|-------------|-------|
| order | 6 |
| refund | 4 |
| support_ticket | 4 |
| supplier_report | 3 |
| warehouse_log | 5 |
| **Total** | **22** |

## Metadata Schema

Every chunk has these fields (all types):
- `source_type` — order / refund / support_ticket / supplier_report / warehouse_log
- `record_id` — e.g. ORD-001, REF-002
- `date` — ISO string (if present); null otherwise
- `category` — domain-specific: "order", "product_defect", "shipment_processed", etc.
- `status` — "shipped", "pending", "resolved", etc.

Plus source-type-specific fields for filtering and citation.

## How to Run

```bash
# Full ingestion (requires Docker with real API keys in .env)
docker-compose up --build
docker-compose exec app python ingest.py

# Test search
docker-compose exec app python ingest.py search "Defective mouse refund"
```

Expected output:
```
INGESTION COMPLETE
Total chunks indexed: 22

Chunks by source type:
  order                  6 chunks
  refund                 4 chunks
  support_ticket        4 chunks
  supplier_report       3 chunks
  warehouse_log         5 chunks
```

## Verify Chroma Persistence

```bash
# After successful ingestion, verify data persists
ls -lh chroma_data/

# Restart container (index should still exist)
docker-compose down
docker-compose up
docker-compose exec app python ingest.py search "mouse"  # Should still work
```

