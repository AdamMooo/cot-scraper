"""
Positioning + price analysis for the Legacy Report (Futures Only) COT file.

Scope is deliberately narrow for v1: one report (Legacy, Futures Only), one
positioning metric (net non-commercial position, its percentile rank
against that market's own history, and its change from the prior report),
compared against what price actually did over the same week
(prices.py). Comparing the two -- not positioning in isolation -- is the
actual point: "is speculative positioning stretched, and did price move
with or against that stretch" is the question a COT reader is usually
asking.

Which markets get analyzed at all is driven by prices.MARKET_TICKERS, an
allow-list of benchmark commodities with a real price series, rather than a
list of things to exclude. Earlier attempts at excluding non-commodities by
keyword/exchange kept missing cases (rates, FX, equity indices, crypto, and
~150 thin ICE Futures Energy Div / Nodal Exchange power-grid and
pipeline-basis contracts all dominated the extremes before this); requiring
a real ticker is what actually pins the report to "the commodity market"
and is also what makes the price comparison possible at all.

Column positions below are the Legacy "Futures Only" long-format layout,
confirmed from a historical year's own header row (every extracted archive
carries one; the current year's live file does not, but shares the same
column order) and from CFTC's published variable list at
HistoricalViewable/cotvariableslegacy.html.

Public interface:
    load_category_rows(category_dir) -> {market_name: [(as_of, net_noncommercial, open_interest), ...]}
    build_report(by_market) -> markdown str
"""

import csv
from datetime import date
from pathlib import Path

import prices

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


def merge_current_year_snapshot(snapshot_file: Path, accumulator_file: Path) -> None:
    """Merge this week's snapshot into the running current-year file this
    repo keeps for itself.

    CFTC's "current year" text file is only ever this week's single
    snapshot per market, not a running year-to-date file (confirmed
    2026-08-25 -- the live deafut.txt has exactly one row per market, the
    latest). Without this merge, every weekly automated run would overwrite
    last week's row with this week's, and the current year would never
    accumulate the history both the percentile ranking and the
    week-over-week comparison need. Keyed on (market, as_of), so re-running
    the same week is a no-op and a missed week just leaves a gap rather
    than breaking anything.
    """
    rows: dict[tuple[str, str], list[str]] = {}

    for source in (accumulator_file, snapshot_file):
        if not source.exists():
            continue
        with source.open(encoding="utf-8", errors="replace", newline="") as f:
            for row in csv.reader(f):
                if len(row) <= _NC_SHORT_COL:
                    continue
                try:
                    int(row[_OPEN_INTEREST_COL])
                except ValueError:
                    continue  # header row
                rows[(row[_MARKET_COL].strip(), row[_DATE_COL].strip())] = row

    accumulator_file.parent.mkdir(parents=True, exist_ok=True)
    with accumulator_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for key in sorted(rows):
            writer.writerow(rows[key])


# COT reports are weekly; a gap much larger than that between the latest
# report and the one before it means there IS no real "prior week" yet
# (e.g. the current year has only ever had one snapshot accumulated so
# far). Comparing against whatever's technically "previous" in that case --
# often the last week of the prior year, months away -- would look like a
# one-week move but actually be a multi-month one, which is worse than not
# showing a comparison at all.
_MAX_PLAUSIBLE_GAP_DAYS = 10


def _percentile_rank(history_values: list[int], latest: int) -> float:
    """Where the latest value sits versus its own market's full history, 0-100."""
    at_or_below = sum(1 for v in history_values if v <= latest)
    return 100 * at_or_below / len(history_values)


def build_report(by_market: MarketHistory, title: str = "Legacy Report (Futures Only)") -> str:
    """Render one markdown table: positioning next to the same week's price move.

    Only markets with a ticker in prices.MARKET_TICKERS are included (see
    module docstring for why). Markets with fewer than two dated rows are
    skipped -- there's no prior week to compare against yet.
    """
    # A market that stopped being reported decades ago still trivially ranks
    # "100th percentile" against its own short, ancient history otherwise --
    # only markets reported as of the most recent date anyone has are still
    # active and worth surfacing.
    latest_overall = max((h[-1][0] for h in by_market.values() if h), default=None)

    price_cache: dict[str, dict[str, float]] = {}
    rows = []
    for market, history in by_market.items():
        ticker = prices.ticker_for(market)
        if ticker is None or len(history) < 2 or history[-1][0] != latest_overall:
            continue

        nets = [h[1] for h in history]
        latest_date, latest_net, _latest_oi = history[-1]
        prior_date, prev_net, _prev_oi = history[-2]

        gap_days = (date.fromisoformat(latest_date) - date.fromisoformat(prior_date)).days
        has_prior_week = gap_days <= _MAX_PLAUSIBLE_GAP_DAYS

        change = latest_net - prev_net if has_prior_week else None
        price_move = None
        if has_prior_week:
            if ticker not in price_cache:
                price_cache[ticker] = prices.daily_closes(ticker)
            price_move = prices.price_change(price_cache[ticker], latest_date, prior_date)

        rows.append((market, latest_date, latest_net, change, _percentile_rank(nets, latest_net), price_move))

    rows.sort(key=lambda r: r[4], reverse=True)

    lines = [
        f"# COT Weekly Report - {title}",
        "",
        f"Generated {date.today().isoformat()} for the report as of {latest_overall}. "
        f"{len(rows)} benchmark commodities tracked. Percentile is versus each market's "
        "own full available history; higher means a more crowded net-long speculative "
        "position. Price change covers the same week as the position change.",
        "",
        "| Market | As of | Net Non-Commercial | Change vs prior report | Percentile vs history | Price change (same week) |",
        "|---|---|---|---|---|---|",
    ]
    for market, as_of, net, change, pct, price_move in rows:
        change_cell = f"{change:+,}" if change is not None else "n/a (no prior week yet)"
        price_cell = f"{price_move[1]:+.1f}%" if price_move else "n/a"
        lines.append(f"| {market} | {as_of} | {net:+,} | {change_cell} | {pct:.0f}th | {price_cell} |")

    return "\n".join(lines)
