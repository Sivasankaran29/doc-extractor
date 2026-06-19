"""
AWS Bedrock client — invokes Claude Sonnet 4.6 via Bedrock global endpoint.
"""
import json
import boto3
from config import get_settings

_client = None


def get_bedrock_client():
    global _client
    if _client is None:
        s = get_settings()
        _client = boto3.client(
            service_name="bedrock-runtime",
            region_name=s.aws_region,
            aws_access_key_id=s.aws_access_key_id,
            aws_secret_access_key=s.aws_secret_access_key,
        )
    return _client


def invoke_claude(prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    """
    Send a prompt to Claude Sonnet 4.6 via AWS Bedrock.
    Returns the text response.
    """
    s = get_settings()
    client = get_bedrock_client()

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system

    response = client.invoke_model(
        modelId=s.bedrock_model_id,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]
