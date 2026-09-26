from datetime import datetime

import httpx

from intel_agent.models import SourceItem, SourceKind
from intel_agent.sources.feeds import parse_feed, within

ARXIV_API = "https://export.arxiv.org/api/query"
AI_CATEGORIES = ("cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.RO", "cs.MA")


def build_query(topic_queries: list[str]) -> str:
    query = "(" + " OR ".join(f"cat:{cat}" for cat in AI_CATEGORIES) + ")"
    if topic_queries:
        query += " AND (" + " OR ".join(topic_queries) + ")"
    return query


async def search_arxiv(
    client: httpx.AsyncClient, topic_queries: list[str], since: datetime, limit: int = 15
) -> list[SourceItem]:
    response = await client.get(
        ARXIV_API,
        params={
            "search_query": build_query(topic_queries),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": str(min(100, limit * 4)),
        },
    )
    response.raise_for_status()
    papers = parse_feed(response.content, "arXiv", SourceKind.PAPER)
    return [paper for paper in papers if within(paper, since)][:limit]
