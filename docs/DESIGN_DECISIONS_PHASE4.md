# Design Decisions — Phase 4: Retrieval Layer with Metadata Filtering

## Metadata Filtering Strategy: source_type + Date

### What We Implemented

**Filter dimensions currently supported:**
1. **source_type** (required for Phase 4)
   - Values: order, refund, support_ticket, supplier_report, warehouse_log
   - Single or multiple (OR logic): `source_types=["refund", "order"]`
   - Use case: "Search only in refunds" or "Search in refunds OR warehouse logs"

2. **date_range** (optional, scaffolded for future use)
   - Format: tuple of (start_YYYY-MM-DD, end_YYYY-MM-DD), inclusive
   - Use case: "Find all shipments delayed in January 2024"
   - Note: Currently requires Chroma's date comparison operators; in production, index date as numeric (timestamp) for range queries

### Why These Dimensions

**source_type:**
- **Natural separation** — Our 5 document types are independently meaningful (orders ≠ refunds ≠ tickets)
- **Phase 5 alignment** — Agent will have separate tools per source type anyway (search_orders, search_refunds, etc.), so filtering here validates that structure
- **Zero ambiguity** — Every chunk has source_type; no null/missing cases to handle

**date_range:**
- **Operational queries** — "Show me all refunds from last quarter" is a common enterprise question
- **Scaffolded, not forced** — Not required in Phase 4, but the framework is there for Phase 5

### Verified Behavior

From TEST 2 output above:
- **Unfiltered "shipment delay"**: 5 results (4 warehouse_log + 1 support_ticket)
- **Filtered "shipment delay" (warehouse_log only)**: 5 results (all warehouse_log; support_ticket dropped)
- **Combined filters (source_types=order AND date=2025)**: 0 results (doesn't exist)

Filter is NOT silently ignored; results genuinely narrows based on metadata.

## Production Extension: From 2 to N Dimensions

To extend this for production, add filters for:

### 1. Department (section 6.1 requirement)
Map to the dataset via category field:
- **Refunds** → Finance/Compliance department
- **Orders** → Sales/Operations department
- **Support tickets** → Customer Service department
- **Supplier reports** → Procurement/Quality department
- **Warehouse logs** → Logistics/Operations department

Implementation:
```python
def semantic_search(
    ...,
    departments: Optional[List[str]] = None,  # New param
    ...
):
    # In _build_metadata_filter:
    if departments:
        dept_to_category = {
            "Finance": ["refund"],
            "Sales": ["order"],
            "CustomerService": ["support_ticket"],
            ...
        }
        allowed_categories = [cat for dept in departments for cat in dept_to_category[dept]]
        conditions.append({"$or": [{"category": c} for c in allowed_categories]})
```

### 2. Amount Range (for orders/refunds)
Requires denormalizing amount into metadata:
- Current: amount is buried in chunk text ("Refund amount: $89.99")
- Production: extract amount during chunking, store as numeric field
- Query: `amount_range=(0, 1000)` returns refunds/orders between $0–$1000

Implementation in chunker:
```python
if source_type == "refund":
    amount = extract_numeric(data.get("total_refund"))  # e.g., 89.99
    metadata["amount"] = amount  # Store as metadata
```

### 3. Status (already partially supported)
Current metadata has status field; just expose it:
```python
def semantic_search(..., statuses: Optional[List[str]] = None):
    if statuses:
        conditions.append({"$or": [{"status": s} for s in statuses]})
```

Example: "Show me pending refunds only" = `source_types=["refund"], statuses=["pending"]`

### 4. Customer ID (for multi-tenant queries)
If this becomes a SaaS product:
```python
def semantic_search(..., customer_id: Optional[str] = None):
    if customer_id:
        conditions.append({"customer_id": customer_id})
```

Ensures tenant isolation: each customer only sees their own data.

## Architecture: Filter Composition in Chroma

Current approach (working, verified):
- **Single source_type**: `{"source_type": "refund"}`
- **Multiple source_types**: `{"$or": [{"source_type": "refund"}, {"source_type": "order"}]}`
- **Multiple filters combined**: `{"$and": [condition1, condition2, ...]}`

Chroma's `where` parameter natively supports this structure, so no additional filtering layer needed.

### Production note
For 100K+ documents with complex queries, consider adding a reranking layer:
1. Semantic search returns top-20 (larger pool)
2. Metadata filter narrows to top-5 (final results)
3. Optional: rerank by business metric (e.g., amount, recency, customer tier)

Currently not needed for 22 documents; becomes important at scale.

## Citation-Ready Format

Each result now returns:
```python
{
    "record_id": "REF-002",           # For agent citation
    "source_type": "refund",           # Document category
    "similarity_score": 0.5675,        # Relevance (0.0-1.0)
    "document": "Refund REF-002...",   # Full chunk text
    "metadata": {...}                  # All indexed fields
}
```

This enables Phase 5 agent to:
- Cite sources: "According to REF-002 (refund)..."
- Filter results: "Found in [source_type]..."
- Reason about documents: "This policy (source_type=refund) contradicts..."

## What's NOT Here (Deliberate Out-of-Scope)

- **Reranking** — semantic relevance is sufficient for Phase 4
- **Hybrid search** — no keyword fallback; pure semantic search
- **Faceted search** — no "show me counts per department"; just binary include/exclude
- **Nested filters** — no "orders from customers who also have refunds"
- **Custom scoring** — all results ranked by cosine distance

These would be Phase 5+ enhancements or production pain-points.

---

## Summary for Interview Defense

**Question:** "How do you handle filtering in the retrieval layer?"

**Answer:** "Metadata filtering is integrated directly into the semantic search via Chroma's `where` parameter. We support source_type (required) and date_range (scaffolded). Single or multiple source types work via OR logic; combined filters use AND. The filter is applied at query time, not post-hoc, so it genuinely narrows results—not silently ignored. Each result returns record_id and source_type at the top level, making it citation-ready for the Phase 5 agent. For production, we'd add department (via category mapping), amount range (via denormalized metadata), customer ID (tenant isolation), and optional reranking at scale."

---

## Test Results (Phase 4 Verification)

| Test | Query | Filter | Results | Notes |
|------|-------|--------|---------|-------|
| 1 | "shipment delay" | None | 5 (4 WH + 1 TKT) | Baseline—mix of types |
| 2 | "shipment delay" | warehouse_log only | 5 (all WH) | Filter works; TKT removed |
| 3 | "shipment delay" | order + future date | 0 | Empty filter confirmed |

