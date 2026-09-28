---
name: intel-agent-ui-testing
description: Local browser testing of the intelligence agent, no-key evidence, exports and responsive tables.
---

## Setup
Repo: /home/ubuntu/repos/devin-projects.
Create a Python virtualenv, install `-e ".[dev]"`, and run
`.venv/bin/uvicorn intel_agent.main:app --port 8000` from the repository.
Reuse an existing server when possible. Static index.html changes need only reload.
No authentication is needed at localhost:8000.

## Devin Secrets Needed
None for evidence-only UI testing. LLM_API_KEY and FRED_API_KEY are optional;
without them, corresponding status pills should show off. Do not claim synthesis
or FRED integration coverage when keys are absent.

## Focused UI paths
Country vs. United States quick-start → Country Malaysia → Ask gives comparison
tables. Answer contains a five-column Markdown table; Data pivots indicators into
country columns. Missing-country questions offer an inline Analyze field.

## Responsive and export assertions
Use Chrome responsive mode at 400 CSS pixels and measure documentElement
clientWidth and scrollWidth. Do not infer viewport width from screenshot pixels.
Measure each visible .tablewrap independently on Answer and Data. overflow-x:auto
alone does not demonstrate scrolling: require scrollWidth > clientWidth and a
native scroll gesture that changes scrollLeft without moving page scrollX.
Watch for over-aggressive word/number wrapping even when page overflow is fixed.

Click Copy answer, paste into the question without submitting, and compare its
value with lastAnswer via browser inspection. If emulated touch focus prevents
keyboard paste, Tab then Shift+Tab can restore native textarea keyboard focus.
Click Download .md and compare downloaded file SHA-256 with Web Crypto SHA-256
of lastAnswer. Duplicate downloads may have numbered suffixes.

Exit device mode and close DevTools for desktop regression evidence. Expect
single-row toolbar and equal page client/scroll widths. Temporary files may be
lost after VM restart; verify artifact paths before reporting them.
