from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from functools import lru_cache
from importlib.resources import files
from typing import Annotated

import httpx
from dotenv import find_dotenv, load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from intel_agent.agent import IntelligenceAgent, utcnow
from intel_agent.config import Settings
from intel_agent.countries import lookup_country
from intel_agent.models import AskRequest, AskResponse, Indicator, QueryPlan, SourceItem
from intel_agent.planner import TOPIC_KEYWORDS, TOPICS
from intel_agent.sources import arxiv, fred, hf_papers, worldbank
from intel_agent.sources.feeds import FEEDS, fetch_feed, within

NEWS_GROUPS = sorted({spec.group for spec in FEEDS})


@lru_cache
def get_settings() -> Settings:
    load_dotenv(find_dotenv(usecwd=True))
    return Settings.from_env()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    async with httpx.AsyncClient(
        timeout=settings.http_timeout,
        follow_redirects=True,
        headers={"User-Agent": settings.user_agent},
    ) as client:
        app.state.http = client
        yield


def get_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


ClientDep = Annotated[httpx.AsyncClient, Depends(get_client)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_agent(client: ClientDep, settings: SettingsDep) -> IntelligenceAgent:
    return IntelligenceAgent(client, settings)


AgentDep = Annotated[IntelligenceAgent, Depends(get_agent)]

app = FastAPI(
    title="AI Research, Innovation & Market Intelligence Agent",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index() -> str:
    return files("intel_agent").joinpath("static/index.html").read_text(encoding="utf-8")


@app.get("/health")
def health(settings: SettingsDep) -> dict[str, object]:
    return {
        "status": "ok",
        "llm_configured": settings.llm_api_key is not None,
        "fred_configured": settings.fred_api_key is not None,
    }


@app.post("/ask")
async def ask(request: AskRequest, agent: AgentDep) -> AskResponse:
    return await agent.ask(request)


@app.post("/plan")
def plan(request: AskRequest, agent: AgentDep) -> QueryPlan:
    return agent.plan(request)


def _since(days: int) -> datetime:
    return utcnow() - timedelta(days=days)


@app.get("/papers")
async def papers(
    client: ClientDep,
    topic: Annotated[list[str], Query(description=f"Any of: {', '.join(TOPICS)}")] = [],  # noqa: B006
    days: Annotated[int, Query(ge=1, le=90)] = 7,
    limit: Annotated[int, Query(ge=1, le=50)] = 15,
    source: Annotated[str, Query(pattern="^(arxiv|huggingface)$")] = "arxiv",
) -> list[SourceItem]:
    unknown = [t for t in topic if t not in TOPICS]
    if unknown:
        raise HTTPException(422, f"Unknown topic(s): {', '.join(unknown)}")
    since = _since(days)
    if source == "huggingface":
        keywords = [k for t in topic for k in TOPIC_KEYWORDS[t]]
        return await hf_papers.trending_papers(client, since, keywords, limit)
    return await arxiv.search_arxiv(client, [TOPICS[t][1] for t in topic], since, limit)


@app.get("/news")
async def news(
    client: ClientDep,
    group: Annotated[str, Query(description=f"One of: {', '.join(NEWS_GROUPS)}")] = "tech_news",
    days: Annotated[int, Query(ge=1, le=90)] = 7,
    q: str | None = None,
) -> list[SourceItem]:
    specs = [spec for spec in FEEDS if spec.group == group]
    if not specs:
        raise HTTPException(422, f"Unknown group; expected one of {NEWS_GROUPS}")
    since = _since(days)
    items: list[SourceItem] = []
    for spec in specs:
        try:
            items.extend(i for i in await fetch_feed(client, spec) if within(i, since))
        except httpx.HTTPError:
            continue
    if q:
        items = [i for i in items if q.lower() in f"{i.title} {i.summary}".lower()]
    return sorted(items, key=lambda i: i.published or since, reverse=True)


@app.get("/indicators/{country}")
async def indicators(
    country: str,
    client: ClientDep,
    settings: SettingsDep,
    compare_us: bool = False,
) -> list[Indicator]:
    target = lookup_country(country)
    if target is None:
        raise HTTPException(404, f"Unknown country: {country}")
    codes = [target.code]
    if compare_us and target.code != "US":
        codes.append("US")
    ids = [
        *worldbank.ECONOMY_INDICATORS,
        *worldbank.TECHNOLOGY_INDICATORS,
        *worldbank.LABOR_INDICATORS,
    ]
    results = await worldbank.fetch_indicators(client, codes, ids)
    if "US" in codes and settings.fred_api_key:
        results.extend(await fred.fetch_us_macro(client, settings.fred_api_key))
    return results
