"""
Reads the Legacy (Futures Only) COT file and builds the weekly report.

The universe is contracts.COMMODITIES -- 24 benchmark commodities, each
defined as a *chain* of CFTC names so a 40-year history survives the
exchange renames that would otherwise shatter it (see contracts.py; this
was a real bug that made copper's 33-year history read as 205 weeks).

The report is deliberately descriptive. An earlier version asserted that
crowded positioning "could unwind sharply", which sounds like analysis but
is unfalsifiable. study.py went and measured it across 185 pooled
historical episodes in 87 distinct quarters: forward returns after a
crowded reading are indistinguishable from chance (reversion hit rates
42-56%, no p-value below 0.26). So this report states what positioning is
and what price did, cites that finding in a footer, and does not forecast.

Column positions below are the Legacy "Futures Only" long-format layout,
confirmed from a historical year's own header row (every extracted archive
carries one; the current year's live file does not, but shares the same
column order) and from CFTC's published variable list at
HistoricalViewable/cotvariableslegacy.html.

Public interface:
    load_category_rows(category_dir)                     -> {market: [(as_of, net, open_interest)]}
    merge_current_year_snapshot(snapshot, accumulator)    -- accumulate weekly snapshots
    build_report(by_market)                              -> markdown str
"""

import csv
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import contracts
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


# Top/bottom decile of a commodity's own positioning history. The label is
# descriptive only: study.py measured what actually follows these readings
# across 185 pooled historical episodes and found forward returns
# indistinguishable from chance (reversion hit rates 42-56%). So the report
# says what positioning IS, never what price will do.
_EXTREME_HIGH = 90
_EXTREME_LOW = 10
_RESEARCH_FILE = Path(__file__).resolve().parent / "research" / "forward_returns.json"
_MM_FLOW_FILE = Path(__file__).resolve().parent / "research" / "mm_flow.json"


def _ordinal(n: float) -> str:
    i = round(n)
    suffix = "th" if 11 <= i % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(i % 10, "th")
    return f"{i}{suffix}"


@dataclass
class Reading:
    name: str
    sector: str
    as_of: str
    net: int  # contracts, the figure people quote
    share: float  # net as a fraction of open interest, what the percentile ranks
    weeks: int  # depth of the stitched history behind the percentile
    pct: float
    change: int | None  # contracts vs prior report; None when no true prior week
    price_pct: float | None  # same-week price move, fraction


def _collect(by_market: MarketHistory) -> list[Reading]:
    """One Reading per commodity, using stitched rename chains.

    Two things make the percentile meaningful, and both were bugs first:

    - The history is stitched across CFTC renames (contracts.py), so it is
      ~1,900 weeks rather than a fragment. Unstitched, copper's history read
      as 205 weeks and every value scored as an all-time extreme.
    - The ranked quantity is net position as a share of open interest, not
      raw contracts. Open interest grew several-fold over 40 years, so a raw
      count ranks market growth as much as crowding.
    """
    out = []
    for name, commodity in contracts.COMMODITIES.items():
        series = contracts.stitch(by_market, commodity)
        shares = contracts.net_share(series)
        if len(series) < 2 or len(shares) < 2:
            continue

        as_of, net, _oi = series[-1]
        prior_date, prior_net, _prior_oi = series[-2]
        if shares[-1][0] != as_of:
            continue  # latest week had no usable open interest

        gap = (date.fromisoformat(as_of) - date.fromisoformat(prior_date)).days
        has_prior = gap <= _MAX_PLAUSIBLE_GAP_DAYS
        change = net - prior_net if has_prior else None

        price_pct = None
        if has_prior:
            closes = prices.weekly_closes(commodity.ticker)
            price_pct = prices.pct_change(closes, prior_date, as_of)

        values = [v for _, v in shares]
        share = shares[-1][1]
        pct = 100.0 * sum(1 for v in values if v <= share) / len(values)
        out.append(Reading(name, commodity.sector, as_of, net, share, len(values), pct, change, price_pct))
    return out


def _predictive_power_note() -> str:
    """One line stating the measured predictive power, so this never reads as a signal."""
    try:
        pooled = json.loads(_RESEARCH_FILE.read_text(encoding="utf-8"))["pooled"]
    except (OSError, ValueError, KeyError):
        return ""
    best = min(pooled, key=lambda p: p["p_value_quarter_clustered"])
    rates = [p["reversion_hit_rate"] for p in pooled]
    note = (
        f"Positioning extremes are context, not forecasts. Across {best['episodes']} historical "
        f"episodes in {best['clusters_quarters']} distinct quarters, forward returns after a "
        f"crowded reading were indistinguishable from chance (mean reversion hit rate "
        f"{min(rates)*100:.0f}-{max(rates)*100:.0f}%, best p={best['p_value_quarter_clustered']:.2f}). "
        f"See research/FINDINGS.md."
    )
    try:
        mm = json.loads(_MM_FLOW_FILE.read_text(encoding="utf-8"))
        note += (
            f" A follow-up with ~36x the statistical power (Managed Money weekly flow, ranked "
            f"across all commodities, {mm['weeks']:,} portfolio-weeks) found the same: rank "
            f"correlation with next week's returns {mm['ic']['flow']['mean']:+.4f} "
            f"(p={mm['ic']['flow']['p_value']:.2f}). See research/MM-FLOW.md."
        )
    except (OSError, ValueError, KeyError):
        pass
    return note


def _fmt(r: Reading) -> str:
    bits = [f"{_ordinal(r.pct)} pct of {r.weeks:,}wk", f"net {r.share*100:+.1f}% of open interest"]
    if r.change is not None:
        bits.append(f"{r.change:+,} contracts this wk")
    if r.price_pct is not None:
        bits.append(f"price {r.price_pct*100:+.1f}%")
    return f"**{r.name}**: {', '.join(bits)}"


def build_report(by_market: MarketHistory, title: str = "Legacy Report (Futures Only)") -> str:
    """Short, readable, descriptive. Detail table last, caveat at the bottom."""
    rows = _collect(by_market)
    if not rows:
        return "# COT Weekly\n\nNo commodities could be read from this week's file."

    rows.sort(key=lambda r: r.pct, reverse=True)
    as_of = max(r.as_of for r in rows)
    longs = [r for r in rows if r.pct >= _EXTREME_HIGH]
    shorts = [r for r in rows if r.pct <= _EXTREME_LOW]
    movers = sorted([r for r in rows if r.change is not None], key=lambda r: abs(r.change), reverse=True)

    lines = [f"# COT Weekly, report as of {as_of}", ""]

    headline = f"{len(rows)} commodities tracked. {len(longs) + len(shorts)} at a positioning extreme"
    if longs or shorts:
        headline += f" ({len(longs)} crowded long, {len(shorts)} crowded short)"
    if movers:
        headline += f". Biggest shift: {movers[0].name} {movers[0].change:+,} contracts"
    lines += [headline + ".", ""]

    # Until a second weekly snapshot accumulates, there is no prior week to
    # difference against and every change/price cell would read "n/a". Say
    # that once here instead of 24 times in the table.
    if not movers:
        lines += ["Week over week changes and price moves are not shown yet: only one weekly "
                  "snapshot has accumulated so far, so there is no prior report to compare "
                  "against. These fill in from the next run onward.", ""]

    if longs:
        lines += ["## Crowded long", ""] + [f"- {_fmt(r)}" for r in longs] + [""]
    if shorts:
        lines += ["## Crowded short", ""] + [f"- {_fmt(r)}" for r in reversed(shorts)] + [""]
    if movers:
        lines += ["## Biggest shifts this week", ""] + [f"- {_fmt(r)}" for r in movers[:5]] + [""]

    lines += ["## All commodities", "",
              "Percentile ranks net position as a share of open interest, so it is not distorted "
              "by decades of growth in market size.",
              "",
              "| Commodity | Sector | Net contracts | % of OI | vs prior wk | Percentile | History | Price (wk) |",
              "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        change = f"{r.change:+,}" if r.change is not None else "n/a"
        price = f"{r.price_pct*100:+.1f}%" if r.price_pct is not None else "n/a"
        lines.append(f"| {r.name} | {r.sector} | {r.net:+,} | {r.share*100:+.1f}% | {change} | "
                     f"{_ordinal(r.pct)} | {r.weeks:,}wk | {price} |")

    note = _predictive_power_note()
    if note:
        lines += ["", "---", "", note]
    return "\n".join(lines)
