import os
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from intel_agent.config import Settings
from intel_agent.main import app, get_settings
from tests.conftest import Recorder, default_handler


def ask(client: TestClient, question: str, **extra: object) -> dict:
    response = client.post("/ask", json={"question": question, **extra})
    assert response.status_code == 200, response.text
    return response.json()


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {
        "status": "ok",
        "llm_configured": False,
        "fred_configured": False,
    }


def test_index_page(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Market Intelligence Agent" in response.text


def test_innovations_without_llm_returns_evidence_digest(client: TestClient) -> None:
    data = ask(client, "What were the biggest AI innovations this week?")
    assert data["plan"]["intent"] == "innovations"
    assert data["llm_used"] is False
    urls = [s["url"] for s in data["sources"]]
    assert "https://huggingface.co/papers/2609.11111" in urls
    assert "https://openai.com/a1" in urls
    assert not any(u.endswith("/old") for u in urls)
    assert "evidence digest" in data["answer"]
    assert any("LLM_API_KEY" in w for w in data["warnings"])


def test_research_papers_sorted_and_filtered(client: TestClient) -> None:
    data = ask(client, "Most important new AI research papers this week on agents?")
    papers = [s for s in data["sources"] if s["kind"] == "paper"]
    assert papers[0]["title"] == "Popular agent paper"
    titles = [p["title"] for p in papers]
    assert "Less popular vision paper" not in titles
    assert "Agents that plan with retrieval" in titles
    assert "An old paper" not in titles


def test_clarification_short_circuits_without_fetching(
    client: TestClient, recorder: Recorder
) -> None:
    data = ask(client, "What is the market gap and potential AI opportunities in {{country}}?")
    assert data["plan"]["needs_clarification"] is True
    assert "Which country" in data["answer"]
    assert recorder.requests == []


def test_country_vs_us_uses_world_bank_for_both(client: TestClient, recorder: Recorder) -> None:
    data = ask(
        client,
        "What is the market gap and potential AI opportunities in {{country}} compared to the US?",
        country="Malaysia",
    )
    assert data["plan"]["intent"] == "country_vs_us"
    assert {i["country_code"] for i in data["indicators"]} == {"MY", "US"}
    wb_paths = [r.url.path for r in recorder.requests if r.url.host == "api.worldbank.org"]
    assert wb_paths and all("/country/MY;US/" in p for p in wb_paths)
    assert all(s["title"].count("Malaysia") for s in data["sources"])


def test_llm_synthesis_receives_evidence_and_structure(
    client: TestClient, recorder: Recorder, settings: Settings
) -> None:
    llm_settings = replace(
        settings, llm_api_key="test-key", llm_base_url="https://api.openai.test/v1"
    )
    app.dependency_overrides[get_settings] = lambda: llm_settings
    data = ask(client, "Give me a report on AI opportunities in Malaysia", audience="entrepreneur")
    assert data["llm_used"] is True
    assert data["answer"] == "**Answer:** synthesized [1]"
    [payload] = recorder.llm_payloads()
    system, user = payload["messages"]
    assert "Never invent statistics" in system["content"]
    assert "## Executive Summary" in user["content"]
    assert "Audience: entrepreneur" in user["content"]
    assert "Malaysia" in user["content"] and "[1]" in user["content"]
    auth = [r for r in recorder.requests if r.url.host == "api.openai.test"][0]
    assert auth.headers["Authorization"] == "Bearer test-key"


def test_source_failures_become_warnings(client: TestClient, recorder: Recorder) -> None:
    def flaky(request: httpx.Request) -> httpx.Response:
        if request.url.host == "huggingface.co":
            return httpx.Response(503)
        if request.url.host == "openai.com":
            return httpx.Response(200, text="<not xml")
        return default_handler(request)

    recorder.handler = flaky
    data = ask(client, "What were the biggest AI innovations this week?")
    assert "Hugging Face Papers unavailable (HTTP 503)." in data["warnings"]
    assert "OpenAI News unavailable (ParseError)." in data["warnings"]
    assert data["sources"]


def test_llm_failure_falls_back_to_digest(
    client: TestClient, recorder: Recorder, settings: Settings
) -> None:
    llm_settings = replace(settings, llm_api_key="k", llm_base_url="https://api.openai.test/v1")
    app.dependency_overrides[get_settings] = lambda: llm_settings

    def broken_llm(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.openai.test":
            return httpx.Response(500)
        return default_handler(request)

    recorder.handler = broken_llm
    data = ask(client, "What were the biggest AI innovations this week?")
    assert data["llm_used"] is False
    assert "evidence digest" in data["answer"]
    assert any("HTTP 500" in w for w in data["warnings"])


def test_news_search_opt_in(client: TestClient, recorder: Recorder, settings: Settings) -> None:
    app.dependency_overrides[get_settings] = lambda: replace(settings, enable_news_search=True)
    data = ask(client, "What are the AI job opportunities in Malaysia?")
    item = next(s for s in data["sources"] if s["url"] == "https://example.com/my")
    assert item["title"] == "Malaysia AI hub opens"
    assert item["source"] == "The Star (via Google News)"


def test_papers_and_indicators_endpoints(client: TestClient) -> None:
    papers = client.get("/papers", params={"topic": ["agents"], "days": 7}).json()
    assert [p["title"] for p in papers] == ["Agents that plan with retrieval"]
    assert client.get("/papers", params={"topic": ["nope"]}).status_code == 422
    hf = client.get("/papers", params={"source": "huggingface"}).json()
    assert hf[0]["score"] == 42
    indicators = client.get("/indicators/malaysia", params={"compare_us": True}).json()
    assert {i["country_code"] for i in indicators} == {"MY", "US"}
    assert client.get("/indicators/atlantis").status_code == 404


def test_news_endpoint(client: TestClient) -> None:
    items = client.get("/news", params={"group": "labs", "q": "launches"}).json()
    assert {i["source"] for i in items} == {
        "OpenAI News",
        "Google DeepMind Blog",
        "Microsoft Research",
    }
    assert client.get("/news", params={"group": "bogus"}).status_code == 422


def test_sources_are_interleaved_across_feeds(client: TestClient) -> None:
    data = ask(client, "What were the biggest AI innovations this week?")
    sources = {s["source"] for s in data["sources"]}
    assert {"OpenAI News", "TechCrunch", "Hugging Face Papers"} <= sources


def test_settings_read_dotenv_and_shell_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".env").write_text("LLM_API_KEY=from-dotenv\nLLM_MODEL=from-dotenv\n")
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    with patch.dict(os.environ, {"LLM_MODEL": "from-shell"}):
        os.environ.pop("LLM_API_KEY", None)
        os.environ.pop("OPENAI_API_KEY", None)
        try:
            settings = get_settings()
        finally:
            get_settings.cache_clear()
    assert settings.llm_api_key == "from-dotenv"
    assert settings.llm_model == "from-shell"
