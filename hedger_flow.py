"""
Commercial (hedger) flow vs pure reversal: the KRT liquidity premium under a
realistic publication lag.

Why this test exists when mm_flow.py already nulled Managed Money flow.
research/APPLICATIONS.md records the one positioning result that survives
post-2004 replication: Kang, Rouwenhorst & Tang (JF 2020) find a short-horizon
liquidity-provision premium in COMMERCIAL position changes -- hedgers get paid
for accommodating momentum-chasing speculators -- and Marechal (JFM 2023)
finds that premium (unlike the smoothed-level insurance premium) robust after
financialization. Two things distinguish it from what mm_flow tested:

  - The variable is commercial flow, not Managed Money flow, and in the
    legacy report commercial net is not the mirror of non-commercial net
    (nonreportables absorb the difference).
  - KRT's effect is front-loaded in days 1-10 after the as-of Tuesday, and
    their inference is regression-with-controls on unlagged formation. This
    repo's harness asks the sharper practical question: does anything
    survive entering AFTER publication (1-week lag) and a head-to-head
    against ranking on the formation-week return alone?

Sign conventions. Hedgers are contrarians (they buy what just fell), so the
KRT effect is: HIGH hedger flow -> HIGHER next-week return. The portfolio is
long the HIGHEST-hedger-flow tercile, short the lowest (implemented by
feeding the inverted percentile to cross_section._spreads, which longs the
lowest signal), and the effect prints as a POSITIVE spread and a POSITIVE IC
on the raw hedger-flow percentile -- the opposite IC sign convention from
mm_flow.py, stated here so nobody "fixes" it.

Sample note: legacy history starts 1986 and the crowding warmup is spent by
1991, but prices exist only from ~2000 and the formation-return percentile
needs its own 260-week warmup on the priced grid, so the panel effectively
starts ~2005. That is still ~2x mm_flow's weeks and includes 2005-2014,
most of KRT's own sample.

Run:  python hedger_flow.py
"""

import csv
import json
import random
import statistics
from datetime import date
from pathlib import Path

import contracts
import cross_section as xs
import mm_flow
import prices
import study

# Verified against the 1986 and 2025 year-files' own header rows on
# 2026-08-27: Commercial Positions-Long/Short (All) are columns 11/12 in
# both. 8/9 (which analysis.py reads) are Noncommercial.
_MARKET_COL = 0
_DATE_COL = 2
_OPEN_INTEREST_COL = 7
_COMM_LONG_COL = 11
_COMM_SHORT_COL = 12

_CATEGORY_DIR = ".cot-cache/Legacy Report (Futures Only)"
_SEED = 20260827

REPO_ROOT = Path(__file__).resolve().parent
RESEARCH_DIR = REPO_ROOT / "research"


def load_commercial(category_dir: Path) -> dict[str, list[tuple[str, int, int]]]:
    """{market: [(as_of, commercial net, open interest)]}."""
    by_market: dict[str, list[tuple[str, int, int]]] = {}
    for txt_file in sorted(category_dir.glob("*.txt")):
        with txt_file.open(encoding="utf-8", errors="replace", newline="") as f:
            for row in csv.reader(f):
                if len(row) <= _COMM_SHORT_COL:
                    continue
                try:
                    open_interest = int(row[_OPEN_INTEREST_COL])
                    c_long = int(row[_COMM_LONG_COL])
                    c_short = int(row[_COMM_SHORT_COL])
                except ValueError:
                    continue
                market = row[_MARKET_COL].strip()
                as_of = row[_DATE_COL].strip()
                by_market.setdefault(market, []).append((as_of, c_long - c_short, open_interest))
    for history in by_market.values():
        history.sort(key=lambda r: r[0])
    return by_market


def _panel():
    """Same construction as mm_flow._panel, on commercial flow.

    hf_sig  -- within-commodity point-in-time percentile of the weekly change
               in commercial net/OI (high = heavy hedger buying)
    rev_sig -- percentile of the formation week's price return
    """
    by_market = load_commercial(REPO_ROOT / _CATEGORY_DIR)

    hf_sig: dict[str, dict[str, float]] = {}
    rev_sig: dict[str, dict[str, float]] = {}
    forward: dict[str, dict[str, float]] = {}
    vol: dict[str, dict[str, float]] = {}

    for name, commodity in contracts.COMMODITIES.items():
        shares = contracts.net_share(contracts.stitch(by_market, commodity))
        if len(shares) < study._WARMUP_WEEKS + 20:
            continue
        dates = [d for d, _ in shares]
        level = [v for _, v in shares]
        closes = prices.weekly_closes(commodity.ticker)
        if not closes:
            continue
        step = [prices.pct_change(closes, dates[i], dates[i + 1]) for i in range(len(dates) - 1)]

        flow = [None] + [level[i] - level[i - 1] for i in range(1, len(level))]
        form = [None] + [step[i - 1] for i in range(1, len(dates))]
        flow_pct = mm_flow._pit_pct_sparse(flow)
        form_pct = mm_flow._pit_pct_sparse(form)

        for i, day in enumerate(dates):
            entry = i + mm_flow._ENTRY_LAG_WEEKS
            exit_ = entry + mm_flow._HOLD_WEEKS
            if flow_pct[i] is None or form_pct[i] is None or exit_ >= len(dates):
                continue
            ret = prices.pct_change(closes, dates[entry], dates[exit_])
            if ret is None:
                continue
            hf_sig.setdefault(day, {})[name] = flow_pct[i]
            rev_sig.setdefault(day, {})[name] = form_pct[i]
            forward.setdefault(day, {})[name] = ret

            hist = [r for r in step[max(0, entry - mm_flow._VOL_WINDOW):entry] if r is not None]
            if len(hist) >= mm_flow._MIN_VOL_OBS:
                sd = statistics.stdev(hist)
                if sd > 0:
                    vol.setdefault(day, {})[name] = sd

    usable = sorted(d for d in hf_sig if len(hf_sig[d]) >= mm_flow._MIN_COMMODITIES)
    return usable, hf_sig, rev_sig, forward, vol


def _invert(sig: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    """xs._spreads longs the LOWEST signal; the KRT portfolio is long the
    HIGHEST hedger flow, so the spread machinery gets the inverted percentile."""
    return {d: {n: 100.0 - v for n, v in m.items()} for d, m in sig.items()}


def run() -> dict:
    rng = random.Random(_SEED)
    dates, hf_sig, rev_sig, forward, vol = _panel()
    if len(dates) < 100:
        raise RuntimeError(f"only {len(dates)} usable weeks; cannot run the test")

    orth_sig = mm_flow.orthogonalise(dates, hf_sig, rev_sig)
    odates = sorted(orth_sig)
    inv_hf, inv_orth = _invert(hf_sig), _invert(orth_sig)

    hf_spread = xs._spreads(dates, inv_hf, forward)
    rev_spread = xs._spreads(dates, rev_sig, forward)
    orth_spread = xs._spreads(odates, inv_orth, forward)

    hf_stats = mm_flow._stats(hf_spread, rng)
    rev_stats = mm_flow._stats(rev_spread, rng)
    orth_stats = mm_flow._stats(orth_spread, rng)
    mean, lo_ci, hi_ci = xs._block_bootstrap_ci(hf_spread, rng)

    # ICs on the RAW percentiles: positive = KRT effect for hedger flow,
    # negative = reversal effect for the formation-return signal.
    hf_ic = xs._ic_series(dates, hf_sig, forward)
    rev_ic = xs._ic_series(dates, rev_sig, forward)
    orth_ic = xs._ic_series(odates, orth_sig, forward)
    ic_rows = {
        "hedger_flow": {"mean": statistics.fmean(hf_ic), "p_value": xs._p_two_sided(hf_ic, rng)},
        "reversal": {"mean": statistics.fmean(rev_ic), "p_value": xs._p_two_sided(rev_ic, rng)},
        "orthogonalised_hedger_flow": {"mean": statistics.fmean(orth_ic),
                                       "p_value": xs._p_two_sided(orth_ic, rng)},
    }

    vdates, vsignal = xs._vol_subpanel(dates, inv_hf, vol)
    target = statistics.fmean([v for d in vdates for v in vol[d].values()])
    rp_stats = mm_flow._stats(xs._vol_scaled_spreads(vdates, vsignal, forward, vol, target), rng)
    ew_stats = mm_flow._stats(xs._spreads(vdates, vsignal, forward), rng)
    gap = xs._leg_vol_gap(vdates, vsignal, vol)

    tail = xs._tail_contribution(hf_spread)
    overlap = statistics.correlation(hf_spread, rev_spread)
    jackknife = mm_flow._jackknife(dates, inv_hf, forward, rng)

    hf_lives = hf_stats["p_value"] < 0.05 or ic_rows["hedger_flow"]["p_value"] < 0.05
    orth_lives = (orth_stats["p_value"] < 0.05
                  or ic_rows["orthogonalised_hedger_flow"]["p_value"] < 0.05)
    if orth_lives:
        verdict = ("hedger flow carries information beyond the formation week's own return -- "
                   "the KRT liquidity premium survives a realistic publication lag here")
    elif hf_lives:
        verdict = ("hedger flow's edge is inherited short-term reversal; orthogonalised "
                   "against the formation-week return it dies")
    else:
        verdict = ("no detectable information in commercial flow after a 1-week publication "
                   "lag -- KRT's liquidity premium does not survive realistic entry in this universe")

    return {
        "generated": date.today().isoformat(),
        "question": "Does COMMERCIAL (hedger) flow rank next week's relative returns after a "
                    "realistic publication lag, beyond what the formation week's return tells you?",
        "portfolio": "equal-weighted terciles, long highest hedger flow, short lowest, "
                     "1-week entry lag, 1-week hold",
        "weeks": len(dates),
        "first_week": dates[0],
        "last_week": dates[-1],
        "avg_commodities_per_week": statistics.fmean([len(hf_sig[d]) for d in dates]),
        "hedger_flow": hf_stats,
        "hf_ci95_low": lo_ci,
        "hf_ci95_high": hi_ci,
        "reversal": rev_stats,
        "orthogonalised_hedger_flow": orth_stats,
        "ic": ic_rows,
        "risk_parity": rp_stats,
        "equal_weight_matched": ew_stats,
        "vol_gap_mean": statistics.fmean(gap),
        "vol_gap_p_value": xs._p_two_sided(gap, rng),
        "hf_reversal_spread_correlation": overlap,
        **tail,
        "jackknife": jackknife,
        "jackknife_specs_above_05": sum(1 for r in jackknife if r["p_value"] >= 0.05),
        "verdict": verdict,
        "caveat": "price-only returns, excludes roll yield and costs; measures information, "
                  "not tradability",
    }


def _markdown(r: dict) -> str:
    row = mm_flow._row
    return "\n".join([
        "# Commercial (hedger) flow: the KRT liquidity premium under a realistic lag",
        "",
        f"Generated {r['generated']}.",
        "",
        f"{r['question']} Portfolio: {r['portfolio']}. Sign convention: hedgers are "
        "contrarians, so the KRT effect prints as a POSITIVE spread and a POSITIVE IC "
        "(opposite to mm_flow's convention).",
        "",
        f"**{r['weeks']:,} portfolio-weeks**, {r['first_week']} to {r['last_week']}, "
        f"averaging {r['avg_commodities_per_week']:.1f} commodities per week. The panel "
        "starts ~2005 (price history from 2000 plus the formation-return percentile's "
        "260-week warmup), which still overlaps most of KRT's own 1994-2014 sample.",
        "",
        "## Head-to-head",
        "",
        "| Signal | Weeks | Mean weekly | Annualised | p |",
        "|---|---|---|---|---|",
        row("Commercial (hedger) flow", r["hedger_flow"]),
        row("Pure short-term reversal (no CFTC data)", r["reversal"]),
        row("Hedger flow orthogonalised vs formation-week return", r["orthogonalised_hedger_flow"]),
        "",
        f"The hedger-flow and reversal spread series correlate at "
        f"{r['hf_reversal_spread_correlation']:+.2f} week to week. Hedgers buy what just "
        "fell, so unlike Managed Money flow (mm_flow.py, +0.05), meaningful overlap is "
        "expected here -- the orthogonalised row is what separates 'hedger flow is "
        "reversal in disguise' from 'hedger flow adds something'.",
        "",
        "## Rank information coefficient",
        "",
        "| Signal | Mean IC | Effect sign | p |",
        "|---|---|---|---|",
        f"| Hedger flow | {r['ic']['hedger_flow']['mean']:+.4f} | + | "
        f"{r['ic']['hedger_flow']['p_value']:.3f} |",
        f"| Reversal | {r['ic']['reversal']['mean']:+.4f} | - | "
        f"{r['ic']['reversal']['p_value']:.3f} |",
        f"| Orthogonalised hedger flow | {r['ic']['orthogonalised_hedger_flow']['mean']:+.4f} | + | "
        f"{r['ic']['orthogonalised_hedger_flow']['p_value']:.3f} |",
        "",
        "## Volatility tilt check (hedger-flow portfolio)",
        "",
        f"Leg vol gap {r['vol_gap_mean']*100:+.2f}pp/wk (p={r['vol_gap_p_value']:.3f}). "
        f"Risk-parity legs {r['risk_parity']['annualised']*100:+.1f}%/yr "
        f"(p={r['risk_parity']['p_value']:.3f}) vs matched equal-weight "
        f"{r['equal_weight_matched']['annualised']*100:+.1f}%/yr "
        f"(p={r['equal_weight_matched']['p_value']:.3f}).",
        "",
        "## Tail contribution",
        "",
        f"The {r['tail_weeks']} largest weeks by magnitude net {r['tail_net']:+.1%} "
        f"against a series total of {r['series_total']:+.1%}.",
        "",
        "## Jackknife (baseline hedger-flow spread)",
        "",
        "| Dropped | Weeks | Mean weekly | Annualised | p |",
        "|---|---|---|---|---|",
        *[f"| {s['dropped']} | {s['weeks']:,} | {s['mean_weekly_spread']*100:+.3f}% | "
          f"{s['annualised']*100:+.1f}% | {s['p_value']:.3f} |" for s in r["jackknife"]],
        "",
        "## Verdict",
        "",
        f"**{r['verdict']}.**",
        "",
        f"Caveat: {r['caveat']}.",
        "",
    ])


if __name__ == "__main__":
    print("Running commercial (hedger) flow test ...")
    result = run()
    RESEARCH_DIR.mkdir(exist_ok=True)
    (RESEARCH_DIR / "HEDGER-FLOW.md").write_text(_markdown(result), encoding="utf-8")
    (RESEARCH_DIR / "hedger_flow.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\n{result['weeks']:,} portfolio-weeks, {result['first_week']} to {result['last_week']}")
    print(f"hedger flow {result['hedger_flow']['annualised']*100:+.1f}%/yr  "
          f"p={result['hedger_flow']['p_value']:.3f}   "
          f"IC {result['ic']['hedger_flow']['mean']:+.4f} p={result['ic']['hedger_flow']['p_value']:.3f}")
    print(f"reversal    {result['reversal']['annualised']*100:+.1f}%/yr  "
          f"p={result['reversal']['p_value']:.3f}   "
          f"IC {result['ic']['reversal']['mean']:+.4f} p={result['ic']['reversal']['p_value']:.3f}")
    print(f"orth hf     {result['orthogonalised_hedger_flow']['annualised']*100:+.1f}%/yr  "
          f"p={result['orthogonalised_hedger_flow']['p_value']:.3f}   "
          f"IC {result['ic']['orthogonalised_hedger_flow']['mean']:+.4f} "
          f"p={result['ic']['orthogonalised_hedger_flow']['p_value']:.3f}")
    print(f"spread correlation hedger flow vs reversal "
          f"{result['hf_reversal_spread_correlation']:+.2f}")
    print(f"verdict: {result['verdict']}")
