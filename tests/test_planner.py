from datetime import date

import pytest

from intel_agent.countries import find_countries
from intel_agent.models import AskRequest, Audience, Intent, Mode
from intel_agent.planner import plan_query

TODAY = date(2026, 9, 26)


def plan(question: str, **kwargs: object):
    return plan_query(AskRequest(question=question, **kwargs), TODAY)


@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("What were the biggest AI innovations this week?", Intent.INNOVATIONS),
        ("What are the most important new AI research papers this week?", Intent.RESEARCH_PAPERS),
        (
            "What is the market gap and potential AI opportunities in Malaysia?",
            Intent.COUNTRY_OPPORTUNITIES,
        ),
        (
            "What is the market gap and potential AI opportunities in Malaysia compared to the US?",
            Intent.COUNTRY_VS_US,
        ),
        ("What are the AI job opportunities in Malaysia?", Intent.JOBS),
        ("How is inflation affecting tech valuations?", Intent.ECONOMY),
        ("Explain what retrieval-augmented generation is", Intent.GENERAL),
    ],
)
def test_intents(question: str, intent: Intent) -> None:
    assert plan(question).intent is intent


def test_country_vs_us_sets_both_countries() -> None:
    p = plan("What is the market gap and AI opportunities in Malaysia compared to the US?")
    assert p.country is not None and p.country.code == "MY"
    assert p.compare_country is not None and p.compare_country.code == "US"
    assert not p.needs_clarification


@pytest.mark.parametrize(
    "question",
    ["Give me a report on AI in Japan", "Deep dive into agentic AI", "Research this: RAG vendors"],
)
def test_report_mode(question: str) -> None:
    assert plan(question).mode is Mode.REPORT


def test_brief_mode_by_default_and_explicit_override() -> None:
    assert plan("What were the biggest AI innovations this week?").mode is Mode.BRIEF
    assert plan("What is RAG?", mode=Mode.REPORT).mode is Mode.REPORT


def test_placeholder_is_replaced_with_requested_country() -> None:
    p = plan(
        "What is the market gap and potential AI opportunities in {{country}}?", country="India"
    )
    assert p.question.endswith("in India?")
    assert p.country is not None and p.country.code == "IN"
    assert not p.needs_clarification


def test_unfilled_placeholder_asks_for_country() -> None:
    p = plan("What are the AI opportunities in {{country}}?")
    assert p.needs_clarification
    assert p.clarification is not None and "Which country" in p.clarification


def test_country_analysis_without_country_asks_for_country() -> None:
    p = plan("What is the market gap and potential AI opportunities compared to the US?")
    assert p.intent is Intent.COUNTRY_OPPORTUNITIES
    assert p.country is not None and p.country.code == "US"
    p = plan("Which startup ecosystem gaps exist?")
    assert p.needs_clarification


def test_pronoun_us_is_not_the_united_states() -> None:
    assert find_countries("Can you tell us about AI in Singapore?")[0].code == "SG"
    assert [c.code for c in find_countries("tell us more")] == []
    assert [c.code for c in find_countries("AI in the US and the UK")] == ["US", "GB"]


@pytest.mark.parametrize(
    ("question", "start", "label"),
    [
        ("AI news today", date(2026, 9, 26), "today"),
        ("AI news this week", date(2026, 9, 20), "this week"),
        ("AI news this month", date(2026, 8, 28), "this month"),
        ("AI news in the last 3 days", date(2026, 9, 24), "last 3 days"),
        ("latest AI news", date(2026, 9, 13), "recent"),
    ],
)
def test_time_windows(question: str, start: date, label: str) -> None:
    period = plan(question).period
    assert period.start == start
    assert period.end == TODAY
    assert period.label.startswith(label)


def test_audience_detection_and_topics() -> None:
    p = plan("As a student, which multimodal and robotics papers should I read?")
    assert p.audience is Audience.STUDENT
    assert p.topics == ["multimodal", "robotics"]
    assert plan("I'm a founder: where are the AI gaps in Kenya?").audience is Audience.ENTREPRENEUR
    assert plan("What is RAG?").audience is Audience.GENERAL
