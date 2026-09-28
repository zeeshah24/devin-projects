import asyncio

import httpx

from intel_agent.models import Indicator

FRED_API = "https://api.stlouisfed.org/fred/series/observations"

FRED_SERIES: dict[str, str] = {
    "FEDFUNDS": "Federal funds effective rate (%)",
    "UNRATE": "Unemployment rate (%)",
    "CPIAUCSL": "CPI, all urban consumers (index 1982-1984=100)",
    "A191RL1Q225SBEA": "Real GDP growth (% change, annualized)",
}


async def _latest(client: httpx.AsyncClient, api_key: str, series_id: str) -> Indicator | None:
    response = await client.get(
        FRED_API,
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": "1",
        },
    )
    response.raise_for_status()
    observations = response.json().get("observations") or []
    if not observations or observations[0].get("value") in (None, "."):
        return None
    latest = observations[0]
    return Indicator(
        country_code="US",
        country_name="United States",
        indicator_id=series_id,
        name=FRED_SERIES[series_id],
        value=float(latest["value"]),
        period=str(latest.get("date", "")),
        source="FRED, Federal Reserve Bank of St. Louis",
        url=f"https://fred.stlouisfed.org/series/{series_id}",
    )


async def fetch_us_macro(client: httpx.AsyncClient, api_key: str) -> list[Indicator]:
    results = await asyncio.gather(*(_latest(client, api_key, s) for s in FRED_SERIES))
    return [r for r in results if r is not None]
