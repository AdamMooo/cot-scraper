"""
Managed Money (Disaggregated, Futures Only): the measure-before-you-model step.

CLAUDE.md names this as the obvious next experiment after the legacy
non-commercial null: CFTC split the Disaggregated report out in 2009 precisely
so Managed Money could be separated from Producer/Merchant hedgers and Swap
Dealers, so it is a cleaner speculation proxy than the legacy "non-commercial"
bucket. This module does NOT run that test. It establishes what the data can
support first, because the last two attempts in this repo each died on a
problem that was cheap to measure up front and expensive to discover
afterwards.

What is verified here against the real files (not inferred from CFTC's docs):

  - Column indices. Managed Money long/short are at 13/14, NOT at the legacy
    report's 8/9 -- 8/9 in this file are Producer/Merchant, so reusing the
    legacy indices would silently have analysed commercial hedgers while
    labelling the output "Managed Money". Open interest is still 7 and the
    report date still 2. Checked in all 17 year-files: 191 columns each, same
    indices throughout.
  - The header label lies in 2010-2012. Those three files declare column 2 as
    Report_Date_as_MM_DD_YYYY, but every value in them is ISO YYYY-MM-DD, the
    same as 2013+ (which declares Report_Date_as_YYYY-MM-DD). Coding to the
    declared name would produce a parser that fails on data it should accept.
    Every row across all years is ISO; verified, not assumed.
  - History starts 2010-01-05, not 2009. The Disaggregated report itself began
    in 2009 but CFTC's per-year archive for this prefix starts at 2010, so
    this study has ~16.5 years and 836 weeks against the legacy study's ~26
    years and 1,348. Correct the "2009-present" figure wherever it appears.
  - The rename chains in contracts.py work unchanged on this report: all 24
    commodities stitch, 836 weeks each (RBOB 489, a later listing).

The two findings that should shape the eventual test:

1. LEVEL IS HOPELESS, FLOW IS NOT. Mean AR(1) of Managed Money net/OI is
   +0.968 as a level and +0.268 as a weekly change. Via the standard
   n*(1-rho)/(1+rho) heuristic that is ~13 independent observations per
   commodity for the level against ~475 for the flow -- roughly 36x the
   power, and an independent confirmation of the "3-12 episodes per
   commodity" arithmetic in CLAUDE.md, arrived at from a different direction.
   Differencing destroys the persistence that starved every level-based test
   in this repo. This is the reason to run the flow version rather than
   re-running the level version on a cleaner proxy.

2. FLOW'S BOOBY TRAP IS NOT THE VOLATILITY TILT, IT IS SHORT-TERM REVERSAL.
   Managed Money flow correlates +0.133 with the SAME week's return: specs
   add length in weeks price rose, which is the documented mechanism, not an
   artifact. Weekly commodity returns mean-revert, so a flow signal inherits
   short-term reversal for free and will look like a positioning discovery.
   Flow against the NEXT week's return is -0.030, negative in 18 of 24
   commodities (sign alone: two-sided binomial p = 0.023) -- the right
   direction for a price-pressure story, and far too small to accept on the
   evidence of a raw tercile spread.

So the eventual cross-sectional test needs a control the previous ones did
not: rank on flow ORTHOGONALISED against the same week's own return, and race
it head-to-head against pure short-term reversal (ranking on lagged return
alone). If reversal does as well, the CFTC column added nothing. Carry the
vol-tilt controls in as well -- IC and risk-parity legs reported alongside the
raw spread, per CLAUDE.md -- since a cleaner speculation proxy is if anything
more likely to correlate with volatility.

Run:  python managed_money.py
"""

import csv
import json
import statistics
from math import comb
from datetime import date
from pathlib import Path

import contracts
import prices

# Verified against all 17 year-files. Managed Money is 13/14 here; the legacy
# report's 8/9 are Producer/Merchant in this layout.
_MARKET_COL = 0
_DATE_COL = 2
_OPEN_INTEREST_COL = 7
_MM_LONG_COL = 13
_MM_SHORT_COL = 14

_CATEGORY_DIR = ".cot-cache/Disaggregated Report (Futures Only)"
_MIN_WEEKS = 100
_MIN_PAIRED_WEEKS = 60

REPO_ROOT = Path(__file__).resolve().parent
RESEARCH_DIR = REPO_ROOT / "research"


def load_managed_money(category_dir: Path) -> dict[str, list[tuple[str, int, int]]]:
    """{market: [(as_of, MM net, open interest)]}, same shape as analysis.load_category_rows.

    Header rows fall out through the int() conversion rather than a name
    check on purpose: the 2010-2012 files declare a different date column
    name than 2013+, so sniffing by header text would need a second case for
    no benefit.
    """
    by_market: dict[str, list[tuple[str, int, int]]] = {}
    for txt_file in sorted(category_dir.glob("*.txt")):
        with txt_file.open(encoding="utf-8", errors="replace", newline="") as f:
            for row in csv.reader(f):
                if len(row) <= _MM_SHORT_COL:
                    continue
                try:
                    open_interest = int(row[_OPEN_INTEREST_COL])
                    mm_long = int(row[_MM_LONG_COL])
                    mm_short = int(row[_MM_SHORT_COL])
                except ValueError:
                    continue
                market = row[_MARKET_COL].strip()
                as_of = row[_DATE_COL].strip()
                by_market.setdefault(market, []).append((as_of, mm_long - mm_short, open_interest))
    for history in by_market.values():
        history.sort(key=lambda r: r[0])
    return by_market


def _sign_test_p(negative: int, total: int) -> float:
    """Two-sided binomial p for a sign split, under a fair-coin null.

    The magnitude of a mean correlation this small is not persuasive on its
    own; whether the sign is consistent across independent commodities is a
    separate and cheaper question, so it gets its own number rather than a
    hand-computed figure in prose.
    """
    k = max(negative, total - negative)
    tail = sum(comb(total, i) for i in range(k, total + 1)) / 2 ** total
    return min(1.0, 2 * tail)


def _ar1(xs: list[float]) -> float | None:
    try:
        return statistics.correlation(xs[:-1], xs[1:])
    except statistics.StatisticsError:
        return None


def _effective_n(n: int, rho: float) -> float:
    """Independent-observation equivalent for an AR(1) series.

    n*(1-rho)/(1+rho) is the standard variance-inflation adjustment for the
    mean of an AR(1) process. At rho=0.97 it discards ~98% of the sample,
    which is the whole reason a decades-long positioning panel behaves like a
    few dozen observations.
    """
    return n * (1 - rho) / (1 + rho)


def run() -> dict:
    by_market = load_managed_money(REPO_ROOT / _CATEGORY_DIR)
    rows = []
    for name, commodity in contracts.COMMODITIES.items():
        series = contracts.net_share(contracts.stitch(by_market, commodity))
        if len(series) < _MIN_WEEKS:
            continue
        dates = [d for d, _ in series]
        level = [v for _, v in series]
        flow = [level[i + 1] - level[i] for i in range(len(level) - 1)]

        closes = prices.weekly_closes(commodity.ticker)
        step = ([prices.pct_change(closes, dates[i], dates[i + 1]) for i in range(len(dates) - 1)]
                if closes else [])

        paired_flow, same_week, next_week = [], [], []
        for i in range(len(flow) - 1):
            if i + 1 >= len(step) or step[i] is None or step[i + 1] is None:
                continue
            paired_flow.append(flow[i])
            same_week.append(step[i])
            next_week.append(step[i + 1])

        rho_level, rho_flow = _ar1(level), _ar1(flow)
        priced = len(paired_flow) >= _MIN_PAIRED_WEEKS
        rows.append({
            "commodity": name,
            "weeks": len(level),
            "first_week": dates[0],
            "last_week": dates[-1],
            "ar1_level": rho_level,
            "ar1_flow": rho_flow,
            "eff_n_level": _effective_n(len(level), rho_level) if rho_level is not None else None,
            "eff_n_flow": _effective_n(len(flow), rho_flow) if rho_flow is not None else None,
            "paired_weeks": len(paired_flow),
            "corr_flow_same_week_return": statistics.correlation(paired_flow, same_week) if priced else None,
            "corr_flow_next_week_return": statistics.correlation(paired_flow, next_week) if priced else None,
        })

    priced_rows = [r for r in rows if r["corr_flow_next_week_return"] is not None]
    lead = [r["corr_flow_next_week_return"] for r in priced_rows]

    return {
        "generated": date.today().isoformat(),
        "report": "Disaggregated Report (Futures Only), Managed Money",
        "columns_verified": {"date": _DATE_COL, "open_interest": _OPEN_INTEREST_COL,
                             "mm_long": _MM_LONG_COL, "mm_short": _MM_SHORT_COL},
        "markets_in_file": len(by_market),
        "commodities_covered": len(rows),
        "commodities_in_universe": len(contracts.COMMODITIES),
        "first_week": min(r["first_week"] for r in rows),
        "last_week": max(r["last_week"] for r in rows),
        "mean_ar1_level": statistics.fmean(r["ar1_level"] for r in rows),
        "mean_ar1_flow": statistics.fmean(r["ar1_flow"] for r in rows),
        "mean_eff_n_level": statistics.fmean(r["eff_n_level"] for r in rows),
        "mean_eff_n_flow": statistics.fmean(r["eff_n_flow"] for r in rows),
        "mean_corr_flow_same_week": statistics.fmean(r["corr_flow_same_week_return"] for r in priced_rows),
        "mean_corr_flow_next_week": statistics.fmean(lead),
        "next_week_negative_count": sum(1 for v in lead if v < 0),
        "next_week_priced_commodities": len(priced_rows),
        "next_week_sign_test_p": _sign_test_p(sum(1 for v in lead if v < 0), len(priced_rows)),
        "per_commodity": rows,
        "verdict": "test the FLOW, not the level; control for short-term reversal, not only the vol tilt",
    }


def _markdown(r: dict) -> str:
    lines = [
        "# Managed Money: what the data can support",
        "",
        f"Generated {r['generated']}. Report: {r['report']}.",
        "",
        "This is the measure-before-you-model step, not the test. Two previous attempts in "
        "this repo (`study.py`, `cross_section.py`) each died on a problem that was cheap to "
        "measure up front and expensive to find afterwards, so this file establishes what the "
        "panel can support before any signal is ranked.",
        "",
        "## Data verification",
        "",
        f"- Managed Money long/short are columns **{r['columns_verified']['mm_long']}/"
        f"{r['columns_verified']['mm_short']}**, not the legacy report's 8/9 -- 8/9 here are "
        "Producer/Merchant, so reusing the legacy indices would have analysed commercial "
        "hedgers under a Managed Money label. Same indices in all 17 year-files, 191 columns each.",
        "- The 2010-2012 files **declare** column 2 as `Report_Date_as_MM_DD_YYYY` while every "
        "value in them is ISO `YYYY-MM-DD`. The header label is wrong; the data is not. Coding "
        "to the declared name yields a parser that rejects valid data.",
        f"- History runs {r['first_week']} to {r['last_week']} -- it starts in 2010, not 2009, "
        "because CFTC's per-year archive for this prefix begins there even though the report "
        "itself launched in 2009.",
        f"- `contracts.py`'s rename chains work unchanged: {r['commodities_covered']} of "
        f"{r['commodities_in_universe']} commodities stitch, out of {r['markets_in_file']:,} "
        "markets in the file.",
        "",
        "## Finding 1: the level is hopeless, the flow is not",
        "",
        "| Variable | Mean AR(1) | Effective independent obs per commodity |",
        "|---|---|---|",
        f"| Net Managed Money / OI, level | {r['mean_ar1_level']:+.3f} | {r['mean_eff_n_level']:.0f} |",
        f"| Weekly change in that ratio (flow) | {r['mean_ar1_flow']:+.3f} | {r['mean_eff_n_flow']:.0f} |",
        "",
        "Effective n uses the standard AR(1) adjustment n(1-rho)/(1+rho). The level figure is "
        "an independent confirmation, from a different direction, of the \"3-12 independent "
        "episodes per commodity\" arithmetic that explains every null in this repo: at "
        f"rho={r['mean_ar1_level']:.2f}, 836 weeks of history are worth about "
        f"{r['mean_eff_n_level']:.0f} observations. Differencing destroys that persistence and "
        f"multiplies the effective sample by roughly "
        f"{r['mean_eff_n_flow'] / r['mean_eff_n_level']:.0f}x.",
        "",
        "**This is the argument for testing flow rather than re-running the level test on a "
        "cleaner proxy.** A better speculation measure does not fix a sample-size problem; "
        "differencing does.",
        "",
        "## Finding 2: flow's booby trap is short-term reversal, not the volatility tilt",
        "",
        "| Correlation | Mean across commodities |",
        "|---|---|",
        f"| Managed Money flow vs **same**-week return | {r['mean_corr_flow_same_week']:+.3f} |",
        f"| Managed Money flow vs **next**-week return | {r['mean_corr_flow_next_week']:+.3f} |",
        "",
        f"Flow is contemporaneously correlated with return at "
        f"{r['mean_corr_flow_same_week']:+.3f}: managed money adds length in weeks when price "
        "rose. That is the documented mechanism, not an artifact -- and it is exactly what "
        "makes a flow signal dangerous. Weekly commodity returns mean-revert, so any flow "
        "signal inherits short-term reversal for free and will present as a positioning "
        "discovery.",
        "",
        f"Against the next week's return the correlation is {r['mean_corr_flow_next_week']:+.3f}, "
        f"negative in {r['next_week_negative_count']} of {r['next_week_priced_commodities']} "
        f"commodities -- a fair coin gives a split that lopsided or worse "
        f"{r['next_week_sign_test_p']:.1%} of the time. The sign consistency is the more "
        "interesting half of that: the mean magnitude is far too small to accept on the "
        "evidence of a raw tercile spread, but a consistent sign across commodities that are "
        "not the same trade is what makes it worth testing properly at all.",
        "",
        "## What the actual test therefore has to include",
        "",
        "1. Rank on flow, cross-sectionally, with the one-week publication entry lag -- CFTC is "
        "as-of Tuesday, published Friday, and `cross_section.py` measured that shortcut as "
        "worth a quarter of its raw effect.",
        "2. **Flow orthogonalised against the same week's own return**, as a spec of its own. "
        "This is the control specific to flow, and neither previous study needed it.",
        "3. **A head-to-head against pure short-term reversal** -- rank on lagged return alone, "
        "no CFTC data involved. If reversal does as well, the positioning column added nothing, "
        "and that is the result.",
        "4. Information coefficient and risk-parity legs reported alongside the raw spread from "
        "the start, per CLAUDE.md. A cleaner speculation proxy is if anything more likely to "
        "correlate with volatility than the legacy bucket was.",
        "",
        "## Per commodity",
        "",
        "| Commodity | Weeks | AR(1) level | AR(1) flow | Eff. n level | Eff. n flow | Flow vs same-wk | Flow vs next-wk |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in r["per_commodity"]:
        same = f"{row['corr_flow_same_week_return']:+.3f}" if row["corr_flow_same_week_return"] is not None else "n/a"
        nxt = f"{row['corr_flow_next_week_return']:+.3f}" if row["corr_flow_next_week_return"] is not None else "n/a"
        lines.append(
            f"| {row['commodity']} | {row['weeks']:,} | {row['ar1_level']:+.3f} | "
            f"{row['ar1_flow']:+.3f} | {row['eff_n_level']:.0f} | {row['eff_n_flow']:.0f} | "
            f"{same} | {nxt} |")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    print("Probing the Managed Money panel ...")
    result = run()
    RESEARCH_DIR.mkdir(exist_ok=True)
    (RESEARCH_DIR / "MANAGED-MONEY.md").write_text(_markdown(result), encoding="utf-8")
    (RESEARCH_DIR / "managed_money.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print()
    print(f"{result['commodities_covered']} of {result['commodities_in_universe']} commodities, "
          f"{result['first_week']} to {result['last_week']}")
    print(f"mean AR(1)  level {result['mean_ar1_level']:+.3f} -> eff n {result['mean_eff_n_level']:.0f}"
          f"   flow {result['mean_ar1_flow']:+.3f} -> eff n {result['mean_eff_n_flow']:.0f}")
    print(f"flow vs same-week return {result['mean_corr_flow_same_week']:+.3f}   "
          f"vs next-week {result['mean_corr_flow_next_week']:+.3f} "
          f"({result['next_week_negative_count']}/{result['next_week_priced_commodities']} negative)")
    print(f"verdict: {result['verdict']}")
