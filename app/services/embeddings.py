from google import genai
from google.genai import types

from app.core.config import settings


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Create 768-dimensional document embeddings using Vertex AI."""
    if not texts:
        return []

    if not settings.GOOGLE_CLOUD_PROJECT:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT must be configured.")

    client = genai.Client(
        enterprise=True,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_LOCATION,
    )
    vectors: list[list[float]] = []
    batch_size = settings.EMBEDDING_BATCH_SIZE

    try:
        for offset in range(0, len(texts), batch_size):
            batch = texts[offset:offset + batch_size]
            response = client.models.embed_content(
                model=settings.EMBEDDING_MODEL,
                contents=batch,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=768,
                ),
            )
            if not response.embeddings:
                raise RuntimeError("Vertex AI returned no embeddings.")
            vectors.extend([list(item.values) for item in response.embeddings])
    finally:
        client.close()

    if len(vectors) != len(texts) or any(len(vector) != 768 for vector in vectors):
        raise RuntimeError("Vertex AI returned an unexpected embedding shape.")

    return vectors
