import httpx

from intel_agent.config import Settings


class LLMError(RuntimeError):
    pass


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
        raise LLMError(f"LLM request failed with HTTP {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        raise LLMError(f"LLM request failed: {type(exc).__name__}") from exc
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise LLMError("LLM returned an unexpected response shape") from exc
    if not isinstance(content, str) or not content.strip():
        raise LLMError("LLM returned an empty response")
    return content.strip()
