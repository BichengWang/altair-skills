#!/usr/bin/env python3
"""Fetch the newest Altair TradingAgents research through the public MCP server.

Standard library only (Python 3.8+). No API key, no MCP client setup.

  python3 altair_research.py tickers                   # covered tickers and report counts
  python3 altair_research.py latest                    # SPY QQQ SOXX XBI, newest analysis date
  python3 altair_research.py latest NVDA AAPL          # any covered ticker
  python3 altair_research.py latest SPY --date 2026-10-14
  python3 altair_research.py report <url> [--section pm|analysts|research|trader|risk|full]
"""

import argparse
import concurrent.futures
import datetime
import json
import re
import sys
import time
import urllib.error
import urllib.request

ENDPOINT = "https://altairworld.com/mcp"
INDEX_TICKERS = ["SPY", "QQQ", "SOXX", "XBI"]
PAGE_SIZE = 100
WORKERS = 2
ATTEMPTS = 3
STALE_DAYS = 10
SUMMARY_CHARS = 600
DISCLAIMER = ("AI-generated reports for AI testing and experimentation only. They are not financial or "
              "investment advice and may contain errors; do not use them to make investment or trading decisions.")
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    # The endpoint sits behind Cloudflare, which rejects the default Python-urllib agent.
    "User-Agent": "altair-research-skill/1.1",
}
SECTIONS = {
    "analysts": "## I. ",
    "research": "## II. ",
    "trader": "## III. ",
    "risk": "## IV. ",
    "pm": "## V. ",
}


class ToolError(Exception):
    pass


class Transient(Exception):
    pass


def post(body):
    request = urllib.request.Request(ENDPOINT, data=body, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            text = response.read().decode("utf-8")
            streamed = "text/event-stream" in response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as error:
        if error.code in (429, 500, 502, 503, 504):
            raise Transient("HTTP {}".format(error.code))
        raise ToolError("{} returned HTTP {}".format(ENDPOINT, error.code))
    except (urllib.error.URLError, OSError) as error:
        raise Transient(str(getattr(error, "reason", error)))
    if streamed:
        events = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")]
        if not events:
            raise Transient("empty event stream")
        text = events[-1]
    return json.loads(text)


def call_tool(name, arguments):
    body = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
    ).encode()
    # The server is a Cloudflare Worker that sometimes drops a request under load; reads are idempotent.
    for attempt in range(ATTEMPTS):
        try:
            message = post(body)
            break
        except Transient as error:
            if attempt == ATTEMPTS - 1:
                raise ToolError("{} failed after {} attempts: {}".format(name, ATTEMPTS, error))
            time.sleep(2 ** attempt)
    if "error" in message:
        raise ToolError("{}: {}".format(name, message["error"].get("message", message["error"])))
    result = message["result"]
    if result.get("isError"):
        detail = " ".join(part.get("text", "") for part in result.get("content", []))
        raise ToolError("{}: {}".format(name, detail.strip() or "tool error"))
    if result.get("structuredContent") is not None:
        return result["structuredContent"]
    return json.loads(result["content"][0]["text"])


def covered_tickers():
    # A ticker filter that matches nothing still returns counts for every covered ticker.
    return call_tool("list_research_reports", {"ticker": "-", "limit": 1}).get("tickers", [])


def runs_for(ticker, date):
    """Newest run per model on `date` (the newest analysis date when None) and, if uncovered, the covered list."""
    picked, seen, offset = [], set(), 0
    while True:
        page = call_tool("list_research_reports", {"ticker": ticker, "limit": PAGE_SIZE, "offset": offset})
        reports = page.get("reports", [])
        for report in reports:
            if date is None:
                date = report["date"]
            if report["date"] > date:
                continue
            if report["date"] < date:
                return date, picked, None
            # Listing is newest first, so the first run seen per model is its latest rerun.
            if report["model"] not in seen:
                seen.add(report["model"])
                picked.append(report)
        offset += len(reports)
        if not reports or offset >= page.get("total", 0):
            if offset == 0:
                return None, [], [t["ticker"] for t in page.get("tickers", [])]
            return date, picked, None


def section(markdown, name):
    if name == "full":
        return markdown
    start = markdown.find(SECTIONS[name])
    if start < 0:
        return ""
    following = [markdown.find(h, start + 1) for h in SECTIONS.values()]
    end = min([i for i in following if i > start] or [len(markdown)])
    return markdown[start:end].strip()


def field(text, label):
    match = re.search(r"^\*\*" + re.escape(label) + r"\*\*:?[ \t]*(.*)$", text, re.M)
    return match.group(1).strip() if match else ""


def first_number(value):
    match = re.search(r"\d[\d,]*(?:\.\d+)?", value)
    return float(match.group(0).replace(",", "")) if match else None


def short(value, limit):
    value = value.strip().lstrip(":").strip()
    if len(value) <= limit:
        return value
    cut = value[:limit]
    stop = cut.rfind(". ")
    return cut[: stop + 1] if stop > limit // 2 else cut.rstrip() + "…"


def decision(report):
    row = {"model": report["model"], "url": report["url"]}
    try:
        data = call_tool("read_research_report", {"url": report["url"]})
    except ToolError as error:
        row["error"] = str(error)
        return row
    pm = section(data["markdown"], "pm")
    summary = ""
    if "**Executive Summary**" in pm:
        summary = pm.split("**Executive Summary**", 1)[1].split("**Investment Thesis**", 1)[0]
    close = first_number(field(pm, "Current Price"))
    target = first_number(field(pm, "Price Target"))
    row.update({
        "rating": field(pm, "Rating") or "not stated",
        "close": close,
        "target": target,
        "upside": (target / close - 1) if close and target else None,
        "confidence": re.split(r"[.;,(]", field(pm, "Confidence"))[0].strip() or "not stated",
        "horizon": short(re.split(r"\. ", field(pm, "Time Horizon"))[0], 60) or "not stated",
        "summary": " ".join(summary.split()),
    })
    return row


def money(value):
    return "n/a" if value is None else "{:,.2f}".format(value)


def render_ticker(ticker, date, rows, summary_chars, covered):
    if covered is not None:
        return "## {}\n\nNot covered. Run `tickers` for the covered list.\n".format(ticker)
    if not rows:
        return "## {}\n\nNo reports for analysis date {}.\n".format(ticker, date)
    read = [row for row in rows if "error" not in row]
    counts = {}
    for row in read:
        counts[row["rating"]] = counts.get(row["rating"], 0) + 1
    split = ", ".join("{} {}".format(n, rating) for rating, n in sorted(counts.items(), key=lambda kv: -kv[1]))
    lines = [
        "## {} · analysis date {} · {} models: {}".format(ticker, date, len(read), split or "none readable"),
        "",
        "| Model | Rating | Close at report | Target | Target vs close | Confidence | Horizon |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in read:
        upside = "n/a" if row["upside"] is None else "{:+.1%}".format(row["upside"])
        lines.append("| [{}]({}) | {} | {} | {} | {} | {} | {} |".format(
            row["model"], row["url"], row["rating"], money(row["close"]), money(row["target"]),
            upside, row["confidence"], row["horizon"]))
    for row in rows:
        if "error" in row:
            lines.append("| [{}]({}) | unavailable: {} | | | | | |".format(row["model"], row["url"], row["error"]))
    lines.append("")
    for row in read:
        lines.append("- **{}**: {}".format(row["model"], short(row["summary"], summary_chars) or "no summary"))
    return "\n".join(lines) + "\n"


def normalize(raw):
    tickers = []
    for item in raw:
        for part in re.split(r"[,\s]+", item):
            ticker = part.strip().lstrip("$").upper()
            if ticker and ticker not in tickers:
                tickers.append(ticker)
    return tickers


def latest(args):
    tickers = normalize(args.tickers) or INDEX_TICKERS
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        listed = dict(zip(tickers, pool.map(lambda t: runs_for(t, args.date), tickers)))
        jobs = [(t, r) for t in tickers for r in listed[t][1]]
        decisions = list(pool.map(lambda job: decision(job[1]), jobs))
    by_ticker = {t: [] for t in tickers}
    for (ticker, _), row in zip(jobs, decisions):
        by_ticker[ticker].append(row)

    today = datetime.date.today()
    out = [
        "# Altair TradingAgents research (fetched {})".format(today.isoformat()),
        "",
        "Source: https://altairworld.com/TradingAgents/ through the public MCP server {}. "
        "Each model runs the same multi-agent pipeline (analysts, bull/bear debate, trader, risk team, "
        "portfolio manager); rows are the portfolio manager's final decision. "
        "\"Close at report\" is the report-time close, not a live quote.".format(ENDPOINT),
        "",
    ]
    for ticker in tickers:
        date, _, covered = listed[ticker]
        out.append(render_ticker(ticker, date, by_ticker[ticker], args.summary_chars, covered))
        if date and (today - datetime.date.fromisoformat(date)).days > STALE_DAYS:
            out.append("> {} research is from {}, more than {} days old.\n".format(ticker, date, STALE_DAYS))
    out.append("Disclaimer: " + DISCLAIMER)
    print("\n".join(out))


def tickers(args):
    covered = covered_tickers()
    index = [t for t in covered if t["ticker"] in INDEX_TICKERS]
    others = [t for t in covered if t["ticker"] not in INDEX_TICKERS]
    print("# Tickers with Altair research ({} covered)\n".format(len(covered)))
    print("Report counts are all runs across models and dates. Index ETFs are refreshed about weekly; "
          "other tickers less regularly, so check the analysis date `latest` prints.\n")
    for title, group in (("Index ETFs", index), ("Stocks and other funds", others)):
        print("{}: {}\n".format(title, ", ".join("{} ({})".format(t["ticker"], t["reports"]) for t in group)))


def report(args):
    data = call_tool("read_research_report", {"url": args.url})
    print("# {} · {} · {}\n{}\n".format(data["ticker"], data["date"], data["model"], data["url"]))
    print(section(data["markdown"], args.section) or "Section not found in this report.")
    print("\nDisclaimer: " + DISCLAIMER)


def analysis_date(value):
    try:
        return datetime.date.fromisoformat(value).isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError("expected a YYYY-MM-DD date, got {!r}".format(value))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    tickers_parser = commands.add_parser("tickers", help="covered tickers with report counts")
    tickers_parser.set_defaults(run=tickers)
    latest_parser = commands.add_parser("latest", help="final decisions from every model on the newest analysis date")
    latest_parser.add_argument("tickers", nargs="*",
                               help="tickers, space- or comma-separated (default: {})".format(" ".join(INDEX_TICKERS)))
    latest_parser.add_argument("--date", type=analysis_date, help="analysis date YYYY-MM-DD instead of the newest")
    latest_parser.add_argument("--summary-chars", type=int, default=SUMMARY_CHARS,
                               help="executive summary length per model (default %(default)s)")
    latest_parser.set_defaults(run=latest)
    report_parser = commands.add_parser("report", help="one section of a report url from `latest`")
    report_parser.add_argument("url")
    report_parser.add_argument("--section", choices=list(SECTIONS) + ["full"], default="pm")
    report_parser.set_defaults(run=report)
    args = parser.parse_args()
    try:
        args.run(args)
    except ToolError as error:
        sys.exit("altair_research: {}".format(error))


if __name__ == "__main__":
    main()
