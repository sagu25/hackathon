"""Shared LLM client — Azure OpenAI or mock fallback."""
import json
from typing import Any

from config import settings

_client = None


def get_client():
    global _client
    if _client is None:
        if settings.is_azure_configured:
            from openai import AzureOpenAI
            _client = AzureOpenAI(
                api_key=settings.azure_openai_api_key,
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
            )
        else:
            _client = "mock"
    return _client


def chat(messages: list[dict], tools: list[dict] | None = None, temperature: float = 0.3) -> dict:
    """Call LLM with optional tool definitions. Returns message dict."""
    client = get_client()

    if client == "mock":
        return _mock_response(messages, tools)

    kwargs: dict[str, Any] = {
        "model": settings.azure_openai_deployment,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    response = client.chat.completions.create(**kwargs)
    msg = response.choices[0].message
    return {
        "role": msg.role,
        "content": msg.content,
        "tool_calls": [
            {
                "id": tc.id,
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in (msg.tool_calls or [])
        ],
    }


def _mock_response(messages: list[dict], tools: list[dict] | None) -> dict:
    """Deterministic mock response when Azure OpenAI is not configured."""
    last = messages[-1].get("content", "")
    content = (
        "Azure OpenAI is not configured. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in your .env file.\n\n"
        f"I received your message: '{last[:100]}...'\n\n"
        "Once configured, I will answer using real AI reasoning over your learning data."
    )
    return {"role": "assistant", "content": content, "tool_calls": []}
