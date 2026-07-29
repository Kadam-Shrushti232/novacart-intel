import time
from openai import OpenAI
from app.core.config import get_settings


def embed_text(text: str, max_retries: int = 1) -> list:
    """Embed text using OpenAI text-embedding-3-small with retry logic."""
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    for attempt in range(max_retries + 1):
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding

        except Exception as e:
            if attempt < max_retries:
                time.sleep(1)
                continue
            else:
                raise RuntimeError(
                    f"Failed to embed text after {max_retries + 1} attempts: {str(e)}"
                ) from e
