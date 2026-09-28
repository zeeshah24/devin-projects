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


GEMINI_HOST = "generativelanguage.googleapis.com"


Request = tuple[str, dict[str, str], dict[str, object]]


def _openai_request(settings: Settings, api_key: str, system: str, user: str) -> Request:
    return (
        f"{settings.llm_base_url}/chat/completions",
        {"Authorization": f"Bearer {api_key}"},
        {
            "model": settings.llm_model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
    )


def _gemini_request(settings: Settings, api_key: str, system: str, user: str) -> Request:
    base = settings.llm_base_url.removesuffix("/openai")
    return (
        f"{base}/models/{settings.llm_model}:generateContent",
        {"x-goog-api-key": api_key},
        {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0.2},
        },
    )


def _openai_content(response: httpx.Response) -> object:
    return response.json()["choices"][0]["message"]["content"]


def _gemini_content(response: httpx.Response) -> object:
    parts = response.json()["candidates"][0]["content"]["parts"]
    return "".join(part.get("text", "") for part in parts)


async def complete(client: httpx.AsyncClient, settings: Settings, system: str, user: str) -> str:
    """Call an OpenAI-compatible chat endpoint, or Google's native Gemini API for its host."""
    api_key = settings.llm_api_key
    if not api_key:
        raise LLMError("LLM_API_KEY is not configured")
    gemini = httpx.URL(settings.llm_base_url).host == GEMINI_HOST
    url, headers, payload = (_gemini_request if gemini else _openai_request)(
        settings, api_key, system, user
    )
    try:
        response = await client.post(url, headers=headers, json=payload, timeout=120.0)
        response.raise_for_status()
        content = _gemini_content(response) if gemini else _openai_content(response)
    except httpx.HTTPStatusError as exc:
        detail = _error_detail(exc.response, api_key)
        suffix = f": {detail}" if detail else ""
        raise LLMError(f"LLM request failed with HTTP {exc.response.status_code}{suffix}") from exc
    except httpx.HTTPError as exc:
        raise LLMError(f"LLM request failed: {type(exc).__name__}") from exc
    except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
        raise LLMError("LLM returned an unexpected response shape") from exc
    if not isinstance(content, str) or not content.strip():
        raise LLMError("LLM returned an empty response")
    return content.strip()
