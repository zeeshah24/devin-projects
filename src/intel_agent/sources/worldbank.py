import asyncio

import httpx

from intel_agent.models import Indicator

WORLD_BANK_API = "https://api.worldbank.org/v2"

ECONOMY_INDICATORS: dict[str, str] = {
    "NY.GDP.MKTP.CD": "GDP (current US$)",
    "NY.GDP.MKTP.KD.ZG": "GDP growth (annual %)",
    "NY.GDP.PCAP.CD": "GDP per capita (current US$)",
    "FP.CPI.TOTL.ZG": "Inflation, consumer prices (annual %)",
    "SP.POP.TOTL": "Population, total",
}
TECHNOLOGY_INDICATORS: dict[str, str] = {
    "IT.NET.USER.ZS": "Individuals using the Internet (% of population)",
    "GB.XPD.RSDV.GD.ZS": "Research and development expenditure (% of GDP)",
    "TX.VAL.TECH.MF.ZS": "High-technology exports (% of manufactured exports)",
    "IT.NET.SECR.P6": "Secure Internet servers (per 1 million people)",
}
LABOR_INDICATORS: dict[str, str] = {
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of labor force)",
    "SL.UEM.1524.ZS": "Unemployment, youth (% of labor force ages 15-24)",
    "SL.TLF.TOTL.IN": "Labor force, total",
    "SL.SRV.EMPL.ZS": "Employment in services (% of total employment)",
}


async def _fetch_indicator(
    client: httpx.AsyncClient, country_codes: list[str], indicator_id: str
) -> list[Indicator]:
    response = await client.get(
        f"{WORLD_BANK_API}/country/{';'.join(country_codes)}/indicator/{indicator_id}",
        params={"format": "json", "mrnev": "1", "per_page": "50"},
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
        return []
    results: list[Indicator] = []
    for row in payload[1]:
        if not isinstance(row, dict) or row.get("value") is None:
            continue
        country_info = row.get("country") or {}
        indicator_info = row.get("indicator") or {}
        code = str(country_info.get("id", ""))
        results.append(
            Indicator(
                country_code=code,
                country_name=str(country_info.get("value", code)),
                indicator_id=indicator_id,
                name=str(indicator_info.get("value", indicator_id)),
                value=float(row["value"]),
                period=str(row.get("date", "")),
                source="World Bank World Development Indicators",
                url=f"https://data.worldbank.org/indicator/{indicator_id}?locations={code}",
            )
        )
    return results


async def fetch_indicators(
    client: httpx.AsyncClient, country_codes: list[str], indicator_ids: list[str]
) -> list[Indicator]:
    batches = await asyncio.gather(
        *(_fetch_indicator(client, country_codes, i) for i in indicator_ids)
    )
    return [indicator for batch in batches for indicator in batch]
