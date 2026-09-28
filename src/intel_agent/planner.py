import re
from datetime import date, timedelta

from intel_agent.countries import find_countries, lookup_country
from intel_agent.models import (
    AskRequest,
    Audience,
    Country,
    Intent,
    Mode,
    Period,
    QueryPlan,
)

COUNTRY_PLACEHOLDER = "{{country}}"

_REPORT = re.compile(
    r"\b(give me a report|(write|prepare|create|produce) (me )?an? (\w+ )?report|"
    r"(full|detailed|comprehensive|in-depth|research) report|report on|deep[- ]dive|"
    r"research this|analy[sz]e (this )?in detail|detailed analysis|in[- ]depth analysis)\b",
    re.IGNORECASE,
)
_COMPARE = re.compile(r"\b(compared? (to|with)|versus|vs\.?|against|relative to)\b", re.IGNORECASE)
_JOBS = re.compile(
    r"\b(jobs?|careers?|hiring|salar(y|ies)|roles?|employment|talent market)\b", re.I
)
_PAPERS = re.compile(r"\b(papers?|arxiv|preprints?|publications?|research findings)\b", re.I)
_OPPORTUNITY = re.compile(
    r"\b(market gaps?|opportunit(y|ies)|unmet needs?|ecosystem|adoption|business ideas?|"
    r"startup landscape)\b",
    re.I,
)
_INNOVATION = re.compile(
    r"\b(innovations?|breakthroughs?|launch(es|ed)?|announce(d|ments?)?|releases?|news|"
    r"developments?|what happened)\b",
    re.I,
)
_ECONOMY = re.compile(
    r"\b(econom(y|ic|ics)|inflation|interest rates?|gdp|recession|federal reserve|fed|"
    r"markets?|stocks?|labor market|unemployment|cpi)\b",
    re.I,
)

_AUDIENCE_TERMS: list[tuple[Audience, re.Pattern[str]]] = [
    (Audience.RESEARCHER, re.compile(r"\b(researcher|phd|academic|scientist)\b", re.I)),
    (Audience.ENTREPRENEUR, re.compile(r"\b(entrepreneur|founder|startup founder)\b", re.I)),
    (Audience.INVESTOR, re.compile(r"\b(investor|vc|venture capitalist)\b", re.I)),
    (Audience.STUDENT, re.compile(r"\b(student|beginner|learner)\b", re.I)),
    (
        Audience.BUSINESS_LEADER,
        re.compile(r"\b(ceo|executive|business leader|manager|board|director)\b", re.I),
    ),
    (
        Audience.TECH_PROFESSIONAL,
        re.compile(r"\b(engineer|developer|cto|architect|ml engineer|data scientist)\b", re.I),
    ),
]
_SELF_DESCRIPTION = re.compile(r"\b(as an?|i am an?|i'm an?|for an?|for)\s+([\w\s-]{2,40})", re.I)

TOPICS: dict[str, tuple[re.Pattern[str], str]] = {
    "llm": (re.compile(r"\b(llms?|language models?)\b", re.I), 'all:"language model"'),
    "reasoning": (re.compile(r"\breasoning\b", re.I), "all:reasoning"),
    "agents": (re.compile(r"\b(agents?|agentic)\b", re.I), "all:agent"),
    "rag": (re.compile(r"\b(rag|retrieval)\b", re.I), 'all:"retrieval augmented"'),
    "multimodal": (
        re.compile(r"\b(multimodal|vision[- ]language|vlms?)\b", re.I),
        "all:multimodal",
    ),
    "coding": (
        re.compile(r"\b(coding|code generation|software engineering)\b", re.I),
        'all:"code generation"',
    ),
    "evaluation": (re.compile(r"\b(evaluation|evals?|benchmarks?)\b", re.I), "all:benchmark"),
    "safety": (re.compile(r"\b(safety|alignment)\b", re.I), "(all:alignment OR all:safety)"),
    "infrastructure": (
        re.compile(r"\b(infrastructure|distributed training|gpus?|accelerators?)\b", re.I),
        'all:"distributed training"',
    ),
    "inference": (
        re.compile(r"\b(inference|quantization|serving|latency)\b", re.I),
        "all:inference",
    ),
    "robotics": (re.compile(r"\brobot(s|ics)?\b", re.I), "cat:cs.RO"),
    "science": (
        re.compile(r"\b(ai for science|scientific|biology|chemistry|materials|protein)\b", re.I),
        "all:scientific",
    ),
}

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "llm": ("language model", "llm"),
    "reasoning": ("reasoning",),
    "agents": ("agent",),
    "rag": ("retrieval", "rag"),
    "multimodal": ("multimodal", "vision-language", "vision language"),
    "coding": ("code", "coding", "software"),
    "evaluation": ("benchmark", "evaluation"),
    "safety": ("safety", "alignment"),
    "infrastructure": ("training", "gpu", "distributed"),
    "inference": ("inference", "quantization", "serving", "decoding"),
    "robotics": ("robot",),
    "science": ("scientific", "biology", "chemistry", "materials", "protein"),
}

_COUNTRY_INTENTS = {Intent.COUNTRY_OPPORTUNITIES, Intent.COUNTRY_VS_US}
_DEFAULT_WINDOW_DAYS = {
    Intent.INNOVATIONS: 7,
    Intent.RESEARCH_PAPERS: 7,
    Intent.ECONOMY: 30,
    Intent.GENERAL: 14,
    Intent.JOBS: 90,
    Intent.COUNTRY_OPPORTUNITIES: 90,
    Intent.COUNTRY_VS_US: 90,
}
_RELATIVE = re.compile(r"\b(?:last|past)\s+(\d{1,3})\s+(day|week|month)s?\b", re.I)
_UNIT_DAYS = {"day": 1, "week": 7, "month": 30}


def detect_mode(question: str) -> Mode:
    return Mode.REPORT if _REPORT.search(question) else Mode.BRIEF


def detect_audience(question: str) -> Audience:
    for match in _SELF_DESCRIPTION.finditer(question):
        phrase = match.group(2)
        for audience, pattern in _AUDIENCE_TERMS:
            if pattern.search(phrase):
                return audience
    return Audience.GENERAL


def detect_topics(question: str) -> list[str]:
    return [name for name, (pattern, _) in TOPICS.items() if pattern.search(question)]


def detect_intent(question: str, has_country: bool, has_comparison: bool) -> Intent:
    if _JOBS.search(question):
        return Intent.JOBS
    if _PAPERS.search(question):
        return Intent.RESEARCH_PAPERS
    if _OPPORTUNITY.search(question) and (has_country or "{{" in question):
        return Intent.COUNTRY_VS_US if has_comparison else Intent.COUNTRY_OPPORTUNITIES
    if _INNOVATION.search(question):
        return Intent.INNOVATIONS
    if _ECONOMY.search(question):
        return Intent.ECONOMY
    if has_country and has_comparison:
        return Intent.COUNTRY_VS_US
    if _OPPORTUNITY.search(question):
        return Intent.COUNTRY_OPPORTUNITIES
    return Intent.GENERAL


def detect_period(question: str, intent: Intent, today: date) -> Period:
    q = question.lower()
    relative = _RELATIVE.search(q)
    if "today" in q:
        days, label = 1, "today"
    elif "yesterday" in q:
        days, label = 2, "since yesterday"
    elif relative:
        days = int(relative.group(1)) * _UNIT_DAYS[relative.group(2).lower()]
        label = relative.group(0)
    elif re.search(r"\b(this|past|last) week\b", q):
        days, label = 7, "this week"
    elif re.search(r"\b(this|past|last) month\b", q):
        days, label = 30, "this month"
    elif re.search(r"\b(this|past|last) year\b", q):
        days, label = 365, "this year"
    elif re.search(r"\b(recent|recently|latest|newest)\b", q):
        days, label = 14, "recent"
    else:
        days = _DEFAULT_WINDOW_DAYS[intent]
        label = f"last {days} days"
    start = today - timedelta(days=days - 1)
    return Period(start=start, end=today, label=f"{label} ({start.isoformat()} to {today})")


def plan_query(request: AskRequest, today: date) -> QueryPlan:
    question = request.question.strip()
    requested_country: Country | None = None
    if request.country:
        requested_country = lookup_country(request.country) or Country(
            code=request.country.strip().upper()[:3], name=request.country.strip()
        )

    unresolved_placeholder = COUNTRY_PLACEHOLDER in question and requested_country is None
    if COUNTRY_PLACEHOLDER in question and requested_country is not None:
        question = question.replace(COUNTRY_PLACEHOLDER, requested_country.name)

    mentioned = find_countries(question)
    non_us = [c for c in mentioned if c.code != "US"]
    us_mentioned = any(c.code == "US" for c in mentioned)
    target = requested_country or (non_us[0] if non_us else None)
    if target is None and us_mentioned:
        target = mentioned[0]
    has_comparison = bool(target and target.code != "US" and us_mentioned) or bool(
        target and _COMPARE.search(question) and len(mentioned) > 1
    )
    compare_country: Country | None = None
    if has_comparison and target is not None:
        others = [c for c in mentioned if c.code != target.code]
        compare_country = next((c for c in others if c.code == "US"), others[0] if others else None)

    intent = detect_intent(question, target is not None, has_comparison)
    plan = QueryPlan(
        question=question,
        intent=intent,
        mode=request.mode or detect_mode(question),
        audience=request.audience or detect_audience(question),
        country=target,
        compare_country=compare_country,
        period=detect_period(question, intent, today),
        topics=detect_topics(question),
    )
    if unresolved_placeholder or (intent in _COUNTRY_INTENTS and target is None):
        plan.needs_clarification = True
        plan.clarification = (
            "Which country would you like me to analyze? For example: Malaysia, India, "
            "Singapore, United Kingdom, Japan, Germany, Canada or UAE."
        )
    return plan
