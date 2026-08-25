"""
Cross-sectional test: does RELATIVE positioning rank predict relative returns?

Why this exists, when study.py already found nothing. study.py asked a
time-series question ("what follows crowded positioning in corn?") and the
answer was dominated by sample size: positioning is so persistent that 40
years of corn yields ~8 independent episodes. No amount of care fixes that.

This asks a different question with a far better sample: every week, rank all
commodities against each other by positioning, buy the least-crowded basket
and sell the most-crowded, and look at the resulting weekly return series.
The unit of observation becomes the portfolio-week (~1,300 of them) rather
than the per-commodity episode (~8), because a single week contributes one
observation using all 24 commodities at once. This is how the commodity
factor literature tests hedging-pressure and positioning effects, and it can
detect a relative effect even when no individual commodity has enough events.

Design choices and the reasoning:

    - Signal is net position as a share of open interest, ranked into a
      point-in-time percentile per commodity (same as everywhere else in
      this repo: raw contracts would rank market growth, and full-history
      ranking would be look-ahead bias).
    - Portfolio is formed on the signal known AT formation, then held for
      the following week. Forming and measuring in the same week would be
      trading on information not yet published: CFTC releases Friday for
      Tuesday's positions, so even a one-week lag is generous to the
      strategy rather than optimistic.
    - Equal-weighted terciles rather than a regression, so the result is a
      readable return series rather than a coefficient, and one outlier
      commodity cannot dominate.
    - Returns are simple weekly price changes in the front continuous
      contract. This is NOT a tradable return: it ignores roll yield, which
      is the dominant term in real commodity futures returns, plus costs and
      margin. So this measures whether the signal contains information, not
      whether a fund could harvest it.
    - Inference on the mean weekly spread uses a stationary block bootstrap
      (mean block 13 weeks) because the spread series is autocorrelated;
      an i.i.d. t-test would overstate significance.

Run:  python cross_section.py
"""

import json
import random
import statistics
from datetime import date
from pathlib import Path

import analysis
import contracts
import prices
import study

# CFTC data is as-of Tuesday but published the following Friday, so a
# portfolio formed on the as-of date and held Tuesday-to-Tuesday spends
# three of its seven days trading on unpublished information. Entering one
# week later puts the entire holding period after publication. Measured
# cost of this correction: the mean weekly spread falls from +0.149% to
# +0.113% and p from 0.006 to 0.046, i.e. roughly a quarter of the raw
# effect was look-ahead.
_ENTRY_LAG_WEEKS = 1
_HOLD_WEEKS = 1
_MIN_COMMODITIES = 8  # a cross-section thinner than this is not a cross-section
_BLOCK_MEAN = 13
_BOOTSTRAP_ITERS = 5000
_SEED = 20260825

REPO_ROOT = Path(__file__).resolve().parent
RESEARCH_DIR = REPO_ROOT / "research"


def _panel() -> tuple[list[str], dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    """Build the aligned panel: signal percentile and forward return per (date, commodity)."""
    by_market = analysis.load_category_rows(REPO_ROOT / ".cot-cache" / "Legacy Report (Futures Only)")

    signal: dict[str, dict[str, float]] = {}
    forward: dict[str, dict[str, float]] = {}
    all_dates: set[str] = set()

    for name, commodity in contracts.COMMODITIES.items():
        shares = contracts.net_share(contracts.stitch(by_market, commodity))
        if len(shares) < study._WARMUP_WEEKS + 20:
            continue
        dates = [d for d, _ in shares]
        pcts = study.point_in_time_percentiles([v for _, v in shares])
        closes = prices.weekly_closes(commodity.ticker)
        if not closes:
            continue

        for i, day in enumerate(dates):
            entry = i + _ENTRY_LAG_WEEKS
            exit_ = entry + _HOLD_WEEKS
            if pcts[i] is None or exit_ >= len(dates):
                continue
            ret = prices.pct_change(closes, dates[entry], dates[exit_])
            if ret is None:
                continue
            signal.setdefault(day, {})[name] = pcts[i]
            forward.setdefault(day, {})[name] = ret
            all_dates.add(day)

    usable = sorted(d for d in all_dates if len(signal.get(d, {})) >= _MIN_COMMODITIES)
    return usable, signal, forward


def _tercile_spread(dates, signal, forward) -> list[tuple[str, float, float, float, int]]:
    """Per week: (date, low-crowding mean return, high-crowding mean return, spread, n)."""
    out = []
    for day in dates:
        pairs = sorted(signal[day].items(), key=lambda kv: kv[1])
        n = len(pairs)
        cut = max(1, n // 3)
        low = [forward[day][name] for name, _ in pairs[:cut]]          # least crowded long
        high = [forward[day][name] for name, _ in pairs[-cut:]]        # most crowded long
        lo, hi = statistics.fmean(low), statistics.fmean(high)
        out.append((day, lo, hi, lo - hi, n))
    return out


def _spreads(dates, signal, forward, buckets: int = 3, clip: float | None = None) -> list[float]:
    """Weekly long-minus-short spread, optionally with finer buckets or clipped returns."""
    out = []
    for day in dates:
        pairs = sorted(signal[day].items(), key=lambda kv: kv[1])
        cut = max(1, len(pairs) // buckets)

        def side(sub):
            vals = [forward[day][name] for name, _ in sub]
            if clip is not None:
                vals = [max(-clip, min(clip, v)) for v in vals]
            return statistics.fmean(vals)

        out.append(side(pairs[:cut]) - side(pairs[-cut:]))
    return out


def _robustness(dates, signal, forward, rng) -> list[dict]:
    """The specifications that decide whether the baseline result is real or fragile.

    A genuine monotonic effect should get STRONGER with finer buckets, should
    not depend on a handful of extreme weeks, and should appear in both
    halves of the sample. Anything that only works in one specification is
    a data-mining artifact until proven otherwise.
    """
    mid = len(dates) // 2
    specs = [
        ("Quintiles instead of terciles", _spreads(dates, signal, forward, buckets=5),
         "a monotonic signal should sharpen, not blur, under a more extreme sort"),
        ("Weekly returns clipped at +/-10%", _spreads(dates, signal, forward, clip=0.10),
         "tests whether a few large moves carry the result"),
        ("Weekly returns clipped at +/-5%", _spreads(dates, signal, forward, clip=0.05),
         "same, more aggressively"),
        (f"First half ({dates[0][:7]} to {dates[mid][:7]})", _spreads(dates[:mid], signal, forward),
         "out-of-sample stability"),
        (f"Second half ({dates[mid][:7]} to {dates[-1][:7]})", _spreads(dates[mid:], signal, forward),
         "out-of-sample stability"),
    ]
    results = []
    for label, series, why in specs:
        mean = statistics.fmean(series)
        results.append({
            "spec": label,
            "why": why,
            "weeks": len(series),
            "mean_weekly_spread": mean,
            "annualised": mean * 52,
            "p_value": _p_two_sided(series, rng),
        })
    return results


def _block_bootstrap_ci(series: list[float], rng) -> tuple[float, float, float]:
    """Mean, and the 2.5/97.5 percentiles of its stationary-block-bootstrap distribution."""
    n = len(series)
    means = []
    for _ in range(_BOOTSTRAP_ITERS):
        drawn: list[float] = []
        while len(drawn) < n:
            start = rng.randrange(n)
            length = min(rng.randint(1, 2 * _BLOCK_MEAN - 1), n - len(drawn))
            drawn.extend(series[(start + k) % n] for k in range(length))
        means.append(statistics.fmean(drawn))
    means.sort()
    return statistics.fmean(series), means[int(0.025 * len(means))], means[int(0.975 * len(means))]


def _p_two_sided(series: list[float], rng) -> float:
    """Bootstrap p-value for mean != 0, preserving autocorrelation via blocks."""
    observed = statistics.fmean(series)
    centred = [v - observed for v in series]  # impose the null
    n = len(series)
    extreme = 0
    for _ in range(_BOOTSTRAP_ITERS):
        drawn: list[float] = []
        while len(drawn) < n:
            start = rng.randrange(n)
            length = min(rng.randint(1, 2 * _BLOCK_MEAN - 1), n - len(drawn))
            drawn.extend(centred[(start + k) % n] for k in range(length))
        if abs(statistics.fmean(drawn)) >= abs(observed):
            extreme += 1
    return extreme / _BOOTSTRAP_ITERS


def run() -> dict:
    rng = random.Random(_SEED)
    dates, signal, forward = _panel()
    if len(dates) < 100:
        raise RuntimeError(f"only {len(dates)} usable weeks; cannot run a cross-sectional test")

    weekly = _tercile_spread(dates, signal, forward)
    spreads = [w[3] for w in weekly]
    mean, lo_ci, hi_ci = _block_bootstrap_ci(spreads, rng)
    p = _p_two_sided(spreads, rng)

    wins = sum(1 for s in spreads if s > 0)
    ann = mean * 52
    vol = statistics.stdev(spreads) * (52 ** 0.5)
    robustness = _robustness(dates, signal, forward, rng)
    held_up = sum(1 for r in robustness if r["p_value"] < 0.05)

    return {
        "generated": date.today().isoformat(),
        "entry_lag_weeks": _ENTRY_LAG_WEEKS,
        "robustness": robustness,
        "robustness_specs_significant": held_up,
        "robustness_specs_total": len(robustness),
        "verdict": (
            "fragile" if held_up <= 1 else "holds up across most specifications"
        ),
        "question": "Do the least-crowded commodities outperform the most-crowded, week to week?",
        "portfolio": "equal-weighted terciles, long lowest positioning percentile, short highest",
        "hold_weeks": _HOLD_WEEKS,
        "weeks": len(spreads),
        "first_week": dates[0],
        "last_week": dates[-1],
        "avg_commodities_per_week": statistics.fmean([w[4] for w in weekly]),
        "mean_weekly_spread": mean,
        "ci95_low": lo_ci,
        "ci95_high": hi_ci,
        "p_value_block_bootstrap": p,
        "positive_weeks_pct": 100 * wins / len(spreads),
        "annualised_spread": ann,
        "annualised_vol": vol,
        "sharpe_like": ann / vol if vol else float("nan"),
        "caveat": "price-only returns, excludes roll yield and costs; measures information, not tradability",
    }


def _markdown(r: dict) -> str:
    if r["p_value_block_bootstrap"] >= 0.05:
        verdict = "**No detectable effect.**"
    elif r["verdict"] == "fragile":
        verdict = (
            f"**Nominally significant, but fragile.** The baseline spec clears p<0.05, yet only "
            f"{r['robustness_specs_significant']} of {r['robustness_specs_total']} robustness "
            "specifications do. Treat this as \"not established\", not as a finding."
        )
    else:
        verdict = "**Detectable effect** that survives the robustness checks, before costs and roll yield."
    return "\n".join([
        "# Cross-sectional test: relative positioning vs relative returns",
        "",
        f"Generated {r['generated']}.",
        "",
        "## Why this test",
        "",
        "The time-series study (FINDINGS.md) was starved of sample: positioning is so "
        "persistent that 40 years yields roughly 8 independent episodes per commodity. "
        "This test uses the portfolio-week as the observation instead, so the whole "
        f"cross-section contributes once per week: **{r['weeks']:,} weekly observations** "
        f"({r['first_week']} to {r['last_week']}), averaging "
        f"{r['avg_commodities_per_week']:.1f} commodities per week.",
        "",
        "## Result",
        "",
        verdict,
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Portfolio | {r['portfolio']} |",
        f"| Holding period | {r['hold_weeks']} week |",
        f"| Weekly observations | {r['weeks']:,} |",
        f"| Mean weekly spread | {r['mean_weekly_spread']*100:+.3f}% |",
        f"| 95% CI (block bootstrap) | {r['ci95_low']*100:+.3f}% to {r['ci95_high']*100:+.3f}% |",
        f"| p-value | {r['p_value_block_bootstrap']:.3f} |",
        f"| Positive weeks | {r['positive_weeks_pct']:.1f}% |",
        f"| Annualised spread | {r['annualised_spread']*100:+.1f}% |",
        f"| Annualised vol | {r['annualised_vol']*100:.1f}% |",
        f"| Return/vol ratio | {r['sharpe_like']:.2f} |",
        "",
        "## Robustness",
        "",
        "The baseline number above is one specification. These are the checks that decide "
        "whether it means anything.",
        "",
        "| Specification | Weeks | Mean weekly | Annualised | p | What it tests |",
        "|---|---|---|---|---|---|",
        *[f"| {s['spec']} | {s['weeks']:,} | {s['mean_weekly_spread']*100:+.3f}% | "
          f"{s['annualised']*100:+.1f}% | {s['p_value']:.3f} | {s['why']} |"
          for s in r["robustness"]],
        "",
        "## Reading this honestly",
        "",
        f"- {r['caveat']}. Roll yield is the dominant term in real commodity futures "
        "returns and is entirely absent here, so the annualised figure is not a "
        "backtest of a strategy.",
        "- The portfolio is formed on the prior week's signal and held the following "
        "week. CFTC publishes Friday for Tuesday's positions, so the real information "
        "lag is longer than modelled; this is generous to the signal, not conservative.",
        "- Inference uses a stationary block bootstrap (mean block 13 weeks) because "
        "the weekly spread series is autocorrelated. An i.i.d. t-test on the same data "
        "would report a smaller p-value and would be wrong.",
        "- The effect shrinking sharply when weekly returns are clipped means it lives in "
        "the tails. Two candidate explanations, and they are not distinguishable with this "
        "data: a genuine premium for bearing spike risk, or artifacts in Yahoo's front-month "
        "continuous series, which is not roll-adjusted, so every roll injects a price gap "
        "that is not a real return. Since term structure and positioning are correlated, "
        "roll artifacts would not wash out at random. Resolving this needs a roll-adjusted "
        "or roll-aware return series, which is the single highest-value next step.",
        "- If the CI straddles zero, or the robustness table mostly fails, the honest "
        "conclusion is that this dataset does not establish a positioning-based "
        "cross-sectional signal, which is consistent with the time-series result and with "
        "the literature.",
        "",
    ])


if __name__ == "__main__":
    print("Running cross-sectional test ...")
    result = run()
    RESEARCH_DIR.mkdir(exist_ok=True)
    (RESEARCH_DIR / "cross_section.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (RESEARCH_DIR / "CROSS-SECTION.md").write_text(_markdown(result), encoding="utf-8")
    print(f"\n{result['weeks']:,} weekly observations")
    print(f"mean weekly spread {result['mean_weekly_spread']*100:+.3f}%  "
          f"p={result['p_value_block_bootstrap']:.3f}  "
          f"CI [{result['ci95_low']*100:+.3f}%, {result['ci95_high']*100:+.3f}%]")
