from datetime import datetime, timezone

import pytest
from defusedxml import DefusedXmlException

from intel_agent.models import SourceKind
from intel_agent.sources.feeds import clean_text, parse_date, parse_feed

RSS2 = """<?xml version="1.0"?><rss version="2.0"><channel><item>
<title>Model &amp; benchmark</title><link>https://example.com/a</link>
<pubDate>Thu, 24 Sep 2026 10:00:00 +0000</pubDate>
<description><![CDATA[<p>Hello <b>world</b></p>]]></description>
<dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">Jane Doe</dc:creator>
</item></channel></rss>"""

ATOM = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom post</title>
<link rel="related" href="https://example.com/pdf"/><link rel="alternate" href="https://example.com/b"/>
<updated>2026-09-23T08:30:00Z</updated><summary>Summary</summary>
<author><name>Sam</name></author></entry></feed>"""

RDF = """<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
 xmlns="http://purl.org/rss/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/">
<item rdf:about="https://www.nature.com/articles/x1"><title>Nature paper</title>
<dc:date>2026-09-22</dc:date></item></rdf:RDF>"""


def test_parse_rss2() -> None:
    [item] = parse_feed(RSS2, "Example", SourceKind.NEWS)
    assert item.title == "Model & benchmark"
    assert item.url == "https://example.com/a"
    assert item.summary == "Hello world"
    assert item.authors == ["Jane Doe"]
    assert item.published == datetime(2026, 9, 24, 10, tzinfo=timezone.utc)


def test_parse_atom_prefers_alternate_link() -> None:
    [item] = parse_feed(ATOM, "Example", SourceKind.LAB)
    assert item.url == "https://example.com/b"
    assert item.authors == ["Sam"]
    assert item.published == datetime(2026, 9, 23, 8, 30, tzinfo=timezone.utc)


def test_parse_rdf_uses_about_and_dc_date() -> None:
    [item] = parse_feed(RDF, "Nature", SourceKind.PAPER)
    assert item.url == "https://www.nature.com/articles/x1"
    assert item.published == datetime(2026, 9, 22, tzinfo=timezone.utc)


def test_rejects_entity_expansion() -> None:
    evil = (
        '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa">]>'
        "<rss><item><title>&a;</title></item></rss>"
    )
    with pytest.raises(DefusedXmlException):
        parse_feed(evil, "Evil", SourceKind.NEWS)


def test_parse_date_and_clean_text() -> None:
    assert parse_date("not a date") is None
    assert parse_date("2026-09-01T00:00:00.000Z") == datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert clean_text("x" * 50, limit=10) == "x" * 9 + "…"
