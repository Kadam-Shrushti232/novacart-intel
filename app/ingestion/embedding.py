from sentence_transformers import SentenceTransformer

# Load model once at module level (cache in memory)
_embedding_model = None


def get_embedding_model():
    """Get or initialize the sentence-transformers embedding model.

    Uses 'all-MiniLM-L6-v2' for fast, free local embeddings. No API key required,
    runs on CPU. Suitable for demonstration and development. For production,
    consider OpenAI text-embedding-3-small or other high-quality API embeddings.
    """
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def embed_text(text: str) -> list:
    """Embed text using local sentence-transformers (all-MiniLM-L6-v2).

    Runs on CPU, no API calls required, no quota limits.
    Embedding dimension: 384
    """
    model = get_embedding_model()
    embedding = model.encode(text, convert_to_tensor=False)
    return embedding.tolist()
