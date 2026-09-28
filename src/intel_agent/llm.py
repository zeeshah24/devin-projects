import httpx

from intel_agent.config import Settings

MAX_ERROR_DETAIL = 300


class LLMError(RuntimeError):
    pass


def _error_detail(response: httpx.Response, api_key: str) -> str:
    """Pull the provider's error message out of an OpenAI- or Gemini-style error body."""
    try:
        body: object = response.json()
    except ValueError:
        return ""
    if isinstance(body, list) and body:
        body = body[0]
    error = body.get("error") if isinstance(body, dict) else None
    message = error.get("message") if isinstance(error, dict) else error
    if not isinstance(message, str):
        return ""
    return " ".join(message.replace(api_key, "[redacted]").split())[:MAX_ERROR_DETAIL]


async def complete(client: httpx.AsyncClient, settings: Settings, system: str, user: str) -> str:
    """Call an OpenAI-compatible chat completions endpoint."""
    if not settings.llm_api_key:
        raise LLMError("LLM_API_KEY is not configured")
    try:
        response = await client.post(
            f"{settings.llm_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={
                "model": settings.llm_model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=120.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as exc:
        detail = _error_detail(exc.response, settings.llm_api_key)
        suffix = f": {detail}" if detail else ""
        raise LLMError(f"LLM request failed with HTTP {exc.response.status_code}{suffix}") from exc
    except httpx.HTTPError as exc:
        raise LLMError(f"LLM request failed: {type(exc).__name__}") from exc
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise LLMError("LLM returned an unexpected response shape") from exc
    if not isinstance(content, str) or not content.strip():
        raise LLMError("LLM returned an empty response")
    return content.strip()
