from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class Intent(str, Enum):
    INNOVATIONS = "innovations"
    RESEARCH_PAPERS = "research_papers"
    COUNTRY_OPPORTUNITIES = "country_opportunities"
    COUNTRY_VS_US = "country_vs_us"
    JOBS = "jobs"
    ECONOMY = "economy"
    GENERAL = "general"


class Mode(str, Enum):
    BRIEF = "brief"
    REPORT = "report"


class Audience(str, Enum):
    RESEARCHER = "researcher"
    ENTREPRENEUR = "entrepreneur"
    TECH_PROFESSIONAL = "technology_professional"
    STUDENT = "student"
    BUSINESS_LEADER = "business_leader"
    INVESTOR = "investor"
    GENERAL = "general"


class SourceKind(str, Enum):
    PAPER = "paper"
    NEWS = "news"
    LAB = "lab"
    GOVERNMENT = "government"


class Country(BaseModel):
    code: str
    name: str


class Period(BaseModel):
    start: date
    end: date
    label: str


class QueryPlan(BaseModel):
    question: str
    intent: Intent
    mode: Mode
    audience: Audience
    country: Country | None = None
    compare_country: Country | None = None
    period: Period
    topics: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification: str | None = None


class SourceItem(BaseModel):
    title: str
    url: str
    source: str
    kind: SourceKind
    published: datetime | None = None
    summary: str = ""
    authors: list[str] = Field(default_factory=list)
    score: float | None = None


class Indicator(BaseModel):
    country_code: str
    country_name: str
    indicator_id: str
    name: str
    value: float
    period: str
    source: str
    url: str


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    country: str | None = Field(
        default=None, description="Fills a {{country}} placeholder or sets the target country."
    )
    audience: Audience | None = None
    mode: Mode | None = None


class AskResponse(BaseModel):
    plan: QueryPlan
    answer: str
    sources: list[SourceItem]
    indicators: list[Indicator]
    llm_used: bool
    warnings: list[str]
    generated_at: datetime
