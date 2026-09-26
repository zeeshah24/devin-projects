import httpx

from intel_agent.models import SourceItem, SourceKind
from intel_agent.sources.feeds import parse_feed

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"


async def search_news(
    client: httpx.AsyncClient, query: str, days: int, limit: int = 10
) -> list[SourceItem]:
    """Keyword news search via the Google News RSS endpoint (opt-in; see README)."""
    response = await client.get(
        GOOGLE_NEWS_RSS,
        params={"q": f"{query} when:{days}d", "hl": "en-US", "gl": "US", "ceid": "US:en"},
    )
    response.raise_for_status()
    results: list[SourceItem] = []
    for item in parse_feed(response.content, "Google News", SourceKind.NEWS)[:limit]:
        title, sep, publisher = item.title.rpartition(" - ")
        if sep and title:
            item = item.model_copy(
                update={"title": title, "source": f"{publisher} (via Google News)"}
            )
        results.append(item)
    return results
