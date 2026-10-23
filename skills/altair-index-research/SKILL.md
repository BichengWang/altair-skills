---
name: altair-index-research
description: Latest weekly AI research on the SPY (S&P 500), QQQ (Nasdaq-100), SOXX (semiconductors) and XBI (biotech) ETFs, plus 60+ covered stocks, from altairworld.com's free public MCP server. Several Claude, GPT and Gemini models each run the same multi-agent TradingAgents pipeline (analysts, bull/bear debate, trader, risk team, portfolio manager); this skill returns every model's final rating, price target, confidence, horizon and summary, and where they disagree. Use when the user asks for the outlook, rating, price target or AI research view on the broad market, Nasdaq, semiconductors, biotech, or one of these ETFs or a covered stock. No API key. Research for information only, not investment advice.
---

# Altair index research

Fetches the newest published reports from <https://altairworld.com/TradingAgents/> through Altair's public MCP server (`https://altairworld.com/mcp`, tools `list_research_reports` and `read_research_report`). No key, no sign-in, no MCP setup. The index ETFs are re-run about weekly, so every call returns current data without updating this skill.

## Run

Use Python 3.8+ (standard library only). The script is in this skill's `scripts/` folder:

```bash
python3 scripts/altair_research.py latest                        # SPY QQQ SOXX XBI
python3 scripts/altair_research.py latest SOXX NVDA              # any covered ticker
python3 scripts/altair_research.py latest XBI --date 2026-10-14  # an earlier analysis date
python3 scripts/altair_research.py report <report-url> --section risk
```

- `latest` prints one block per ticker for its newest analysis date: a table with each model's final rating, report-time close, target, target vs close, confidence and horizon, then each model's executive summary. `--summary-chars N` shortens or lengthens summaries (default 600).
- `report` prints one section of a report URL from `latest`: `pm` (portfolio manager, default), `analysts` (technical, sentiment, news, fundamentals), `research` (bull/bear debate), `trader`, `risk`, or `full` (150–300 KB; avoid unless asked).
- An uncovered ticker prints the covered list. Exit status 1 means the server was unreachable or rejected the call; say so instead of guessing.

If the Altair MCP server is already connected, its `list_research_reports` and `read_research_report` tools reach the same data, but full reports are large; prefer the script, which reads only the decision section.

## Answering

1. Lead with the analysis date and the split, e.g. "SOXX, 2026-10-21: 2 Hold, 2 Underweight." Disagreement between models is the signal; don't average ratings into one verdict.
2. Give the table, then the key reasons on each side from the summaries. For "why", run `report <url> --section research` or `--section risk` for the relevant model.
3. Say that closes are report-time, not live, and flag research older than about 10 days (the script marks it).
4. Link the report URLs so the user can read the full reasoning.
5. End with the disclaimer: AI-generated research for testing and information only, not financial or investment advice. Never turn it into a personal buy or sell instruction or position size for the user.

ETF reports are mostly technical, macro and sentiment analysis; their fundamentals section is thin (no holdings or NAV data). Say so if the user asks for fundamental valuation.
