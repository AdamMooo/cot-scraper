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
from dataclasses import dataclass
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


# A market in the top or bottom decile of its own history is "crowded" --
# stretched enough to be worth naming, not just a data point in the table.
_EXTREME_HIGH = 90
_EXTREME_LOW = 10


def _ordinal(n: float) -> str:
    i = round(n)
    if 11 <= i % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(i % 10, "th")
    return f"{i}{suffix}"


@dataclass
class MarketRow:
    market: str  # full CFTC name, "CORN - CHICAGO BOARD OF TRADE"
    as_of: str
    net: int
    change: int | None  # contracts vs. prior report; None if no real prior week yet
    pct: float  # percentile of `net` vs. this market's own full history
    price_move: tuple[float, float] | None  # (latest close, % change); None if unavailable

    @property
    def name(self) -> str:
        return self.market.rsplit(" - ", 1)[0]


def _collect_rows(by_market: MarketHistory) -> list[MarketRow]:
    """One MarketRow per currently-active, ticker-mapped, benchmark commodity.

    Only markets with a ticker in prices.MARKET_TICKERS are included (see
    module docstring for why). A market that stopped being reported decades
    ago would otherwise trivially rank "100th percentile" against its own
    short, ancient history, so only markets reported as of the most recent
    date anyone has are considered active.
    """
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

        rows.append(MarketRow(market, latest_date, latest_net, change, _percentile_rank(nets, latest_net), price_move))

    rows.sort(key=lambda r: r.pct, reverse=True)
    return rows


def _crowding_read(row: MarketRow) -> str:
    """One sentence: is price confirming this positioning extreme, or diverging from it."""
    direction = "long" if row.pct >= _EXTREME_HIGH else "short"

    if row.change is None or row.price_move is None:
        return (f"**{row.name}** sits at the {_ordinal(row.pct)} percentile of its own history "
                f"(crowded {direction}), but there's no prior-week data yet to say whether "
                "that's a new move or already been the case a while.")

    price_pct = row.price_move[1]
    price_dir = "up" if price_pct > 0.05 else "down" if price_pct < -0.05 else "roughly flat"
    confirming = (direction == "long" and price_pct > 0.05) or (direction == "short" and price_pct < -0.05)

    if price_dir == "roughly flat":
        verdict = "price hasn't confirmed either way yet"
    elif confirming:
        verdict = ("price is confirming the crowd for now -- momentum is with the position, "
                   "but a stretch this extreme is also historically the kind that unwinds "
                   "sharply once it turns")
    else:
        verdict = ("that's a **divergence**: price is moving against the crowded position, "
                   "which is often the first sign a stretched trade is starting to unwind")

    return (f"**{row.name}** is at the {_ordinal(row.pct)} percentile (crowded {direction}, "
            f"{row.change:+,} contracts this week) while price moved {price_dir} "
            f"{abs(price_pct):.1f}% over the same week -- {verdict}.")


def _key_takeaways(rows: list[MarketRow]) -> list[str]:
    extremes = [r for r in rows if r.pct >= _EXTREME_HIGH or r.pct <= _EXTREME_LOW]
    crowded_long = sum(1 for r in extremes if r.pct >= _EXTREME_HIGH)
    crowded_short = len(extremes) - crowded_long

    lines = [f"**{len(extremes)} of {len(rows)}** tracked commodities are at a positioning "
             f"extreme this week (top or bottom decile of their own history): "
             f"{crowded_long} crowded long, {crowded_short} crowded short."]
    if not extremes:
        return lines

    lines.append("")
    for row in extremes:
        lines.append(f"- {_crowding_read(row)}")

    biggest_movers = [r for r in rows if r.change is not None]
    biggest_movers.sort(key=lambda r: abs(r.change), reverse=True)
    if biggest_movers:
        lines.append("")
        lines.append("**Biggest positioning shifts this week:**")
        for row in biggest_movers[:5]:
            price_bit = f", price {row.price_move[1]:+.1f}%" if row.price_move else ""
            lines.append(f"- {row.name}: {row.change:+,} contracts ({_ordinal(row.pct)} percentile{price_bit})")

    return lines


def build_report(by_market: MarketHistory, title: str = "Legacy Report (Futures Only)") -> str:
    """Render the report: a plain-English read first, the supporting table second."""
    rows = _collect_rows(by_market)
    latest_overall = rows[0].as_of if rows else None

    lines = [
        f"# COT Weekly Report - {title}",
        "",
        f"Report as of {latest_overall}, generated {date.today().isoformat()}. "
        f"{len(rows)} benchmark commodities tracked.",
        "",
        "## Key takeaways",
        "",
        *_key_takeaways(rows),
        "",
        "## Full data",
        "",
        "Percentile is versus each market's own full available history; higher means a "
        "more crowded net-long speculative position. Price change covers the same week "
        "as the position change.",
        "",
        "| Market | As of | Net Non-Commercial | Change vs prior report | Percentile vs history | Price change (same week) |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        change_cell = f"{row.change:+,}" if row.change is not None else "n/a (no prior week yet)"
        price_cell = f"{row.price_move[1]:+.1f}%" if row.price_move else "n/a"
        lines.append(f"| {row.market} | {row.as_of} | {row.net:+,} | {change_cell} | {_ordinal(row.pct)} | {price_cell} |")

    return "\n".join(lines)
