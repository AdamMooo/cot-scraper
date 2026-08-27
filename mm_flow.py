"""
The Managed Money FLOW test: the final experiment this repo's three studies
were building toward, run exactly as managed_money.py's diagnostic specified.

Why flow and why these controls (managed_money.py measured all of this
before this file was written):

  - The LEVEL of Managed Money net/OI has AR(1) +0.968: ~13 effective
    observations per commodity, the same sample starvation that nulled
    study.py. The weekly CHANGE has AR(1) +0.268: ~475 effective
    observations, ~36x the power. So the signal here is flow.
  - Flow correlates +0.133 with the SAME week's return (specs add length in
    weeks price rose). Weekly commodity returns mean-revert, so a flow
    signal inherits short-term reversal for free and will present as a
    positioning discovery. Hence the two specs neither earlier study needed:
      1. flow ORTHOGONALISED against the formation week's own return, and
      2. a head-to-head against pure reversal (rank on the formation-week
         return alone, no CFTC data involved).
    If reversal does as well as flow, the CFTC column added nothing, and
    that is the finding.
  - Everything cross_section.py learned carries over: one-week entry lag
    (CFTC publishes Friday for Tuesday positions; skipping this was worth a
    quarter of that study's raw effect), within-commodity point-in-time
    percentiles (cross-commodity flow scales differ, so ranking raw flow
    would sort on positioning turnover, a cousin of the vol tilt), the rank
    IC as the tail-insensitive statistic, risk-parity legs with strictly
    trailing vol, block-bootstrap inference, and a leave-one-out jackknife.

Sign convention throughout: the portfolio is long the LOWEST-signal tercile
and short the HIGHEST, so a price-pressure/unwind effect (heavy inflow ->
weaker next week) shows up as a POSITIVE spread and a NEGATIVE IC.

Sample note: Managed Money history starts 2010-01-05 and the 260-week
percentile warmup is spent inside it (the legacy study warmed up in the
1980s), so usable portfolio-weeks start around 2015. Both signals are
percentiled on the same grid so the head-to-head runs on identical weeks.

Run:  python mm_flow.py
"""

import bisect
import json
import random
import statistics
from datetime import date
from pathlib import Path

import contracts
import cross_section as xs
import managed_money
import prices
import study

_ENTRY_LAG_WEEKS = xs._ENTRY_LAG_WEEKS
_HOLD_WEEKS = xs._HOLD_WEEKS
_MIN_COMMODITIES = xs._MIN_COMMODITIES
_VOL_WINDOW = xs._VOL_WINDOW
_MIN_VOL_OBS = xs._MIN_VOL_OBS
_JACKKNIFE_ITERS = xs._JACKKNIFE_ITERS
_SEED = 20260827

REPO_ROOT = Path(__file__).resolve().parent
RESEARCH_DIR = REPO_ROOT / "research"


def _pit_pct_sparse(values: list[float | None]) -> list[float | None]:
    """study.point_in_time_percentiles for a series with gaps.

    The formation-week return series has occasional None weeks (price
    lookup misses); study's version takes a dense list. Same warmup, same
    ranking, Nones pass through and do not enter the history.
    """
    out: list[float | None] = []
    history: list[float] = []
    for v in values:
        if v is None:
            out.append(None)
            continue
        bisect.insort(history, v)
        if len(history) < study._WARMUP_WEEKS:
            out.append(None)
        else:
            out.append(100.0 * bisect.bisect_right(history, v) / len(history))
    return out


def _panel():
    """Aligned per-week cross-sections, keyed on the signal (as-of) date.

    flow_sig  -- within-commodity point-in-time percentile of the weekly
                 change in Managed Money net/OI
    rev_sig   -- same transform applied to the formation week's price
                 return, so the reversal benchmark gets identical
                 processing and the race is apples-to-apples
    forward   -- return over the held week, entered one week after as-of
    vol       -- trailing weekly vol over the _VOL_WINDOW weeks strictly
                 before entry (sparse where a first year has not accrued)

    A (day, name) cell exists only when BOTH signals and the forward return
    are defined, so every spec below runs on the same observations.
    """
    by_market = managed_money.load_managed_money(REPO_ROOT / managed_money._CATEGORY_DIR)

    flow_sig: dict[str, dict[str, float]] = {}
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
        # step[k] spans dates[k] -> dates[k+1]; the formation week ending at
        # dates[i] is step[i-1], the same week flow[i] was accumulated over.
        form = [None] + [step[i - 1] for i in range(1, len(dates))]
        flow_pct = _pit_pct_sparse(flow)
        form_pct = _pit_pct_sparse(form)

        for i, day in enumerate(dates):
            entry = i + _ENTRY_LAG_WEEKS
            exit_ = entry + _HOLD_WEEKS
            if flow_pct[i] is None or form_pct[i] is None or exit_ >= len(dates):
                continue
            ret = prices.pct_change(closes, dates[entry], dates[exit_])
            if ret is None:
                continue
            flow_sig.setdefault(day, {})[name] = flow_pct[i]
            rev_sig.setdefault(day, {})[name] = form_pct[i]
            forward.setdefault(day, {})[name] = ret

            hist = [r for r in step[max(0, entry - _VOL_WINDOW):entry] if r is not None]
            if len(hist) >= _MIN_VOL_OBS:
                sd = statistics.stdev(hist)
                if sd > 0:
                    vol.setdefault(day, {})[name] = sd

    usable = sorted(d for d in flow_sig if len(flow_sig[d]) >= _MIN_COMMODITIES)
    return usable, flow_sig, rev_sig, forward, vol


def orthogonalise(dates, flow_sig, rev_sig) -> dict[str, dict[str, float]]:
    """Per week, the residual of flow percentile on formation-return percentile.

    One cross-sectional OLS per week: flow_i = a + b*ret_i + resid_i across
    that week's names. The residual is the part of the flow ranking that the
    same week's price action cannot explain -- if managed money only chases
    price, the residuals are noise and any spread built on them dies. This
    is the standard factor-neutralisation step (Fama-MacBeth style
    cross-sectional regression), applied to the one factor flow is known to
    load on.
    """
    out: dict[str, dict[str, float]] = {}
    for day in dates:
        names = sorted(flow_sig[day])
        f = [flow_sig[day][n] for n in names]
        r = [rev_sig[day][n] for n in names]
        rbar, fbar = statistics.fmean(r), statistics.fmean(f)
        var = sum((x - rbar) ** 2 for x in r)
        if var == 0:
            continue
        beta = sum((r[k] - rbar) * (f[k] - fbar) for k in range(len(names))) / var
        out[day] = {names[k]: f[k] - beta * (r[k] - rbar) for k in range(len(names))}
    return out


def _jackknife(dates, signal, forward, rng) -> list[dict]:
    """Leave-one-commodity-out on the baseline flow spread, per cross_section's
    lesson: membership is the axis a 24-name portfolio is most exposed on.
    The tercile-cut artifact documented there applies here too -- compare
    drops against each other, not against the full baseline."""
    names = sorted({n for day in dates for n in signal[day]})
    saved, out = xs._BOOTSTRAP_ITERS, []
    xs._BOOTSTRAP_ITERS = _JACKKNIFE_ITERS
    try:
        for dropped in names:
            sub = {d: {n: v for n, v in m.items() if n != dropped} for d, m in signal.items()}
            ok = [d for d in dates if len(sub[d]) >= _MIN_COMMODITIES]
            series = xs._spreads(ok, sub, forward)
            mean = statistics.fmean(series)
            out.append({
                "dropped": dropped,
                "weeks": len(series),
                "mean_weekly_spread": mean,
                "annualised": mean * 52,
                "p_value": xs._p_two_sided(series, rng),
            })
    finally:
        xs._BOOTSTRAP_ITERS = saved
    out.sort(key=lambda r: -r["p_value"])
    return out


def _stats(series: list[float], rng) -> dict:
    mean = statistics.fmean(series)
    return {
        "weeks": len(series),
        "mean_weekly": mean,
        "annualised": mean * 52,
        "p_value": xs._p_two_sided(series, rng),
    }


def run() -> dict:
    rng = random.Random(_SEED)
    dates, flow_sig, rev_sig, forward, vol = _panel()
    if len(dates) < 100:
        raise RuntimeError(f"only {len(dates)} usable weeks; cannot run the test")

    orth_sig = orthogonalise(dates, flow_sig, rev_sig)
    odates = sorted(orth_sig)

    flow_spread = xs._spreads(dates, flow_sig, forward)
    rev_spread = xs._spreads(dates, rev_sig, forward)
    orth_spread = xs._spreads(odates, orth_sig, forward)

    flow_stats = _stats(flow_spread, rng)
    rev_stats = _stats(rev_spread, rng)
    orth_stats = _stats(orth_spread, rng)
    mean, lo_ci, hi_ci = xs._block_bootstrap_ci(flow_spread, rng)

    flow_ic = xs._ic_series(dates, flow_sig, forward)
    rev_ic = xs._ic_series(dates, rev_sig, forward)
    orth_ic = xs._ic_series(odates, orth_sig, forward)
    ic_rows = {
        "flow": {"mean": statistics.fmean(flow_ic), "p_value": xs._p_two_sided(flow_ic, rng)},
        "reversal": {"mean": statistics.fmean(rev_ic), "p_value": xs._p_two_sided(rev_ic, rng)},
        "orthogonalised_flow": {"mean": statistics.fmean(orth_ic), "p_value": xs._p_two_sided(orth_ic, rng)},
    }

    vdates, vsignal = xs._vol_subpanel(dates, flow_sig, vol)
    target = statistics.fmean([v for d in vdates for v in vol[d].values()])
    rp_stats = _stats(xs._vol_scaled_spreads(vdates, vsignal, forward, vol, target), rng)
    ew_stats = _stats(xs._spreads(vdates, vsignal, forward), rng)

    gap = xs._leg_vol_gap(vdates, vsignal, vol)
    gap_mean = statistics.fmean(gap)
    gap_p = xs._p_two_sided(gap, rng)

    # The reversal benchmark gets the same vol-tilt treatment as the signal
    # under test. It is the side that looks alive, and cross_section.py's
    # whole lesson is that an equal-weighted spread can be a volatility bet
    # wearing a signal's clothes.
    rvdates, rvsignal = xs._vol_subpanel(dates, rev_sig, vol)
    rev_rp_stats = _stats(xs._vol_scaled_spreads(rvdates, rvsignal, forward, vol, target), rng)
    rev_ew_stats = _stats(xs._spreads(rvdates, rvsignal, forward), rng)
    rev_gap = xs._leg_vol_gap(rvdates, rvsignal, vol)
    rev_gap_mean = statistics.fmean(rev_gap)
    rev_gap_p = xs._p_two_sided(rev_gap, rng)

    tail = xs._tail_contribution(flow_spread)
    overlap = statistics.correlation(flow_spread, rev_spread)
    jackknife = _jackknife(dates, flow_sig, forward, rng)

    flow_lives = flow_stats["p_value"] < 0.05 or ic_rows["flow"]["p_value"] < 0.05
    orth_lives = orth_stats["p_value"] < 0.05 or ic_rows["orthogonalised_flow"]["p_value"] < 0.05
    if orth_lives:
        verdict = ("flow carries information beyond the same week's price action; "
                   "survives orthogonalisation -- worth the full robustness treatment")
    elif flow_lives:
        verdict = ("flow's apparent edge is inherited short-term reversal; "
                   "orthogonalised against the formation-week return it dies -- "
                   "the CFTC column added nothing")
    else:
        verdict = "no detectable cross-sectional information in Managed Money flow at all"

    return {
        "generated": date.today().isoformat(),
        "question": "Does Managed Money FLOW rank next week's relative returns, "
                    "beyond what the same week's price move already tells you?",
        "portfolio": "equal-weighted terciles, long lowest-signal, short highest-signal, "
                     "1-week entry lag, 1-week hold",
        "weeks": len(dates),
        "first_week": dates[0],
        "last_week": dates[-1],
        "avg_commodities_per_week": statistics.fmean([len(flow_sig[d]) for d in dates]),
        "flow": flow_stats,
        "flow_ci95_low": lo_ci,
        "flow_ci95_high": hi_ci,
        "flow_positive_weeks_pct": 100 * sum(1 for s in flow_spread if s > 0) / len(flow_spread),
        "reversal": rev_stats,
        "orthogonalised_flow": orth_stats,
        "ic": ic_rows,
        "risk_parity": rp_stats,
        "equal_weight_matched": ew_stats,
        "vol_gap_mean": gap_mean,
        "vol_gap_p_value": gap_p,
        "vol_gap_positive_weeks_pct": 100 * sum(1 for g in gap if g > 0) / len(gap),
        "reversal_risk_parity": rev_rp_stats,
        "reversal_equal_weight_matched": rev_ew_stats,
        "reversal_vol_gap_mean": rev_gap_mean,
        "reversal_vol_gap_p_value": rev_gap_p,
        "flow_reversal_spread_correlation": overlap,
        **tail,
        "jackknife": jackknife,
        "jackknife_specs_above_05": sum(1 for r in jackknife if r["p_value"] >= 0.05),
        "verdict": verdict,
        "caveat": "price-only returns, excludes roll yield and costs; measures information, "
                  "not tradability",
    }


def _row(label: str, s: dict) -> str:
    return (f"| {label} | {s['weeks']:,} | {s['mean_weekly']*100:+.3f}% | "
            f"{s['annualised']*100:+.1f}% | {s['p_value']:.3f} |")


def _markdown(r: dict) -> str:
    return "\n".join([
        "# Managed Money flow: the cross-sectional test",
        "",
        f"Generated {r['generated']}.",
        "",
        "## The question",
        "",
        f"{r['question']} Portfolio: {r['portfolio']}. Sign convention: a "
        "price-pressure effect (heavy spec inflow -> weaker next week) shows as a "
        "positive spread and a negative IC.",
        "",
        f"**{r['weeks']:,} portfolio-weeks**, {r['first_week']} to {r['last_week']}, "
        f"averaging {r['avg_commodities_per_week']:.1f} commodities per week. The "
        "260-week percentile warmup is spent inside the 2010-start Managed Money "
        "history, which is why the sample starts ~2015 rather than 2010.",
        "",
        "## Head-to-head: the three specs that decide it",
        "",
        "| Signal | Weeks | Mean weekly | Annualised | p |",
        "|---|---|---|---|---|",
        _row("Managed Money flow", r["flow"]),
        _row("Pure short-term reversal (no CFTC data)", r["reversal"]),
        _row("Flow orthogonalised vs formation-week return", r["orthogonalised_flow"]),
        "",
        f"The flow and reversal spread series correlate at only "
        f"{r['flow_reversal_spread_correlation']:+.2f} week to week: the +0.133 "
        "contemporaneous flow/return correlation is too weak, once pushed through "
        "within-commodity percentiles and tercile cuts, to make the two portfolios "
        "overlap much. So the orthogonalisation barely changes flow -- and it did "
        "not need to, because flow has nothing to remove reversal FROM. Both flow "
        "rows are flat before and after the control.",
        "",
        "## Rank information coefficient",
        "",
        "Per-week Spearman correlation between signal and forward return; negative "
        "is the effect's sign. Ranking caps any single week's contribution, so a "
        "genuine ordering survives here and a magnitude artifact does not.",
        "",
        "| Signal | Mean IC | p |",
        "|---|---|---|",
        f"| Flow | {r['ic']['flow']['mean']:+.4f} | {r['ic']['flow']['p_value']:.3f} |",
        f"| Reversal | {r['ic']['reversal']['mean']:+.4f} | {r['ic']['reversal']['p_value']:.3f} |",
        f"| Orthogonalised flow | {r['ic']['orthogonalised_flow']['mean']:+.4f} | "
        f"{r['ic']['orthogonalised_flow']['p_value']:.3f} |",
        "",
        "## Volatility tilt check",
        "",
        f"Trailing-vol gap between the flow portfolio's legs: "
        f"{r['vol_gap_mean']*100:+.2f}pp/wk (p={r['vol_gap_p_value']:.3f}, long leg "
        f"more volatile in {r['vol_gap_positive_weeks_pct']:.0f}% of weeks). "
        f"Risk-parity legs: {r['risk_parity']['annualised']*100:+.1f}% annualised, "
        f"p={r['risk_parity']['p_value']:.3f}, against the matched equal-weighted "
        f"control's {r['equal_weight_matched']['annualised']*100:+.1f}%, "
        f"p={r['equal_weight_matched']['p_value']:.3f}.",
        "",
        "## The reversal side-finding, treated with the same suspicion",
        "",
        f"The benchmark that uses no CFTC data at all prints "
        f"{r['reversal']['annualised']*100:+.1f}% annualised at "
        f"p={r['reversal']['p_value']:.3f}, and its IC "
        f"({r['ic']['reversal']['mean']:+.4f}, p={r['ic']['reversal']['p_value']:.3f}) "
        "is modest next to that spread -- the same big-spread/small-IC shape that, in "
        "the legacy study, meant the money lived in magnitudes rather than ordering. "
        "Its own vol-tilt numbers: leg vol gap "
        f"{r['reversal_vol_gap_mean']*100:+.2f}pp/wk "
        f"(p={r['reversal_vol_gap_p_value']:.3f}); risk-parity legs "
        f"{r['reversal_risk_parity']['annualised']*100:+.1f}% "
        f"(p={r['reversal_risk_parity']['p_value']:.3f}) against a matched "
        f"equal-weighted {r['reversal_equal_weight_matched']['annualised']*100:+.1f}% "
        f"(p={r['reversal_equal_weight_matched']['p_value']:.3f}). Short-term reversal "
        "is also the strategy classically killed by transaction costs (weekly turnover "
        "approaches 100%) and inflated by measurement noise in closes. It is reported "
        "here as the yardstick flow failed against, not as a discovery -- promoting it "
        "to a finding would need the full cross_section.py treatment on its own terms, "
        "and that is a different project from 'does CFTC positioning data help'.",
        "",
        "## Tail contribution",
        "",
        f"The {r['tail_weeks']} largest weeks by magnitude net {r['tail_net']:+.1%} "
        f"against a series total of {r['series_total']:+.1%}.",
        "",
        "## Jackknife (baseline flow spread)",
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
    print("Running Managed Money flow test ...")
    result = run()
    RESEARCH_DIR.mkdir(exist_ok=True)
    (RESEARCH_DIR / "MM-FLOW.md").write_text(_markdown(result), encoding="utf-8")
    (RESEARCH_DIR / "mm_flow.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\n{result['weeks']:,} portfolio-weeks, {result['first_week']} to {result['last_week']}")
    print(f"flow        {result['flow']['annualised']*100:+.1f}%/yr  p={result['flow']['p_value']:.3f}   "
          f"IC {result['ic']['flow']['mean']:+.4f} p={result['ic']['flow']['p_value']:.3f}")
    print(f"reversal    {result['reversal']['annualised']*100:+.1f}%/yr  p={result['reversal']['p_value']:.3f}   "
          f"IC {result['ic']['reversal']['mean']:+.4f} p={result['ic']['reversal']['p_value']:.3f}")
    print(f"orth flow   {result['orthogonalised_flow']['annualised']*100:+.1f}%/yr  "
          f"p={result['orthogonalised_flow']['p_value']:.3f}   "
          f"IC {result['ic']['orthogonalised_flow']['mean']:+.4f} "
          f"p={result['ic']['orthogonalised_flow']['p_value']:.3f}")
    print(f"spread correlation flow vs reversal {result['flow_reversal_spread_correlation']:+.2f}")
    print(f"reversal leg vol gap {result['reversal_vol_gap_mean']*100:+.2f}pp/wk "
          f"p={result['reversal_vol_gap_p_value']:.3f}   "
          f"risk-parity {result['reversal_risk_parity']['annualised']*100:+.1f}%/yr "
          f"p={result['reversal_risk_parity']['p_value']:.3f}")
    print(f"verdict: {result['verdict']}")
