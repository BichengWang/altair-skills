# Altair skills

Agent skills from [Altair AI](https://altairworld.com). They read live data from Altair's free public MCP server, so an installed skill always returns the newest research without updates.

## altair-index-research

The latest weekly AI research on four index ETFs: **SPY** (S&P 500), **QQQ** (Nasdaq-100), **SOXX** (semiconductors) and **XBI** (biotech), plus 60+ covered stocks.

Each week Claude, GPT and Gemini each run the same multi-agent [TradingAgents](https://github.com/BichengWang/TradingAgents) pipeline on every ticker: technical, sentiment, news and fundamentals analysts, a bull/bear debate, a trader, a risk team and a portfolio manager. Reports are published at [altairworld.com/TradingAgents](https://altairworld.com/TradingAgents/). The skill pulls every model's final decision for the newest analysis date and shows where the models disagree:

```text
## SOXX · analysis date 2026-10-21 · 4 models: 2 Hold, 2 Underweight

| Model            | Rating      | Close at report | Target | Target vs close | Confidence | Horizon    |
| claude-fable-5-1 | Hold        | 510.36          | 522.51 | +2.4%           | Low        | 1-2 months |
| gpt-6-astra      | Underweight | 512.64          | 493.39 | -3.8%           | Medium     | 4-8 weeks  |
| gemini-4-argon   | Underweight | 510.36          | 470.12 | -7.9%           | High       | 1-3 months |
| claude-opus-5-5  | Hold        | 512.64          | 535.33 | +4.4%           | Medium     | 1-2 months |
```

Then ask your agent things like "What do the AI models think of the semiconductor ETF this week?" or "Why is GPT underweight XBI?"

### Install

Any agent that supports skills (Claude Code, Codex, Cursor, Gemini CLI and others), using the [skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add BichengWang/altair-skills --skill altair-index-research
```

Claude Code plugin:

```bash
claude plugin marketplace add BichengWang/altair-skills
claude plugin install altair@altair-skills
```

Or copy `skills/altair-index-research` into your agent's skills folder.

Needs Python 3.8+ and internet access. No API key or sign-in.

### Run it yourself

```bash
python3 skills/altair-index-research/scripts/altair_research.py latest
python3 skills/altair-index-research/scripts/altair_research.py latest NVDA --date 2026-10-14
python3 skills/altair-index-research/scripts/altair_research.py report <report-url> --section risk
```

The script calls the MCP tools `list_research_reports` and `read_research_report` at `https://altairworld.com/mcp` over plain HTTPS. To use those tools directly in an MCP client instead: `claude mcp add --transport http altair https://altairworld.com/mcp`. See [altairworld.com/mcp](https://altairworld.com/mcp) for the other free tools, such as market breadth.

## Disclaimer

The reports are AI-generated for AI testing and experimentation only. They are not financial or investment advice, may contain errors, and must not be used to make investment or trading decisions.

## License

[MIT](LICENSE)
