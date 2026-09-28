import html
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree.ElementTree import Element

import httpx
from defusedxml.ElementTree import fromstring

from intel_agent.models import SourceItem, SourceKind

SUMMARY_LIMIT = 600


@dataclass(frozen=True)
class FeedSpec:
    name: str
    url: str
    kind: SourceKind
    group: str


TECH_NEWS = "tech_news"
LABS = "labs"
RESEARCH_NEWS = "research_news"
ECONOMY = "economy"

FEEDS: tuple[FeedSpec, ...] = (
    FeedSpec(
        "MIT Technology Review",
        "https://www.technologyreview.com/topic/artificial-intelligence/feed",
        SourceKind.NEWS,
        TECH_NEWS,
    ),
    FeedSpec(
        "TechCrunch",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        SourceKind.NEWS,
        TECH_NEWS,
    ),
    FeedSpec(
        "The Verge",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        SourceKind.NEWS,
        TECH_NEWS,
    ),
    FeedSpec("OpenAI News", "https://openai.com/news/rss.xml", SourceKind.LAB, LABS),
    FeedSpec("Google DeepMind Blog", "https://deepmind.google/blog/rss.xml", SourceKind.LAB, LABS),
    FeedSpec(
        "Microsoft Research", "https://www.microsoft.com/en-us/research/feed/", SourceKind.LAB, LABS
    ),
    FeedSpec(
        "MIT News (AI)",
        "https://news.mit.edu/rss/topic/artificial-intelligence2",
        SourceKind.NEWS,
        RESEARCH_NEWS,
    ),
    FeedSpec(
        "Nature Machine Intelligence",
        "https://www.nature.com/natmachintell.rss",
        SourceKind.PAPER,
        RESEARCH_NEWS,
    ),
    FeedSpec(
        "Federal Reserve",
        "https://www.federalreserve.gov/feeds/press_all.xml",
        SourceKind.GOVERNMENT,
        ECONOMY,
    ),
    FeedSpec(
        "U.S. Bureau of Economic Analysis",
        "https://apps.bea.gov/rss/rss.xml",
        SourceKind.GOVERNMENT,
        ECONOMY,
    ),
)

_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


def clean_text(value: str | None, limit: int = SUMMARY_LIMIT) -> str:
    if not value:
        return ""
    text = _SPACE.sub(" ", html.unescape(_TAG.sub(" ", value))).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    parsed: datetime | None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        parsed = None
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(element: Element, *names: str) -> list[Element]:
    return [child for child in element if _local(child.tag) in names]


def _first_text(element: Element, *names: str) -> str | None:
    for name in names:
        for child in _children(element, name):
            text = "".join(child.itertext()).strip()
            if text:
                return text
    return None


def _link(element: Element) -> str | None:
    fallback: str | None = None
    for child in _children(element, "link"):
        href = child.get("href")
        if href:
            if child.get("rel") in (None, "alternate"):
                return href
            fallback = fallback or href
        elif child.text and child.text.strip():
            return child.text.strip()
    return fallback or element.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about")


def _authors(element: Element) -> list[str]:
    names = [
        name
        for author in _children(element, "author")
        if (name := _first_text(author, "name") or (author.text or "").strip())
    ]
    names.extend(
        (child.text or "").strip() for child in _children(element, "creator") if child.text
    )
    return names


def parse_feed(content: bytes | str, source: str, kind: SourceKind) -> list[SourceItem]:
    """Parse RSS 2.0, RSS 1.0 (RDF) or Atom content into source items."""
    root = fromstring(content)
    items: list[SourceItem] = []
    for element in root.iter():
        if _local(element.tag) not in ("item", "entry"):
            continue
        title = clean_text(_first_text(element, "title"), limit=300)
        url = _link(element)
        if not title or not url:
            continue
        items.append(
            SourceItem(
                title=title,
                url=url,
                source=source,
                kind=kind,
                published=parse_date(_first_text(element, "published", "pubDate", "date"))
                or parse_date(_first_text(element, "updated")),
                summary=clean_text(_first_text(element, "summary", "description", "encoded")),
                authors=_authors(element),
            )
        )
    return items


def matches_terms(item: SourceItem, terms: Iterable[str]) -> bool:
    haystack = f"{item.title} {item.summary}".lower()
    return any(term.lower() in haystack for term in terms)


def within(item: SourceItem, since: datetime) -> bool:
    return item.published is not None and item.published >= since


async def fetch_feed(client: httpx.AsyncClient, spec: FeedSpec) -> list[SourceItem]:
    response = await client.get(spec.url)
    response.raise_for_status()
    return parse_feed(response.content, spec.name, spec.kind)


def feeds_for(groups: Iterable[str]) -> list[FeedSpec]:
    wanted = set(groups)
    return [spec for spec in FEEDS if spec.group in wanted]
