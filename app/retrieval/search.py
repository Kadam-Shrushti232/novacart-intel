from typing import Optional, List
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import get_settings


def get_chroma_client():
    """Initialize Chroma client for retrieval."""
    settings = get_settings()
    chroma_settings = ChromaSettings(
        persist_directory=settings.chroma_persist_directory,
        is_persistent=True,
    )
    return chromadb.Client(chroma_settings)


def _build_metadata_filter(
    source_types: Optional[List[str]] = None,
    date_range: Optional[tuple[str, str]] = None,
) -> Optional[dict]:
    """Build Chroma metadata filter from source_type and date constraints.

    Args:
        source_types: List of source_type values to include (e.g., ["refund", "order"])
        date_range: Tuple of (start_date, end_date) in YYYY-MM-DD format (inclusive).
                    Converts to YYYYMMDD integers for Chroma numeric range comparison.

    Returns:
        Chroma where clause dict, or None if no filters
    """
    conditions = []

    if source_types:
        if len(source_types) == 1:
            conditions.append({"source_type": source_types[0]})
        else:
            conditions.append({"$or": [{"source_type": st} for st in source_types]})

    if date_range:
        start_date, end_date = date_range
        # Convert YYYY-MM-DD strings to YYYYMMDD integers for Chroma numeric comparison
        try:
            start_int = int(start_date.replace("-", ""))
            end_int = int(end_date.replace("-", ""))
            conditions.append({
                "$and": [
                    {"date_int": {"$gte": start_int}},
                    {"date_int": {"$lte": end_int}},
                ]
            })
        except (ValueError, AttributeError):
            pass  # Skip date filter if conversion fails

    if not conditions:
        return None
    elif len(conditions) == 1:
        return conditions[0]
    else:
        return {"$and": conditions}


def semantic_search(
    query: str,
    collection_name: str = "novacart_docs",
    n_results: int = 5,
    source_types: Optional[List[str]] = None,
    date_range: Optional[tuple[str, str]] = None,
) -> list:
    """Search the index with optional metadata filtering.

    Supports filtering by source_type (order, refund, support_ticket, supplier_report,
    warehouse_log) and date range. Results include record_id and source_type at top level
    for easy integration with Phase 5 agent.

    Args:
        query: Natural language search query
        collection_name: Chroma collection name
        n_results: Number of results to return
        source_types: Filter to specific source types (e.g., ["refund", "order"])
        date_range: Filter to date range, tuple of (start, end) in YYYY-MM-DD format

    Returns:
        List of result dicts: {id, record_id, source_type, document, distance, metadata}
    """
    client = get_chroma_client()
    try:
        collection = client.get_collection(name=collection_name)
    except Exception:
        return []

    where_clause = _build_metadata_filter(source_types=source_types, date_range=date_range)

    kwargs = {
        "query_texts": [query],
        "n_results": n_results,
    }

    if where_clause:
        kwargs["where"] = where_clause

    try:
        results = collection.query(**kwargs)
    except Exception:
        return []

    formatted = []
    if results and results["ids"] and len(results["ids"]) > 0:
        for i, doc_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            formatted.append({
                "id": doc_id,
                "record_id": metadata.get("record_id", doc_id),
                "source_type": metadata.get("source_type", "unknown"),
                "document": results["documents"][0][i] if results["documents"] else "",
                "distance": results["distances"][0][i] if results["distances"] else None,
                "metadata": metadata,
            })

    return formatted
