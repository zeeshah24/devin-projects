import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from xml.etree.ElementTree import ParseError

import httpx
from defusedxml import DefusedXmlException

from intel_agent import llm
from intel_agent.config import Settings
from intel_agent.countries import country_terms
from intel_agent.models import (
    AskRequest,
    AskResponse,
    Indicator,
    Intent,
    Mode,
    QueryPlan,
    SourceItem,
)
from intel_agent.planner import TOPIC_KEYWORDS, TOPICS, plan_query
from intel_agent.prompts import SYSTEM_PROMPT, build_user_prompt, format_indicators
from intel_agent.sources import arxiv, fred, hf_papers, news_search, worldbank
from intel_agent.sources.feeds import (
    ECONOMY,
    LABS,
    RESEARCH_NEWS,
    TECH_NEWS,
    FeedSpec,
    feeds_for,
    fetch_feed,
    matches_terms,
    within,
)

JOB_TERMS = ("job", "hiring", "hire", "talent", "workforce", "skills", "layoff", "career", "salar")
ECONOMY_TERMS = ("econom", "inflation", "interest rate", "gdp", "market", "invest", "tariff")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Evidence:
    sources: list[SourceItem] = field(default_factory=list)
    indicators: list[Indicator] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class IntelligenceAgent:
    def __init__(
        self,
        client: httpx.AsyncClient,
        settings: Settings,
        now: Callable[[], datetime] = utcnow,
    ) -> None:
        self.client = client
        self.settings = settings
        self.now = now

    def plan(self, request: AskRequest) -> QueryPlan:
        return plan_query(request, self.now().date())

    async def ask(self, request: AskRequest) -> AskResponse:
        plan = self.plan(request)
        if plan.needs_clarification:
            return AskResponse(
                plan=plan,
                answer=plan.clarification or "",
                sources=[],
                indicators=[],
                llm_used=False,
                warnings=[],
                generated_at=self.now(),
            )

        evidence = await self.gather(plan)
        answer: str | None = None
        if self.settings.llm_api_key:
            try:
                answer = await llm.complete(
                    self.client,
                    self.settings,
                    SYSTEM_PROMPT,
                    build_user_prompt(plan, evidence.sources, evidence.indicators),
                )
            except llm.LLMError as exc:
                evidence.warnings.append(f"{exc}; returning an evidence digest instead.")
        else:
            evidence.warnings.append(
                "LLM_API_KEY is not set; returning an evidence digest without synthesis."
            )
        return AskResponse(
            plan=plan,
            answer=answer or evidence_digest(plan, evidence),
            sources=evidence.sources,
            indicators=evidence.indicators,
            llm_used=answer is not None,
            warnings=evidence.warnings,
            generated_at=self.now(),
        )

    async def gather(self, plan: QueryPlan) -> Evidence:
        since = datetime.combine(plan.period.start, time.min, tzinfo=timezone.utc)
        per_source = 10 if plan.mode is Mode.REPORT else 5
        total = 30 if plan.mode is Mode.REPORT else 12
        topic_queries = [TOPICS[t][1] for t in plan.topics]
        topic_keywords = [k for t in plan.topics for k in TOPIC_KEYWORDS[t]]

        country_codes: list[str] = []
        if plan.country:
            country_codes.append(plan.country.code)
        if plan.compare_country:
            country_codes.append(plan.compare_country.code)
        place_terms = [t for c in country_codes if c != "US" for t in _safe_terms(c)]

        source_tasks: list[tuple[str, Awaitable[list[SourceItem]]]] = []
        indicator_tasks: list[tuple[str, Awaitable[list[Indicator]]]] = []

        def add_feeds(groups: tuple[str, ...], terms: list[str] | None = None) -> None:
            for spec in feeds_for(groups):
                source_tasks.append((spec.name, self._feed(spec, since, per_source, terms or None)))

        def add_indicators(codes: list[str], ids: dict[str, str]) -> None:
            if codes:
                indicator_tasks.append(
                    (
                        "World Bank",
                        worldbank.fetch_indicators(self.client, codes, list(ids)),
                    )
                )

        def add_fred() -> None:
            if self.settings.fred_api_key:
                indicator_tasks.append(
                    ("FRED", fred.fetch_us_macro(self.client, self.settings.fred_api_key))
                )

        def add_arxiv() -> None:
            source_tasks.append(
                ("arXiv", arxiv.search_arxiv(self.client, topic_queries, since, per_source * 2))
            )

        def add_news_search(suffix: str = "") -> None:
            if self.settings.enable_news_search and plan.country:
                days = (plan.period.end - plan.period.start).days + 1
                query = f'"artificial intelligence" "{plan.country.name}"{suffix}'
                source_tasks.append(
                    ("News search", news_search.search_news(self.client, query, days, per_source))
                )

        def add_hf() -> None:
            source_tasks.append(
                (
                    "Hugging Face Papers",
                    hf_papers.trending_papers(self.client, since, topic_keywords, per_source),
                )
            )

        if plan.intent is Intent.RESEARCH_PAPERS:
            add_hf()
            add_arxiv()
            add_feeds((RESEARCH_NEWS,))
        elif plan.intent is Intent.INNOVATIONS:
            add_feeds((LABS, TECH_NEWS, RESEARCH_NEWS), topic_keywords)
            add_hf()
        elif plan.intent in (Intent.COUNTRY_OPPORTUNITIES, Intent.COUNTRY_VS_US):
            add_indicators(
                country_codes,
                worldbank.ECONOMY_INDICATORS | worldbank.TECHNOLOGY_INDICATORS,
            )
            add_news_search()
            add_feeds((TECH_NEWS, LABS), place_terms)
        elif plan.intent is Intent.JOBS:
            add_indicators(
                country_codes or ["WLD"],
                worldbank.LABOR_INDICATORS | worldbank.TECHNOLOGY_INDICATORS,
            )
            add_news_search(" jobs")
            add_feeds((TECH_NEWS,), place_terms or list(JOB_TERMS))
            if "US" in country_codes:
                add_fred()
        elif plan.intent is Intent.ECONOMY:
            add_indicators(country_codes or ["US"], worldbank.ECONOMY_INDICATORS)
            add_feeds((ECONOMY,))
            add_feeds((TECH_NEWS,), place_terms or list(ECONOMY_TERMS))
            if not country_codes or "US" in country_codes:
                add_fred()
        else:
            add_feeds((LABS, TECH_NEWS), topic_keywords or place_terms)
            if plan.topics:
                add_arxiv()
            add_indicators(country_codes, worldbank.ECONOMY_INDICATORS)

        evidence = Evidence()
        source_results = await asyncio.gather(
            *(task for _, task in source_tasks), return_exceptions=True
        )
        indicator_results = await asyncio.gather(
            *(task for _, task in indicator_tasks), return_exceptions=True
        )
        per_source_items: list[list[SourceItem]] = []
        for (name, _), result in zip(source_tasks, source_results, strict=True):
            if isinstance(result, BaseException):
                evidence.warnings.append(f"{name} unavailable ({_describe(result)}).")
                continue
            per_source_items.append(result)
        evidence.sources = _interleave(per_source_items, total)
        for (name, _), result in zip(indicator_tasks, indicator_results, strict=True):
            if isinstance(result, BaseException):
                evidence.warnings.append(f"{name} data unavailable ({_describe(result)}).")
                continue
            evidence.indicators.extend(result)
        if not evidence.sources and not evidence.indicators:
            evidence.warnings.append(f"No evidence found for {plan.period.label}.")
        if plan.country and not evidence.sources and not self.settings.enable_news_search:
            evidence.warnings.append(
                f"No {plan.country.name}-specific articles in the monitored feeds; set "
                "ENABLE_NEWS_SEARCH=1 to add keyword news search."
            )
        return evidence

    async def _feed(
        self, spec: FeedSpec, since: datetime, limit: int, terms: list[str] | None
    ) -> list[SourceItem]:
        items = [i for i in await fetch_feed(self.client, spec) if within(i, since)]
        if terms:
            items = [i for i in items if matches_terms(i, terms)]
        items.sort(key=lambda i: i.published or since, reverse=True)
        return items[:limit]


def _interleave(groups: list[list[SourceItem]], limit: int) -> list[SourceItem]:
    """Round-robin across sources so every source is represented before any is exhausted."""
    seen: set[str] = set()
    merged: list[SourceItem] = []
    for rank in range(max((len(g) for g in groups), default=0)):
        for group in groups:
            if rank < len(group) and group[rank].url not in seen and len(merged) < limit:
                seen.add(group[rank].url)
                merged.append(group[rank])
    return merged


def _safe_terms(code: str) -> list[str]:
    try:
        return country_terms(code)
    except KeyError:
        return []


def _describe(exc: BaseException) -> str:
    """Short, secret-free reason for a source failure; unexpected errors propagate."""
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    if isinstance(exc, httpx.HTTPError | ParseError | DefusedXmlException | ValueError):
        return type(exc).__name__
    raise exc


def evidence_digest(plan: QueryPlan, evidence: Evidence) -> str:
    """Deterministic, citation-only answer used when no LLM is configured or it fails."""
    lines = [
        "**Answer (evidence digest, no LLM synthesis):**",
        f"Retrieved evidence for *{plan.question}* covering {plan.period.label}.",
        "Items below are verified source listings; no analysis or inference has been added.",
        "",
    ]
    names = {i.source for i in evidence.sources} | {i.source for i in evidence.indicators}
    if evidence.indicators:
        lines += ["**Key data:**", format_indicators(evidence.indicators), ""]
    if evidence.sources:
        lines.append("**Recent sources:**")
        for n, item in enumerate(evidence.sources, start=1):
            date = item.published.date().isoformat() if item.published else "undated"
            summary = f" {item.summary[:240]}" if item.summary else ""
            lines.append(f"{n}. [{item.title}]({item.url}) ({item.source}, {date}).{summary}")
        lines.append("")
    if not evidence.sources and not evidence.indicators:
        lines += ["No matching items were found in the monitored sources for this period.", ""]
    lines += [
        "**Why it matters:** analysis requires LLM synthesis; configure `LLM_API_KEY` to get "
        'the full "so what?" interpretation.',
        "",
        "**Sources:** " + (", ".join(sorted(names)) or "none"),
    ]
    return "\n".join(lines)
