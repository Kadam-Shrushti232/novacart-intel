from typing import Optional
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


def semantic_search(
    query: str,
    collection_name: str = "novacart_docs",
    n_results: int = 5,
    where: Optional[dict] = None,
) -> list:
    """Search the index for documents matching a query."""
    client = get_chroma_client()
    try:
        collection = client.get_collection(name=collection_name)
    except Exception:
        return []

    kwargs = {
        "query_texts": [query],
        "n_results": n_results,
    }

    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    formatted = []
    if results and results["ids"] and len(results["ids"]) > 0:
        for i, doc_id in enumerate(results["ids"][0]):
            formatted.append({
                "id": doc_id,
                "document": results["documents"][0][i] if results["documents"] else "",
                "distance": results["distances"][0][i] if results["distances"] else None,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
            })

    return formatted
