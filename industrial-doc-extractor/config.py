from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # AWS Bedrock
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "global.anthropic.claude-sonnet-4-6"

    # Azure OpenAI (Updated to match what your pipeline calls)
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_API_VERSION: str = "2023-05-15"
    AZURE_OPENAI_ENDPOINT: str = ""
    azure_embedding_deployment_name: str = "text-embedding-ada-002"

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "pdf_extractions"

    # Ollama
    ollama_host: str = "http://ollama-llama3:11434"
    ollama_model: str = "llama3"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
