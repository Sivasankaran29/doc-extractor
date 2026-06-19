

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


