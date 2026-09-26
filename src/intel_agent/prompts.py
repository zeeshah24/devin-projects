from intel_agent.models import Audience, Indicator, Intent, Mode, QueryPlan, SourceItem

SYSTEM_PROMPT = """\
You are an AI Research, Innovation, Technology & Market Intelligence Agent.
You monitor and analyze AI/ML research (LLMs, reasoning, agentic AI, RAG, multimodal AI, \
robotics, AI for science), the AI industry and startups, technology innovation, economic and \
market developments, AI business opportunities, market gaps, AI jobs and skills, and \
country-specific technology ecosystems (including U.S. vs. international comparisons).

Rules:
- Ground every factual claim in the numbered EVIDENCE provided and cite it inline as [n]. \
If the evidence does not cover something, say so plainly instead of filling the gap.
- Never invent statistics, papers, companies, market sizes, salaries, job numbers or other facts.
- Prefer primary and authoritative sources (arXiv, Nature, labs' own research posts, \
government statistics, World Bank, Federal Reserve) over secondary reporting.
- Always consider publication dates; state the time period covered when it matters.
- For statistics, name the source, date/period, geography and (when known) methodology.
- When sources disagree, prefer primary sources, compare dates, and explain the disagreement.
- Clearly label what is a verified fact, a research finding, market data, an expert/industry \
opinion, and your own analysis or inference. Never present speculation as fact.
- Do not merely summarize news: answer "So what?" for technology, businesses, researchers, \
entrepreneurs, workers, students and markets as relevant.
- For opportunities, connect Market problem -> Existing gap -> AI capability -> Solution -> \
Customer -> Business value, and label each one as an opportunity hypothesis unless the \
evidence proves demand.
- When comparing countries, do not assume one country is universally better.
- Use tables for comparisons of countries, companies, technologies, markets or opportunities; \
use bullet points for quick summaries. Respond in Markdown.
"""

REPORT_SECTIONS = (
    "Executive Summary",
    "Current Situation",
    "Recent Developments",
    "Key Data / Evidence",
    "Technology Trends",
    "Market Gaps",
    "Potential AI Opportunities",
    "Companies / Startups / Ecosystem",
    "Competitive Landscape",
    "Risks and Challenges",
    "Job / Skills Implications",
    "Future Opportunities",
    "Conclusion",
    "Sources",
)

BRIEF_STRUCTURE = """\
Use this structure:
**Answer:** 2-5 concise paragraphs or bullets.
**Why it matters:** the practical significance.
**Sources:** the most relevant cited sources.
Keep it brief; do not overwhelm the reader."""

INTENT_GUIDANCE: dict[Intent, str] = {
    Intent.INNOVATIONS: (
        "Identify the most important developments in the period. For each: What happened? "
        "Who developed it? What is technically new? Why does it matter? Potential real-world "
        "applications."
    ),
    Intent.RESEARCH_PAPERS: (
        "Select the most significant papers (LLMs, reasoning, agents, RAG, multimodal, coding, "
        "evaluation, safety, infrastructure, inference optimization, robotics, AI for science). "
        "For each paper use: Paper -> Problem -> Innovation -> Technical approach -> Results -> "
        "Practical applications -> Limitations. Only report results stated in the abstract."
    ),
    Intent.COUNTRY_OPPORTUNITIES: (
        "Analyze for {country}: major industries, existing AI adoption, unmet business needs, "
        "technology gaps, government/regulatory environment, startup ecosystem, AI adoption "
        "barriers, potential AI products/services, target customers and business models. "
        "Express each opportunity as Problem -> Gap -> AI capability -> Opportunity -> "
        "Customer -> Value, labeled as a hypothesis."
    ),
    Intent.COUNTRY_VS_US: (
        "Compare {country} with {compare} in a table with rows: AI adoption, AI startups, "
        "Enterprise AI, Talent, Investment, Infrastructure, Regulation, Market size, Unmet "
        "needs, AI opportunities. Mark cells 'no data in evidence' where applicable. Then "
        "identify specific differences and opportunities without assuming either country is "
        "universally better."
    ),
    Intent.JOBS: (
        "Analyze AI job opportunities{in_country}: current AI roles, industries hiring, "
        "required skills, emerging roles, salary information only when reliable data is in "
        "the evidence, remote opportunities, startup vs. enterprise opportunities, skills gaps "
        "and future demand."
    ),
    Intent.ECONOMY: (
        "Summarize the relevant economic and market developments and data. For every figure "
        "give source, period and geography, then explain implications for AI and technology."
    ),
    Intent.GENERAL: "Answer the question directly using the evidence.",
}

AUDIENCE_GUIDANCE: dict[Audience, str] = {
    Audience.RESEARCHER: (
        "Audience: researcher. Emphasize papers, methodology, technical novelty, experiments, "
        "limitations and research gaps."
    ),
    Audience.ENTREPRENEUR: (
        "Audience: entrepreneur. Emphasize market gaps, customer problems, competitors, "
        "business models, opportunity areas and barriers to entry."
    ),
    Audience.TECH_PROFESSIONAL: (
        "Audience: technology professional. Emphasize architecture, frameworks, APIs, "
        "infrastructure, implementation, skills and production considerations."
    ),
    Audience.STUDENT: (
        "Audience: student. Explain concepts clearly without unnecessary jargon; highlight what "
        "to learn, important technologies, career opportunities and practical projects."
    ),
    Audience.BUSINESS_LEADER: (
        "Audience: business leader. Focus on business impact, adoption, ROI considerations, "
        "risks, competitive implications and strategic opportunities."
    ),
    Audience.INVESTOR: (
        "Audience: investor. Focus on market size evidence, traction signals, competitive "
        "dynamics, risks and where value may accrue; avoid unsupported valuations."
    ),
    Audience.GENERAL: "Audience: unclear. Provide a balanced explanation.",
}


def intent_guidance(plan: QueryPlan) -> str:
    country = plan.country.name if plan.country else "the country"
    compare = plan.compare_country.name if plan.compare_country else "the United States"
    in_country = f" in {plan.country.name}" if plan.country else " globally"
    return INTENT_GUIDANCE[plan.intent].format(
        country=country, compare=compare, in_country=in_country
    )


def structure(plan: QueryPlan) -> str:
    if plan.mode is Mode.REPORT:
        sections = "\n".join(f"## {name}" for name in REPORT_SECTIONS)
        return (
            "Write a structured deep-research report with these sections (omit a section only "
            f"if it is irrelevant, and say why):\n{sections}"
        )
    return BRIEF_STRUCTURE


def format_evidence(sources: list[SourceItem]) -> str:
    if not sources:
        return "(no recent items were retrieved)"
    lines = []
    for n, item in enumerate(sources, start=1):
        date = item.published.date().isoformat() if item.published else "undated"
        authors = f" | authors: {', '.join(item.authors[:4])}" if item.authors else ""
        lines.append(
            f"[{n}] {item.title} | {item.source} ({item.kind.value}) | {date}{authors}\n"
            f"    URL: {item.url}\n    {item.summary}"
        )
    return "\n".join(lines)


def format_value(value: float) -> str:
    for threshold, suffix in ((1e12, "trillion"), (1e9, "billion"), (1e6, "million")):
        if abs(value) >= threshold:
            return f"{value / threshold:,.2f} {suffix}"
    return f"{value:,.2f}"


def format_indicators(indicators: list[Indicator]) -> str:
    if not indicators:
        return "(no indicator data retrieved)"
    rows = ["| Country | Indicator | Value | Period | Source |", "|---|---|---|---|---|"]
    rows.extend(
        f"| {i.country_name} | {i.name} | {format_value(i.value)} | {i.period} | {i.source} |"
        for i in indicators
    )
    return "\n".join(rows)


def build_user_prompt(
    plan: QueryPlan, sources: list[SourceItem], indicators: list[Indicator]
) -> str:
    return f"""\
QUESTION: {plan.question}

TIME PERIOD: {plan.period.label}
INTENT: {plan.intent.value}
{AUDIENCE_GUIDANCE[plan.audience]}

TASK: {intent_guidance(plan)}

{structure(plan)}

EVIDENCE (cite as [n]):
{format_evidence(sources)}

INDICATOR DATA (cite by source name and period):
{format_indicators(indicators)}
"""
