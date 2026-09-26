from datetime import datetime

import httpx

from intel_agent.models import SourceItem, SourceKind
from intel_agent.sources.feeds import clean_text, parse_date

HF_DAILY_PAPERS_API = "https://huggingface.co/api/daily_papers"


def _paper_item(entry: dict[str, object]) -> tuple[SourceItem, datetime | None] | None:
    paper = entry.get("paper")
    if not isinstance(paper, dict):
        return None
    paper_id = paper.get("id")
    title = paper.get("title") or entry.get("title")
    if not isinstance(paper_id, str) or not isinstance(title, str):
        return None
    published = parse_date(str(paper.get("publishedAt") or "") or None)
    featured = parse_date(str(paper.get("submittedOnDailyAt") or "") or None)
    authors = paper.get("authors")
    upvotes = paper.get("upvotes")
    item = SourceItem(
        title=clean_text(title, limit=300),
        url=f"https://huggingface.co/papers/{paper_id}",
        source="Hugging Face Papers",
        kind=SourceKind.PAPER,
        published=published,
        summary=clean_text(str(paper.get("summary") or "")),
        authors=[
            a["name"]
            for a in (authors if isinstance(authors, list) else [])
            if isinstance(a, dict) and isinstance(a.get("name"), str)
        ],
        score=float(upvotes) if isinstance(upvotes, int | float) else None,
    )
    latest = max((d for d in (published, featured) if d is not None), default=None)
    return item, latest


async def trending_papers(
    client: httpx.AsyncClient,
    since: datetime,
    keywords: list[str] | None = None,
    limit: int = 15,
) -> list[SourceItem]:
    response = await client.get(HF_DAILY_PAPERS_API, params={"limit": "100"})
    response.raise_for_status()
    payload = response.json()
    results: list[SourceItem] = []
    for entry in payload if isinstance(payload, list) else []:
        parsed = _paper_item(entry) if isinstance(entry, dict) else None
        if parsed is None:
            continue
        item, latest = parsed
        if latest is None or latest < since:
            continue
        text = f"{item.title} {item.summary}".lower()
        if keywords and not any(k.lower() in text for k in keywords):
            continue
        results.append(item)
    results.sort(key=lambda p: p.score or 0, reverse=True)
    return results[:limit]
