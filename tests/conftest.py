import json
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from intel_agent.config import Settings
from intel_agent.main import app, get_client, get_settings

NOW = datetime.now(timezone.utc)


def rfc822(dt: datetime) -> str:
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def rss(items: list[tuple[str, str, datetime, str]]) -> str:
    body = "".join(
        f"<item><title>{t}</title><link>{link}</link><pubDate>{rfc822(d)}</pubDate>"
        f"<description><![CDATA[<p>{desc}</p>]]></description></item>"
        for t, link, d, desc in items
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel>{body}</channel></rss>'


def arxiv_atom(entries: list[tuple[str, str, datetime]]) -> str:
    body = "".join(
        f"<entry><id>http://arxiv.org/abs/{pid}</id><title>{title}</title>"
        f"<published>{iso(d)}</published><summary>Abstract of {title}.</summary>"
        f'<link href="https://arxiv.org/abs/{pid}" rel="alternate" type="text/html"/>'
        f'<link href="https://arxiv.org/pdf/{pid}" rel="related" title="pdf"/>'
        f"<author><name>Ada Lovelace</name></author></entry>"
        for pid, title, d in entries
    )
    return f'<feed xmlns="http://www.w3.org/2005/Atom">{body}</feed>'


def default_handler(request: httpx.Request) -> httpx.Response:
    host, path = request.url.host, request.url.path
    recent, old = NOW - timedelta(days=1), NOW - timedelta(days=400)
    if host == "export.arxiv.org":
        return httpx.Response(
            200,
            text=arxiv_atom(
                [
                    ("2609.00001v1", "Agents that plan with retrieval", recent),
                    ("2001.00001v1", "An old paper", old),
                ]
            ),
        )
    if host == "huggingface.co":
        papers = [
            {
                "paper": {
                    "id": "2609.11111",
                    "title": "Popular agent paper",
                    "summary": "An agent benchmark.",
                    "publishedAt": iso(recent),
                    "upvotes": 42,
                    "authors": [{"name": "Grace Hopper"}],
                }
            },
            {
                "paper": {
                    "id": "2609.22222",
                    "title": "Less popular vision paper",
                    "summary": "A multimodal model.",
                    "publishedAt": iso(recent),
                    "upvotes": 3,
                }
            },
        ]
        return httpx.Response(200, json=papers)
    if host == "api.worldbank.org":
        indicator_id = path.rsplit("/", 1)[-1]
        codes = path.split("/country/")[1].split("/")[0].split(";")
        rows = [
            {
                "indicator": {"id": indicator_id, "value": f"Indicator {indicator_id}"},
                "country": {
                    "id": code,
                    "value": {"MY": "Malaysia", "US": "United States"}.get(code, code),
                },
                "date": "2025",
                "value": 5.5,
            }
            for code in codes
        ]
        return httpx.Response(200, json=[{"page": 1}, rows])
    if host == "api.openai.test":
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "**Answer:** synthesized [1]"}}]}
        )
    if host == "news.google.com":
        return httpx.Response(
            200,
            text=rss([("Malaysia AI hub opens - The Star", "https://example.com/my", recent, "x")]),
        )
    return httpx.Response(
        200,
        text=rss(
            [
                (
                    f"{host} launches new AI model in Malaysia",
                    f"https://{host}/a1",
                    recent,
                    "A new agent model &amp; benchmark",
                ),
                (f"{host} old story", f"https://{host}/old", old, "old"),
            ]
        ),
    )


class Recorder:
    def __init__(self) -> None:
        self.handler: Callable[[httpx.Request], httpx.Response] = default_handler
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.handler(request)

    def llm_payloads(self) -> list[dict[str, object]]:
        return [json.loads(r.content) for r in self.requests if r.url.host == "api.openai.test"]


@pytest.fixture
def recorder() -> Recorder:
    return Recorder()


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def client(recorder: Recorder, settings: Settings) -> Iterator[TestClient]:
    http = httpx.AsyncClient(transport=httpx.MockTransport(recorder))
    app.dependency_overrides[get_client] = lambda: http
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
