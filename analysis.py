"""
Positioning analysis for the Legacy Report (Futures Only) COT file.

Scope is deliberately narrow for v1: one report (Legacy, Futures Only), one
metric (net non-commercial position, its percentile rank against that
market's own history, and its change from the prior report). This is the
classic "how crowded is speculative positioning" read; other report types
(Disaggregated's Managed Money, TFF) can get their own pass later without
touching this one.

Column positions below are the Legacy "Futures Only" long-format layout,
confirmed from a historical year's own header row (every extracted archive
carries one; the current year's live file does not, but shares the same
column order) and from CFTC's published variable list at
HistoricalViewable/cotvariableslegacy.html. Reading positionally rather than
by header name is what lets the current year's headerless file and each
historical year's headered file share one code path.

Public interface:
    load_category_rows(category_dir) -> {market_name: [(as_of, net_noncommercial, open_interest), ...]}
    build_report(by_market) -> markdown str
"""

import csv
from datetime import date
from pathlib import Path

_MARKET_COL = 0
_DATE_COL = 2
_OPEN_INTEREST_COL = 7
_NC_LONG_COL = 8
_NC_SHORT_COL = 9

MarketHistory = dict[str, list[tuple[str, int, int]]]


def load_category_rows(category_dir: Path) -> MarketHistory:
    """Read every *.txt in a category's folder into one history per market.

    Historical files carry a header row (skipped by column-count/type
    sniffing below); the current year's file does not. Rows are pooled
    across all files and then sorted by date, so it doesn't matter that
    files arrive one-per-year.
    """
    by_market: MarketHistory = {}

    for txt_file in sorted(category_dir.glob("*.txt")):
        with txt_file.open(encoding="utf-8", errors="replace", newline="") as f:
            for row in csv.reader(f):
                if len(row) <= _NC_SHORT_COL:
                    continue
                try:
                    open_interest = int(row[_OPEN_INTEREST_COL])
                    nc_long = int(row[_NC_LONG_COL])
                    nc_short = int(row[_NC_SHORT_COL])
                except ValueError:
                    continue  # the header row, or a malformed line
                market = row[_MARKET_COL].strip()
                as_of = row[_DATE_COL].strip()
                by_market.setdefault(market, []).append((as_of, nc_long - nc_short, open_interest))

    for history in by_market.values():
        history.sort(key=lambda r: r[0])
    return by_market


def _percentile_rank(history_values: list[int], latest: int) -> float:
    """Where the latest value sits versus its own market's full history, 0-100."""
    at_or_below = sum(1 for v in history_values if v <= latest)
    return 100 * at_or_below / len(history_values)


_MIN_OPEN_INTEREST = 20_000  # excludes thin/illiquid contracts (small basis, nodal power, micro contracts)
_HIGHLIGHT_COUNT = 12

# The Legacy report covers every CFTC-regulated future, not just physical
# commodities -- it's the original report, predating the 2009 Disaggregated
# split, and still carries rates, FX, equity index, and (more recently)
# crypto derivatives alongside corn and crude. This is a manually curated
# exclusion of the non-commodity instruments actually seen in the data as of
# 2026-08-25, matched case-insensitively as a substring of the market name.
# Extend it if a new financial product shows up in a future report.
_NON_COMMODITY_KEYWORDS = [
    # interest rates
    "UST ", "T-NOTE", "T-BOND", "SOFR", "FED FUND", "EURODOLLAR", "YIELD",
    "BUND", "SCHATZ", "BOBL", "OVERNIGHT", "TREASURY", "SHORT TERM RATE",
    # currencies
    "EURO FX", "JAPANESE YEN", "BRITISH POUND", "SWISS FRANC",
    "CANADIAN DOLLAR", "AUSTRALIAN DOLLAR", "NEW ZEALAND DOLLAR", "NZ DOLLAR",
    "MEXICAN PESO", "BRAZILIAN REAL", "SOUTH AFRICAN RAND", "DOLLAR INDEX",
    # equity indices
    "S&P", "NASDAQ", "DOW JONES", "DJIA", "RUSSELL", "NIKKEI", "VIX", "MSCI",
    "STOCK INDEX", "BLOOMBERG COMMODITY", "BBG COMMODITY",
    # crypto
    "BITCOIN", "ETHER", "COINBASE DERIVATIVES", "MICRO SOL",
]

# These two exchanges list power-grid nodal contracts, pipeline gas-basis
# differentials, RECs and carbon credits -- real markets, but utility
# hedging instruments rather than "the commodity market" in the sense this
# report means. None of the benchmark physical commodities (crude, Henry
# Hub gas, metals, grains, softs, livestock) trade under either exchange
# name; they're on CBOT/CME/NYMEX/COMEX/ICE Futures U.S. instead.
_NON_COMMODITY_EXCHANGES = ["ICE FUTURES ENERGY DIV", "NODAL EXCHANGE"]


def _is_commodity(market: str) -> bool:
    upper = market.upper()
    if any(exch in upper for exch in _NON_COMMODITY_EXCHANGES):
        return False
    return not any(keyword in upper for keyword in _NON_COMMODITY_KEYWORDS)


def _table(rows: list[tuple[str, str, int, int, float]]) -> str:
    lines = ["| Market | As of | Net Non-Commercial | Change vs prior report | Percentile vs history |",
              "|---|---|---|---|---|"]
    for market, as_of, net, change, pct in rows:
        lines.append(f"| {market} | {as_of} | {net:+,} | {change:+,} | {pct:.0f}th |")
    return "\n".join(lines)


def build_report(by_market: MarketHistory, title: str = "Legacy Report (Futures Only)") -> str:
    """Render a curated highlights summary rather than every market.

    This report alone tracks ~340 markets, most of them thin basis or
    electricity-node contracts nobody means when they say "the commodity
    market". _MIN_OPEN_INTEREST filters those out, and the report itself
    surfaces the extremes (most crowded long/short, biggest movers) rather
    than a full dump -- the point is "what's worth knowing," not "everything
    that exists."
    """
    # A market that stopped being reported decades ago still trivially ranks
    # "100th percentile" against its own short, ancient history otherwise --
    # only markets reported as of the most recent date anyone has are still
    # active and worth surfacing.
    latest_overall = max((h[-1][0] for h in by_market.values() if h), default=None)

    rows = []
    for market, history in by_market.items():
        if len(history) < 2 or history[-1][0] != latest_overall:
            continue
        latest_date, latest_net, latest_oi = history[-1]
        if latest_oi < _MIN_OPEN_INTEREST or not _is_commodity(market):
            continue
        nets = [h[1] for h in history]
        prev_net = history[-2][1]
        rows.append((market, latest_date, latest_net, latest_net - prev_net, _percentile_rank(nets, latest_net)))

    lines = [
        f"# COT Weekly Report - {title}",
        "",
        f"Generated {date.today().isoformat()} for the report as of {latest_overall}. "
        f"{len(rows)} markets with at least {_MIN_OPEN_INTEREST:,} open interest. Percentile is "
        "versus each market's own full available history; higher means a more crowded net-long "
        "speculative position.",
        "",
        "## Most crowded net-long",
        "",
        _table(sorted(rows, key=lambda r: r[4], reverse=True)[:_HIGHLIGHT_COUNT]),
        "",
        "## Most crowded net-short",
        "",
        _table(sorted(rows, key=lambda r: r[4])[:_HIGHLIGHT_COUNT]),
        "",
        "## Biggest moves this week",
        "",
        _table(sorted(rows, key=lambda r: abs(r[3]), reverse=True)[:_HIGHLIGHT_COUNT]),
    ]
    return "\n".join(lines)
