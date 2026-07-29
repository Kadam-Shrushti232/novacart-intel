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
    """Index multiple chunks into Chroma in a batch."""
    if not chunks:
        return 0

    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    ids = [chunk.record_id for chunk in chunks]
    texts = [chunk.text for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]
    embeddings = [chunk.metadata.get("_embedding") for chunk in chunks]

    embeddings = [e for e in embeddings if e is not None]
    if embeddings and len(embeddings) == len(chunks):
        collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
    else:
        collection.add(ids=ids, documents=texts, metadatas=metadatas)

    return len(chunks)


def clear_index(collection_name: str = "novacart_docs") -> None:
    """Delete all documents from the collection."""
    try:
        client = get_chroma_client()
        client.delete_collection(name=collection_name)
    except Exception:
        pass
