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
from datetime import date, timedelta
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
    trend_13w: float | None  # 13-week price change, the trend perspective
    range_52w: float | None  # latest close's position in its 52-week range, 0..1
    oi_change_pct: float | None  # open interest vs prior report, fraction
    oi_collapsing: bool  # this week's OI change in the bottom decile of its own history


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

        as_of, net, oi = series[-1]
        prior_date, prior_net, prior_oi = series[-2]
        if shares[-1][0] != as_of:
            continue  # latest week had no usable open interest

        gap = (date.fromisoformat(as_of) - date.fromisoformat(prior_date)).days
        has_prior = gap <= _MAX_PLAUSIBLE_GAP_DAYS
        change = net - prior_net if has_prior else None

        closes = prices.weekly_closes(commodity.ticker)
        price_pct = prices.pct_change(closes, prior_date, as_of) if has_prior else None
        trend_13w = prices.pct_change(closes, _days_back(as_of, 91), as_of)
        range_52w = _range_position(closes, as_of)

        # OI collapse is flagged against the market's OWN distribution of
        # weekly OI changes rather than a fixed threshold -- what counts as a
        # sharp contraction in milk is routine in crude. The fragility read
        # (one-sided positioning + shrinking open interest) is the shape the
        # squeeze episode record points at; see research/APPLICATIONS.md.
        oi_change_pct = None
        oi_collapsing = False
        if has_prior and prior_oi:
            oi_change_pct = (oi - prior_oi) / prior_oi
            oi_moves = sorted((b[2] - a[2]) / a[2] for a, b in zip(series, series[1:]) if a[2])
            if len(oi_moves) >= 50:
                oi_collapsing = oi_change_pct <= oi_moves[len(oi_moves) // 10]

        values = [v for _, v in shares]
        share = shares[-1][1]
        pct = 100.0 * sum(1 for v in values if v <= share) / len(values)
        out.append(Reading(name, commodity.sector, as_of, net, share, len(values), pct, change,
                           price_pct, trend_13w, range_52w, oi_change_pct, oi_collapsing))
    return out


def _days_back(iso: str, days: int) -> str:
    return (date.fromisoformat(iso) - timedelta(days=days)).isoformat()


# Needs most of a year of weekly bars, or "position in the 52-week range" is
# really position in whatever stub of history exists and reads as an extreme.
_MIN_RANGE_WEEKS = 40


def _range_position(closes: list[tuple[str, float]], as_of: str) -> float | None:
    """Where the latest close sits in its trailing 52-week range, 0..1."""
    last = prices.close_asof(closes, as_of)
    if last is None:
        return None
    floor = _days_back(as_of, 365)
    window = [c for d, c in closes if floor < d <= as_of]
    if len(window) < _MIN_RANGE_WEEKS:
        return None
    lo, hi = min(window), max(window)
    if hi == lo:
        return None
    return (last - lo) / (hi - lo)


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


def _flow_read(r: Reading) -> str | None:
    """What this week's move was made of, in plain English. Descriptive only.

    Flow-with-price is the documented spec pattern (they chase: measured
    +0.133 same-week flow/return correlation, research/MM-FLOW.md); flow
    AGAINST price says the price move was driven by someone else's book --
    commercial hedging, physical demand. Neither reading forecasts anything;
    it attributes what already happened, which is the use the literature and
    practitioner record actually support (research/APPLICATIONS.md).
    """
    if r.change is None or r.price_pct is None or r.change == 0 or abs(r.price_pct) < 0.001:
        return None
    if r.change > 0:
        return "specs bought the rally" if r.price_pct > 0 else "a drop against spec buying"
    return "specs sold the break" if r.price_pct < 0 else "a rally against spec selling"


# Below this 13-week move, calling a market "rising" or "falling" is noise.
_FLAT_TREND = 0.02

# "Near" the edge of the 52-week range, mirroring the positioning deciles.
_RANGE_HIGH = 0.90
_RANGE_LOW = 0.10


def _trend_read(r: Reading) -> str | None:
    """Pair the positioning extreme with the multi-week price trend: the same
    market seen from both sides. Says whether the crowd sits with or against
    what price has already done -- never what either will do next."""
    if r.trend_13w is None or not (r.pct >= _EXTREME_HIGH or r.pct <= _EXTREME_LOW):
        return None
    long_side = r.pct >= _EXTREME_HIGH
    rng = f", {r.range_52w*100:.0f}% of its 52wk range" if r.range_52w is not None else ""
    px = f"price {r.trend_13w*100:+.1f}% over 13wk{rng}"
    if abs(r.trend_13w) < _FLAT_TREND:
        return f"{px} -- a one-sided crowd in a sideways market"
    if (r.trend_13w > 0) == long_side:
        return f"{px} -- the crowd is positioned with the trend"
    against = "long into a falling market" if long_side else "short into a rising market"
    return f"{px} -- positioning and trend diverge: specs are crowded {against}"


def _fmt(r: Reading, with_trend: bool = False) -> str:
    bits = [f"{_ordinal(r.pct)} pct of {r.weeks:,}wk", f"net {r.share*100:+.1f}% of open interest"]
    if r.change is not None:
        bits.append(f"{r.change:+,} contracts this wk")
    if r.price_pct is not None:
        bits.append(f"price {r.price_pct*100:+.1f}%")
    read = _flow_read(r)
    if read:
        bits.append(read)
    line = f"**{r.name}**: {', '.join(bits)}"
    trend = _trend_read(r) if with_trend else None
    if trend:
        line += f". {trend[0].upper()}{trend[1:]}"
    return line


# The scenario mechanics of an extreme: which way the accelerant points.
# Deliberately conditional, never directional -- measured forward returns
# after extremes are a coin flip (research/FINDINGS.md), but WHO can act next
# is arithmetic: a crowd this large exiting is mechanical flow in one
# scenario, and exhausted buying power in the other. Fuel asymmetry, not a
# forecast; stated once per section rather than per market.
_LONG_MECHANICS = ("At these levels the accelerant points down: a break lower would meet "
                   "mechanical selling from exiting spec longs, while further upside needs "
                   "new buyers -- specs have little room left to add. Which scenario arrives "
                   "is the coin flip the footer describes; its speed is not.")
_SHORT_MECHANICS = ("At these levels the accelerant points up: a bounce can be amplified by "
                    "spec short-covering, while further downside needs new sellers -- specs "
                    "have little room left to add. Which scenario arrives is the coin flip "
                    "the footer describes; its speed is not.")


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
        with_trend = sum(1 for r in longs if r.trend_13w is not None and r.trend_13w >= _FLAT_TREND) \
            + sum(1 for r in shorts if r.trend_13w is not None and r.trend_13w <= -_FLAT_TREND)
        against = sum(1 for r in longs if r.trend_13w is not None and r.trend_13w <= -_FLAT_TREND) \
            + sum(1 for r in shorts if r.trend_13w is not None and r.trend_13w >= _FLAT_TREND)
        if with_trend or against:
            headline += (f"; of those, {with_trend} sit with the 13-week price trend "
                         f"and {against} against it")
    if movers:
        m = movers[0]
        headline += f". Biggest shift: {m.name} {m.change:+,} contracts"
        if m.price_pct is not None:
            headline += f" into a {m.price_pct*100:+.1f}% week"
            read = _flow_read(m)
            if read:
                headline += f" -- {read}"
    lines += [headline + ".", ""]

    # Until a second weekly snapshot accumulates, there is no prior week to
    # difference against and every change/price cell would read "n/a". Say
    # that once here instead of 24 times in the table.
    if not movers:
        lines += ["Week-over-week comparisons (position change, same-week price, OI change) are "
                  "not shown yet: only one weekly snapshot has accumulated so far, so there is "
                  "no prior report to difference against. They fill in from the next run onward; "
                  "the 13-week trend and 52-week range columns do not need a prior report and "
                  "are already live.", ""]

    if longs:
        lines += ["## Crowded long", "", _LONG_MECHANICS, ""] \
            + [f"- {_fmt(r, with_trend=True)}" for r in longs] + [""]
    if shorts:
        lines += ["## Crowded short", "", _SHORT_MECHANICS, ""] \
            + [f"- {_fmt(r, with_trend=True)}" for r in reversed(shorts)] + [""]

    # The squeeze episode record (research/APPLICATIONS.md: nickel 2022,
    # cocoa 2024) says the dangerous shape is one-sided positioning while the
    # market itself shrinks -- crowded exits, vanishing liquidity. Flagged
    # only when both halves hold; still context, not a forecast.
    fragile = [r for r in rows
               if (r.pct >= _EXTREME_HIGH or r.pct <= _EXTREME_LOW) and r.oi_collapsing]
    if fragile:
        lines += ["## Fragility watch", "",
                  "Positioning at an extreme while open interest contracts sharply -- the crowd "
                  "is one-sided and the market it would have to exit through is shrinking.", ""]
        for r in fragile:
            side = "long" if r.pct >= _EXTREME_HIGH else "short"
            lines.append(f"- **{r.name}**: crowded {side} ({_ordinal(r.pct)} pct) with open "
                         f"interest {r.oi_change_pct*100:+.1f}% this week, a bottom-decile "
                         f"contraction for this market")
        lines.append("")

    # The same markets viewed price-first: the crowded sections ask "where is
    # positioning stretched, and what is price doing there" -- this asks
    # "where is PRICE stretched, and how are specs positioned there". Near a
    # 52-week boundary the two views either tell one story or visibly
    # disagree, and that pairing is the report's whole point.
    at_highs = sorted([r for r in rows if r.range_52w is not None and r.range_52w >= _RANGE_HIGH],
                      key=lambda r: r.range_52w, reverse=True)
    at_lows = sorted([r for r in rows if r.range_52w is not None and r.range_52w <= _RANGE_LOW],
                     key=lambda r: r.range_52w)
    if at_highs or at_lows:
        lines += ["## Price trend snapshot", "",
                  "Markets trading near the edge of their own 52-week range, with speculative "
                  "positioning alongside -- the price-first view of the same pairing the "
                  "sections above read positioning-first.", ""]
        for label, group in (("near 52wk highs", at_highs), ("near 52wk lows", at_lows)):
            for r in group:
                trend = f", {r.trend_13w*100:+.1f}% over 13wk" if r.trend_13w is not None else ""
                lines.append(f"- **{r.name}** ({label}): {r.range_52w*100:.0f}% of its 52wk "
                             f"range{trend}; specs at the {_ordinal(r.pct)} percentile of "
                             f"positioning history")
        lines.append("")

    if movers:
        lines += ["## Biggest shifts this week", ""] + [f"- {_fmt(r)}" for r in movers[:5]] + [""]

    lines += ["## All commodities", "",
              "Percentile ranks net position as a share of open interest, so it is not distorted "
              "by decades of growth in market size. The last three columns are the price "
              "perspective: this week's move, the 13-week trend, and where the latest close sits "
              "in its 52-week range.",
              "",
              "| Commodity | Sector | Net contracts | % of OI | vs prior wk | OI (wk) | Percentile | History | Price (wk) | Price (13wk) | 52wk range |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        change = f"{r.change:+,}" if r.change is not None else "n/a"
        oi_move = f"{r.oi_change_pct*100:+.1f}%" if r.oi_change_pct is not None else "n/a"
        price = f"{r.price_pct*100:+.1f}%" if r.price_pct is not None else "n/a"
        trend = f"{r.trend_13w*100:+.1f}%" if r.trend_13w is not None else "n/a"
        rng = f"{r.range_52w*100:.0f}%" if r.range_52w is not None else "n/a"
        lines.append(f"| {r.name} | {r.sector} | {r.net:+,} | {r.share*100:+.1f}% | {change} | "
                     f"{oi_move} | {_ordinal(r.pct)} | {r.weeks:,}wk | {price} | {trend} | {rng} |")

    note = _predictive_power_note()
    if note:
        lines += ["", "---", "", note]
    return "\n".join(lines)
