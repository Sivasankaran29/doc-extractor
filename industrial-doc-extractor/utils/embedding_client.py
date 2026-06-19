

from openai import AzureOpenAI
from config import get_settings

_client: AzureOpenAI | None = None


def get_azure_client() -> AzureOpenAI:
    global _client

    if _client is None:
        s = get_settings()

        _client = AzureOpenAI(
            api_key=s.AZURE_OPENAI_API_KEY,
            api_version=s.AZURE_OPENAI_API_VERSION,
            azure_endpoint=s.AZURE_OPENAI_ENDPOINT,
        )

    return _client


def embed_text(text: str) -> list[float]:
    """
    Generate embedding vector for the given text.
    Returns empty list for blank text.
    """

    if not text.strip():
        return []

    client = get_azure_client()
    s = get_settings()

    response = client.embeddings.create(
        input=text[:8000],  # truncate large text
        model=s.azure_embedding_deployment_name
    )

    return response.data[0].embedding

def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two embedding vectors.
    Returns a float in [-1.0, 1.0]. Used to build semantic graph edges.
    """
    import math

    if not vec_a or not vec_b:
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a ** 2 for a in vec_a))
    mag_b = math.sqrt(sum(b ** 2 for b in vec_b))

    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)

