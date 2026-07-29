import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.models import Chunk
from app.core.config import get_settings


def get_chroma_client():
    """Initialize Chroma client with persistent storage."""
    settings = get_settings()
    chroma_settings = ChromaSettings(
        persist_directory=settings.chroma_persist_directory,
        is_persistent=True,
    )
    return chromadb.Client(chroma_settings)


def index_chunks(chunks: list, collection_name: str = "novacart_docs") -> int:
    """Index multiple chunks into Chroma in a batch.

    Handles duplicate record_ids by generating unique Chroma IDs while preserving
    the original record_id in metadata. This allows Chroma to index all chunks
    while making data quality issues (duplicate IDs) visible to the agent.
    """
    if not chunks:
        return 0

    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    # Generate unique IDs for Chroma (handle duplicates by appending suffix)
    seen_ids = {}
    unique_ids = []
    for chunk in chunks:
        record_id = chunk.record_id
        if record_id in seen_ids:
            # Duplicate ID - append suffix to make it unique for Chroma
            seen_ids[record_id] += 1
            unique_id = f"{record_id}#{seen_ids[record_id]}"
        else:
            seen_ids[record_id] = 0
            unique_id = record_id
        unique_ids.append(unique_id)

    texts = [chunk.text for chunk in chunks]

    # Extract embeddings and clean metadata for Chroma
    embeddings = []
    metadatas = []
    for chunk in chunks:
        metadata = dict(chunk.metadata)  # Copy to avoid modifying original
        embedding = metadata.pop("_embedding", None)

        # Chroma doesn't support None values; convert to empty string
        # (preserves schema while making fields filterable)
        clean_metadata = {}
        for key, value in metadata.items():
            if value is None:
                clean_metadata[key] = ""
            else:
                clean_metadata[key] = str(value)  # Ensure all values are serializable

        metadatas.append(clean_metadata)
        embeddings.append(embedding)

    # Index with embeddings if all chunks have them
    embeddings = [e for e in embeddings if e is not None]
    if embeddings and len(embeddings) == len(chunks):
        collection.add(ids=unique_ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
    else:
        collection.add(ids=unique_ids, documents=texts, metadatas=metadatas)

    return len(chunks)


def clear_index(collection_name: str = "novacart_docs") -> None:
    """Delete all documents from the collection."""
    try:
        client = get_chroma_client()
        client.delete_collection(name=collection_name)
    except Exception:
        pass
