import os
from dataclasses import dataclass

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; intel-agent/0.1; +https://github.com/zeeshah24/devin-projects)"
)


@dataclass(frozen=True)
class Settings:
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    fred_api_key: str | None = None
    http_timeout: float = 20.0
    enable_news_search: bool = False
    user_agent: str = DEFAULT_USER_AGENT

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            llm_api_key=os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or None,
            llm_base_url=os.environ.get("LLM_BASE_URL", cls.llm_base_url).rstrip("/"),
            llm_model=os.environ.get("LLM_MODEL", cls.llm_model),
            fred_api_key=os.environ.get("FRED_API_KEY") or None,
            http_timeout=float(os.environ.get("HTTP_TIMEOUT", cls.http_timeout)),
            enable_news_search=os.environ.get("ENABLE_NEWS_SEARCH", "").lower()
            in ("1", "true", "yes"),
            user_agent=os.environ.get("HTTP_USER_AGENT", DEFAULT_USER_AGENT),
        )
