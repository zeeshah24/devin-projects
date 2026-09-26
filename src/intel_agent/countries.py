import re

from intel_agent.models import Country

# ISO 3166-1 alpha-2 code -> (display name, case-insensitive aliases)
COUNTRIES: dict[str, tuple[str, tuple[str, ...]]] = {
    "US": ("United States", ("united states", "u.s.", "u.s.a.", "usa", "america")),
    "MY": ("Malaysia", ("malaysia",)),
    "IN": ("India", ("india",)),
    "SG": ("Singapore", ("singapore",)),
    "GB": ("United Kingdom", ("united kingdom", "uk", "u.k.", "britain", "great britain")),
    "JP": ("Japan", ("japan",)),
    "DE": ("Germany", ("germany",)),
    "CA": ("Canada", ("canada",)),
    "AE": ("United Arab Emirates", ("united arab emirates", "uae", "dubai", "abu dhabi")),
    "CN": ("China", ("china", "prc")),
    "ID": ("Indonesia", ("indonesia",)),
    "TH": ("Thailand", ("thailand",)),
    "VN": ("Vietnam", ("vietnam", "viet nam")),
    "PH": ("Philippines", ("philippines",)),
    "AU": ("Australia", ("australia",)),
    "NZ": ("New Zealand", ("new zealand",)),
    "KR": ("South Korea", ("south korea", "korea", "republic of korea")),
    "FR": ("France", ("france",)),
    "IT": ("Italy", ("italy",)),
    "ES": ("Spain", ("spain",)),
    "NL": ("Netherlands", ("netherlands", "holland")),
    "SE": ("Sweden", ("sweden",)),
    "NO": ("Norway", ("norway",)),
    "DK": ("Denmark", ("denmark",)),
    "FI": ("Finland", ("finland",)),
    "CH": ("Switzerland", ("switzerland",)),
    "IE": ("Ireland", ("ireland",)),
    "PL": ("Poland", ("poland",)),
    "IL": ("Israel", ("israel",)),
    "SA": ("Saudi Arabia", ("saudi arabia", "ksa")),
    "QA": ("Qatar", ("qatar",)),
    "TR": ("Turkey", ("turkey", "turkiye", "türkiye")),
    "EG": ("Egypt", ("egypt",)),
    "NG": ("Nigeria", ("nigeria",)),
    "KE": ("Kenya", ("kenya",)),
    "ZA": ("South Africa", ("south africa",)),
    "BR": ("Brazil", ("brazil",)),
    "MX": ("Mexico", ("mexico",)),
    "AR": ("Argentina", ("argentina",)),
    "CL": ("Chile", ("chile",)),
    "CO": ("Colombia", ("colombia",)),
    "PK": ("Pakistan", ("pakistan",)),
    "BD": ("Bangladesh", ("bangladesh",)),
    "HK": ("Hong Kong", ("hong kong",)),
    "TW": ("Taiwan", ("taiwan",)),
}

_ALIAS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (code, re.compile(r"(?<![\w.])" + re.escape(alias) + r"(?![\w])", re.IGNORECASE))
    for code, (_, aliases) in COUNTRIES.items()
    for alias in aliases
]
# Upper-case "US" only, so the pronoun "us" is not mistaken for the country.
_US_ABBREV = re.compile(r"\bUS\b")


def country(code: str) -> Country:
    return Country(code=code, name=COUNTRIES[code][0])


def lookup_country(value: str) -> Country | None:
    value = value.strip()
    if value.upper() in COUNTRIES:
        return country(value.upper())
    found = find_countries(value)
    return found[0] if found else None


def find_countries(text: str) -> list[Country]:
    """Countries mentioned in ``text``, in order of first appearance."""
    positions: dict[str, int] = {}
    for code, pattern in _ALIAS_PATTERNS:
        match = pattern.search(text)
        if match and match.start() < positions.get(code, len(text) + 1):
            positions[code] = match.start()
    us_match = _US_ABBREV.search(text)
    if us_match and us_match.start() < positions.get("US", len(text) + 1):
        positions["US"] = us_match.start()
    return [country(code) for code, _ in sorted(positions.items(), key=lambda kv: kv[1])]


def country_terms(code: str) -> list[str]:
    name, aliases = COUNTRIES[code]
    return sorted({name.lower(), *(a for a in aliases if len(a) > 3)})
