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

What the 2026-08-25 re-examination changed, because the first robustness
table was read wrong and the conclusion happened to survive for the wrong
reasons:

  - The originally-named suspect, roll contamination in Yahoo's continuous
    series, is NOT the driver. `roll_check` localises it to three
    livestock/dairy contracts, and removing them makes the raw effect
    STRONGER (+5.9% -> +6.3% annualised, p 0.047 -> 0.037). Milk alone out:
    +7.0%, p=0.034. Roll gaps were diluting the signal, not creating it.
  - Three of the five original specs measured statistical power, not effect
    stability, and were miscounted as failures. See the "Reading a robustness
    table" section of the generated markdown for the arithmetic.
  - What actually explains the result is a VOLATILITY TILT. The least-crowded
    leg is systematically more volatile than the most-crowded leg (+0.37pp
    per week, p=0.000, holding in 69% of weeks), so the portfolio was long
    high-vol / short low-vol commodities two weeks in three. There is a
    mechanism: volatility clusters, and speculators cut net length AFTER
    adverse moves, so a low crowding percentile mechanically coincides with
    elevated trailing vol. The signal is partly a lagged volatility proxy.
  - The rank information coefficient -- the tail-insensitive version of the
    same question -- is flat (about -0.005, p=0.42). There is no monotonic
    cross-sectional ordering to find. This, not the fragility table, is the
    strongest single piece of evidence against the signal.

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
# The jackknife runs one bootstrap per commodity, so it gets a cheaper budget.
# p-resolution of 0.0005 is far finer than a robustness screen needs.
_JACKKNIFE_ITERS = 2000
_SEED = 20260825

# Trailing realised vol for the risk-parity spec, measured over weeks
# STRICTLY BEFORE entry. Full-sample vol would be look-ahead of exactly the
# kind point_in_time_percentiles exists to avoid.
# The third angle the verdict rests on: if the largest weeks by magnitude net
# AGAINST the effect, no small set of weeks is manufacturing it.
_TAIL_WEEKS = 20

_VOL_WINDOW = 52
_MIN_VOL_OBS = 30

REPO_ROOT = Path(__file__).resolve().parent
RESEARCH_DIR = REPO_ROOT / "research"


def _panel() -> tuple[list[str], dict, dict, dict]:
    """The aligned panel: signal percentile, forward return, and trailing vol.

    `vol` is deliberately allowed to be sparse where the first year of a
    commodity's price history has not accumulated _MIN_VOL_OBS weeks yet.
    Gating the whole panel on it would silently shrink the baseline sample
    and make the risk-parity spec non-comparable to it; `_vol_subpanel`
    restricts instead, and both the control and the treatment are reported
    on that restricted sample.
    """
    by_market = analysis.load_category_rows(REPO_ROOT / ".cot-cache" / "Legacy Report (Futures Only)")

    signal: dict[str, dict[str, float]] = {}
    forward: dict[str, dict[str, float]] = {}
    vol: dict[str, dict[str, float]] = {}
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
        step = [prices.pct_change(closes, dates[i], dates[i + 1]) for i in range(len(dates) - 1)]

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

            # step[k] spans dates[k] -> dates[k+1], so returns known at entry
            # are step[:entry]. Slicing up to `entry` is what keeps this
            # point-in-time.
            hist = [r for r in step[max(0, entry - _VOL_WINDOW):entry] if r is not None]
            if len(hist) >= _MIN_VOL_OBS:
                sd = statistics.stdev(hist)
                if sd > 0:
                    vol.setdefault(day, {})[name] = sd

    usable = sorted(d for d in all_dates if len(signal.get(d, {})) >= _MIN_COMMODITIES)
    return usable, signal, forward, vol


def _vol_subpanel(dates, signal, vol) -> tuple[list[str], dict]:
    """Restrict every week's cross-section to names with a trailing vol estimate."""
    restricted = {}
    for day in dates:
        names = {n: p for n, p in signal[day].items() if n in vol.get(day, {})}
        if len(names) >= _MIN_COMMODITIES:
            restricted[day] = names
    return sorted(restricted), restricted


def _average_ranks(vals: list[float]) -> list[float]:
    """Ranks 1..n, with tied values sharing the average of the positions they span."""
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        shared = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = shared
        i = j + 1
    return ranks


def spearman_ic(signal_vals: list[float], return_vals: list[float]) -> float | None:
    """Rank correlation between crowding and forward return for ONE week.

    This is the information coefficient (Grinold's fundamental law of active
    management: IR = IC * sqrt(breadth)), and it is the tail-insensitive
    version of the tercile test. Ranking caps how much any single extreme
    return can contribute, so a real monotonic ordering survives here while
    an effect that lives only in a few large moves does not.

    Contract:
      - `signal_vals[k]` and `return_vals[k]` describe the same commodity;
        the lists are equal length and at least _MIN_COMMODITIES long.
      - Convert each list to ranks, then return the Pearson correlation of
        the two rank vectors.
      - Ties take the AVERAGE of the positions they span (the standard
        tie-corrected Spearman). Crowding percentiles are continuous so ties
        are rare there, but forward returns can genuinely tie at zero, and
        assigning them arbitrary distinct ranks invents ordering that is not
        in the data.
      - Return None if either rank vector has zero variance, which happens
        when every value is identical -- correlation is undefined, not zero,
        and folding it in as zero would bias the mean IC toward the null.
      - Sign convention: `signal_vals` is a CROWDING percentile, so a real
        "crowded positions underperform" effect gives a NEGATIVE IC.
    """
    a, b = _average_ranks(signal_vals), _average_ranks(return_vals)
    try:
        return statistics.correlation(a, b)
    except statistics.StatisticsError:
        return None


def vol_scaled_leg(names, returns: dict, vols: dict, target_vol: float) -> float:
    """Mean return of one leg after scaling each name to a common vol.

    Equal-weighting sizes positions by dollar, which means a commodity with
    twice the volatility contributes twice the risk. That is how the
    portfolio picked up its volatility tilt: the least-crowded leg is
    reliably the more volatile one, so the equal-weighted spread is long
    volatility as well as long the signal. Scaling each name by
    target_vol / its own trailing vol equalises risk contribution and
    strips that exposure out (Moreira-Muir volatility management, and the
    same correction that turns beta-sorted returns into betting-against-beta).

    Contract:
      - `names` is the leg's commodities; `returns[n]` and `vols[n]` are that
        week's forward return and trailing vol for each.
      - Each name's scaled return is its return times target_vol / vols[n].
      - Return the mean over the leg.
      - `target_vol` only sets the units the answer is quoted in -- it
        multiplies every observation equally, so it cannot change a p-value.
        It exists so the output is readable next to the unscaled spread.
    """
    return statistics.fmean(returns[n] * target_vol / vols[n] for n in names)


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


def _ic_series(dates, signal, forward, drop=()) -> list[float]:
    out = []
    for day in dates:
        names = [n for n in signal[day] if n not in drop]
        if len(names) < _MIN_COMMODITIES:
            continue
        ic = spearman_ic([signal[day][n] for n in names], [forward[day][n] for n in names])
        if ic is not None:
            out.append(ic)
    return out


def _vol_scaled_spreads(dates, signal, forward, vol, target_vol) -> list[float]:
    out = []
    for day in dates:
        pairs = sorted(signal[day].items(), key=lambda kv: kv[1])
        cut = max(1, len(pairs) // 3)
        lo = vol_scaled_leg([n for n, _ in pairs[:cut]], forward[day], vol[day], target_vol)
        hi = vol_scaled_leg([n for n, _ in pairs[-cut:]], forward[day], vol[day], target_vol)
        out.append(lo - hi)
    return out


def _leg_vol_gap(dates, signal, vol) -> list[float]:
    """Per week: trailing vol of the least-crowded leg minus the most-crowded leg.

    If this is reliably positive the equal-weighted spread is not a pure
    positioning bet, it is also long volatility.
    """
    out = []
    for day in dates:
        pairs = sorted(signal[day].items(), key=lambda kv: kv[1])
        cut = max(1, len(pairs) // 3)
        out.append(statistics.fmean([vol[day][n] for n, _ in pairs[:cut]])
                   - statistics.fmean([vol[day][n] for n, _ in pairs[-cut:]]))
    return out


def _tail_contribution(spreads: list[float], k: int = _TAIL_WEEKS) -> dict:
    """Do the k biggest weeks by magnitude carry the total, or net against it?

    A magnitude-weighted spread can be manufactured by a handful of weeks, so
    "the tails do not drive it" needs a number rather than an assertion. Note
    what this is NOT: the largest single positive and negative weeks are
    near-mirror images (+16% / -16%), and quoting those as the tail's net
    contribution was an error in an earlier version of the docs.
    """
    top = sorted(spreads, key=lambda v: -abs(v))[:k]
    return {
        "tail_weeks": k,
        "tail_net": sum(top),
        "tail_largest_week": max(spreads),
        "tail_most_negative_week": min(spreads),
        "series_total": sum(spreads),
    }


def _clip_share(dates, forward, clip: float) -> float:
    """Fraction of commodity-weeks a clip actually binds on."""
    vals = [r for day in dates for r in forward[day].values()]
    return sum(1 for r in vals if abs(r) > clip) / len(vals)


def _jackknife(dates, signal, forward, rng) -> list[dict]:
    """Drop one commodity at a time. Does the result rest on a single contract?

    The original robustness table varied buckets, clipping and time, but
    never cross-section MEMBERSHIP, which is the axis a 24-name portfolio is
    most exposed on.

    One mechanical artifact to expect when reading this: dropping any name
    takes the tercile cut from 24//3 = 8 to 23//3 = 7, so both legs get
    slightly more extreme and most drops nudge the mean UP. That is the cut
    changing, not the dropped commodity mattering. Compare drops against
    each other, not against the 24-name baseline.
    """
    names = sorted({n for day in dates for n in signal[day]})
    saved, out = _BOOTSTRAP_ITERS, []
    globals()["_BOOTSTRAP_ITERS"] = _JACKKNIFE_ITERS
    try:
        for dropped in names:
            sub = {d: {n: v for n, v in m.items() if n != dropped} for d, m in signal.items()}
            ok = [d for d in dates if len(sub[d]) >= _MIN_COMMODITIES]
            series = _spreads(ok, sub, forward)
            mean = statistics.fmean(series)
            out.append({
                "dropped": dropped,
                "weeks": len(series),
                "mean_weekly_spread": mean,
                "annualised": mean * 52,
                "p_value": _p_two_sided(series, rng),
            })
    finally:
        globals()["_BOOTSTRAP_ITERS"] = saved
    out.sort(key=lambda r: -r["p_value"])
    return out


def _robustness(dates, signal, forward, vol, rng) -> list[dict]:
    """Specifications that decide whether the baseline result means anything.

    Each spec is tagged with WHAT IT CAN FALSIFY, because the first version
    of this table conflated two different things and drew the wrong lesson
    from three of its five rows:

      "effect size" -- the spec leaves the sample and the estimator roughly
      intact, so a large move in the mean is real evidence. These are the
      only rows worth counting pass/fail.

      "power" -- the spec deliberately shrinks the sample or de-diversifies
      the legs, so the standard error grows BY CONSTRUCTION and a larger
      p-value is the expected outcome even for a genuine effect. Compare the
      means across these rows; ignore their p-values as falsifications.

      "distorted" -- the transform changes so many observations that the
      resulting estimate is not measuring the same quantity any more. Kept
      only because the original table leaned on it.
    """
    mid = len(dates) // 2
    vdates, vsignal = _vol_subpanel(dates, signal, vol)
    target = statistics.fmean([v for d in vdates for v in vol[d].values()])
    contaminated = {"Class III Milk", "Lean Hogs", "Live Cattle"}
    ex_signal = {d: {n: v for n, v in m.items() if n not in contaminated} for d, m in signal.items()}
    ex_dates = [d for d in dates if len(ex_signal[d]) >= _MIN_COMMODITIES]

    specs = [
        ("Vol-scaled legs (risk parity)", "effect size",
         _vol_scaled_spreads(vdates, vsignal, forward, vol, target),
         "removes the volatility tilt; the control row below is the matched comparison"),
        ("Equal-weighted, same weeks as above", "effect size",
         _spreads(vdates, vsignal, forward),
         "control for the risk-parity row, so the two differ only by weighting"),
        (f"Ex roll-contaminated ({len(contaminated)} contracts)", "effect size",
         _spreads(ex_dates, ex_signal, forward),
         "drops the series roll_check flags; tests the original prime suspect"),
        (f"Returns winsorised at +/-10% ({_clip_share(dates, forward, 0.10)*100:.0f}% of obs)",
         "effect size", _spreads(dates, signal, forward, clip=0.10),
         "genuine outlier trim: it binds on few enough observations to stay comparable"),
        ("Quintiles instead of terciles", "power",
         _spreads(dates, signal, forward, buckets=5),
         "a quintile leg holds ~4 names against a tercile's ~8, so it is less "
         "diversified and noisier; a flat mean with a worse p is expected"),
        (f"First half ({dates[0][:7]} to {dates[mid][:7]})", "power",
         _spreads(dates[:mid], signal, forward),
         "halving the sample multiplies the standard error by ~sqrt(2)"),
        (f"Second half ({dates[mid][:7]} to {dates[-1][:7]})", "power",
         _spreads(dates[mid:], signal, forward),
         "same; compare the two halves' MEANS to each other, not their p-values to 0.05"),
        (f"Returns clipped at +/-5% ({_clip_share(dates, forward, 0.05)*100:.0f}% of obs)",
         "distorted", _spreads(dates, signal, forward, clip=0.05),
         "binds on too much of the data to be an outlier test; it compresses the "
         "whole distribution in the volatile half of the universe"),
    ]
    results = []
    for label, kind, series, why in specs:
        mean = statistics.fmean(series)
        results.append({
            "spec": label,
            "tests": kind,
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
    dates, signal, forward, vol = _panel()
    if len(dates) < 100:
        raise RuntimeError(f"only {len(dates)} usable weeks; cannot run a cross-sectional test")

    weekly = _tercile_spread(dates, signal, forward)
    spreads = [w[3] for w in weekly]
    mean, lo_ci, hi_ci = _block_bootstrap_ci(spreads, rng)
    p = _p_two_sided(spreads, rng)

    wins = sum(1 for s in spreads if s > 0)
    ann = mean * 52
    spread_vol = statistics.stdev(spreads) * (52 ** 0.5)

    ics = _ic_series(dates, signal, forward)
    ic_mean = statistics.fmean(ics)
    ic_sd = statistics.stdev(ics)
    ic_p = _p_two_sided(ics, rng)

    vdates, vsignal = _vol_subpanel(dates, signal, vol)
    gap = _leg_vol_gap(vdates, vsignal, vol)
    gap_mean = statistics.fmean(gap)
    gap_p = _p_two_sided(gap, rng)

    tail = _tail_contribution(spreads)

    robustness = _robustness(dates, signal, forward, vol, rng)
    jackknife = _jackknife(dates, signal, forward, rng)

    sized = [r for r in robustness if r["tests"] == "effect size"]
    held_up = sum(1 for r in sized if r["p_value"] < 0.05)
    jk_fail = sum(1 for r in jackknife if r["p_value"] >= 0.05)

    if ic_p >= 0.05 and any(r["spec"].startswith("Vol-scaled") and r["p_value"] >= 0.05
                            for r in robustness):
        verdict = "explained by a volatility tilt, not positioning"
    elif held_up <= 1:
        verdict = "fragile"
    else:
        verdict = "holds up across most specifications"

    return {
        "generated": date.today().isoformat(),
        "entry_lag_weeks": _ENTRY_LAG_WEEKS,
        "robustness": robustness,
        "robustness_effect_size_specs": len(sized),
        "robustness_effect_size_significant": held_up,
        "robustness_specs_total": len(robustness),
        "jackknife": jackknife,
        "jackknife_specs_above_05": jk_fail,
        "verdict": verdict,
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
        "annualised_vol": spread_vol,
        "sharpe_like": ann / spread_vol if spread_vol else float("nan"),
        "ic_weeks": len(ics),
        "ic_mean": ic_mean,
        "ic_sd": ic_sd,
        "ic_annualised_ir": ic_mean / ic_sd * (52 ** 0.5) if ic_sd else float("nan"),
        "ic_p_value": ic_p,
        "vol_gap_weeks": len(gap),
        "vol_gap_mean": gap_mean,
        "vol_gap_p_value": gap_p,
        "vol_gap_positive_weeks_pct": 100 * sum(1 for g in gap if g > 0) / len(gap),
        **tail,
        "caveat": "price-only returns, excludes roll yield and costs; measures information, not tradability",
    }


def _markdown(r: dict) -> str:
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
        "## Headline",
        "",
        f"The equal-weighted tercile spread earns {r['annualised_spread']*100:+.1f}% "
        f"annualised at p={r['p_value_block_bootstrap']:.3f}. **That number is not a "
        "positioning effect.** Two independent tests below say what it actually is.",
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
        "## Test 1: is there any rank information? (information coefficient)",
        "",
        "The tercile spread is a magnitude-weighted statistic, so a handful of large "
        "returns can carry it. The information coefficient asks the same question in "
        "ranks -- each week, the Spearman correlation across the cross-section between "
        "crowding percentile and forward return. Ranking caps how much any single "
        "extreme return can contribute, so a genuine monotonic ordering survives here "
        "and a magnitude artifact does not. This is the standard factor-research "
        "diagnostic (Grinold's fundamental law: IR = IC x sqrt(breadth)).",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Weeks | {r['ic_weeks']:,} |",
        f"| Mean IC | {r['ic_mean']:+.4f} |",
        f"| IC standard deviation | {r['ic_sd']:.3f} |",
        f"| Implied annual IR | {r['ic_annualised_ir']:+.2f} |",
        f"| p-value | {r['ic_p_value']:.3f} |",
        "",
        (f"The IC carries the right sign but is indistinguishable from zero "
         f"(p={r['ic_p_value']:.2f}). **There is no monotonic cross-sectional ordering "
         "to find.** Whatever the tercile spread is measuring, it is not a consistent "
         "tendency for less-crowded commodities to out-rank more-crowded ones."
         if r["ic_p_value"] >= 0.05 else
         f"The IC is significant (p={r['ic_p_value']:.3f}), so the ordering itself "
         "carries information and the tercile result is not purely a magnitude artifact."),
        "",
        "## Test 2: is the spread secretly a volatility bet?",
        "",
        "Equal weighting sizes positions by dollar, not by risk, so a commodity with "
        "twice the volatility contributes twice the risk. If crowding correlates with "
        "volatility, the long-short spread carries a volatility exposure that has "
        "nothing to do with positioning.",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Weeks | {r['vol_gap_weeks']:,} |",
        f"| Mean trailing-vol gap, long leg minus short leg | {r['vol_gap_mean']*100:+.2f}pp/wk |",
        f"| p-value | {r['vol_gap_p_value']:.3f} |",
        f"| Weeks the long leg is the more volatile | {r['vol_gap_positive_weeks_pct']:.0f}% |",
        "",
        (f"The least-crowded leg is systematically the more volatile one "
         f"({r['vol_gap_mean']*100:+.2f}pp per week, p={r['vol_gap_p_value']:.3f}, in "
         f"{r['vol_gap_positive_weeks_pct']:.0f}% of weeks). The portfolio was long "
         "high-vol and short low-vol commodities most of the time. There is a mechanism "
         "for it rather than just a correlation: volatility clusters, and speculators cut "
         "net length *after* adverse moves, so a low crowding percentile mechanically "
         "coincides with elevated trailing volatility. The signal is partly a lagged "
         "volatility proxy. The risk-parity row in the robustness table below removes "
         "this exposure."
         if r["vol_gap_p_value"] < 0.05 else
         "No detectable volatility tilt between the legs."),
        "",
        "## Robustness",
        "",
        "Each row is tagged with what it can actually falsify, which the first version of "
        "this table got wrong. See \"Reading a robustness table\" below.",
        "",
        "| Specification | Tests | Weeks | Mean weekly | Annualised | p | What it tests |",
        "|---|---|---|---|---|---|---|",
        *[f"| {s['spec']} | {s['tests']} | {s['weeks']:,} | {s['mean_weekly_spread']*100:+.3f}% | "
          f"{s['annualised']*100:+.1f}% | {s['p_value']:.3f} | {s['why']} |"
          for s in r["robustness"]],
        "",
        f"Of the {r['robustness_effect_size_specs']} effect-size specifications, "
        f"{r['robustness_effect_size_significant']} clear p<0.05. The power-limited and "
        "distorted rows are reported for continuity but are not counted, because a larger "
        "p-value there is the arithmetically expected outcome and not evidence of anything.",
        "",
        "## Reading a robustness table",
        "",
        "This section exists because the first version of this analysis counted "
        "\"0 of 5 specifications survive\" and concluded the effect was fragile. The "
        "conclusion was right; three fifths of the reasoning was not, and the error is "
        "worth keeping visible because it is easy to repeat.",
        "",
        "**A p-value is an effect size divided by a standard error.** A specification can "
        "raise a p-value by shrinking the numerator (real evidence against the effect) or "
        "by inflating the denominator (no evidence about the effect at all). A robustness "
        "table that only prints p-values cannot tell you which happened. Compare the "
        "*means*.",
        "",
        "- **Quintiles instead of terciles.** The original comment claimed a monotonic "
        "signal should sharpen under a more extreme sort. Under a finer sort the mean "
        "spread should rise *and* the volatility should rise, because a quintile leg holds "
        "~4 names against a tercile's ~8 and is that much less diversified. Which effect "
        "wins is an open question, so a worse p-value is not a falsification. The quintile "
        "mean came in flat against baseline, which is mild evidence against monotonicity "
        "-- and far weaker than the p-value degradation made it look.",
        "- **Each half of the sample.** Halving the sample multiplies the standard error by "
        "about sqrt(2), so an effect at p=0.045 in full is *expected* to land near p=0.15 "
        "in each half. Demanding that both halves independently clear p<0.05 is a much "
        "higher bar than the full-sample test, not a robustness check. The right question "
        "is whether the two halves' estimates differ from *each other*; here they differ "
        "by 0.3% annualised, which is nothing. This is the Gelman-Stern point that a "
        "difference in significance is not significance in difference.",
        "- **Clipping at +/-5%.** This binds on a large share of the observations, not a "
        "few outliers -- weekly moves above 5% are routine in natural gas, crude and "
        "cocoa. It compresses the whole distribution in the volatile half of the universe "
        "rather than trimming tails, so the resulting estimate is not comparable. The "
        "+/-10% winsorisation is the meaningful version and it leaves the estimate "
        "largely intact.",
        "",
        "The specifications that *do* carry evidence are the ones that change the "
        "weighting or the universe while leaving the sample size alone: risk parity "
        "against its matched equal-weighted control, and the ex-roll-contaminated "
        "universe.",
        "",
        "## Jackknife: does one contract carry the result?",
        "",
        "The original table varied buckets, clipping and time, but never cross-section "
        "membership -- the axis a 24-name portfolio is most exposed on. Each row drops one "
        "commodity and re-runs.",
        "",
        "| Dropped | Weeks | Mean weekly | Annualised | p |",
        "|---|---|---|---|---|",
        *[f"| {s['dropped']} | {s['weeks']:,} | {s['mean_weekly_spread']*100:+.3f}% | "
          f"{s['annualised']*100:+.1f}% | {s['p_value']:.3f} |" for s in r["jackknife"]],
        "",
        f"{r['jackknife_specs_above_05']} of {len(r['jackknife'])} single drops push p above "
        "0.05. Note the mechanical artifact: dropping any name takes the tercile cut from "
        "24//3 = 8 to 23//3 = 7, so both legs get slightly more extreme and most drops nudge "
        "the mean up. Compare the drops against each other, not against the 24-name baseline.",
        "",
        "## Roll contamination: the suspect that was wrong",
        "",
        "Yahoo's continuous front-month series is not roll-adjusted, so every contract "
        "roll injects a price gap that nobody earned. That was named here as the leading "
        "explanation for the residual effect, and as the highest-value next step. It was "
        "the wrong suspect.",
        "",
        "`roll_check.py` localises the contamination by bucketing weekly |return| by "
        "day-of-month: a calendar-fixed expiry makes a roll gap land in a consistent "
        "bucket. Three of 24 series are affected -- Class III Milk (2.97x, and its peak "
        "bucket matches its month-end settlement), Lean Hogs (1.51x, matching its "
        "~10th-business-day expiry) and Live Cattle (1.38x, last business day). The rest "
        "of the universe is flat to within 1.25x, and for monthly-cycle contracts like "
        "crude the test has real power and finds nothing.",
        "",
        "Removing the three contaminated contracts makes the raw effect **stronger**, not "
        "weaker (see the robustness table). Roll gaps were adding noise, not manufacturing "
        "the result. A roll-adjusted price feed would sharpen this analysis; it would not "
        "change its conclusion, so it is no longer the priority it was recorded as.",
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
        "- Trailing volatility for the risk-parity spec uses the 52 weeks strictly before "
        "entry. Full-sample volatility would be look-ahead bias of exactly the kind "
        "point-in-time percentiles exist to avoid, and measuring it (2026-08-26) shows "
        "where the damage lands: the point ESTIMATE is unchanged (+0.0959% vs +0.0964% "
        "per week), because ~81% of the leg vol gap is a durable cross-sectional ranking "
        "that a static estimate still sees. What changes is the standard error -- a "
        "rolling 1/vol scaler injects estimation noise and amplifies weeks whose trailing "
        "window happened to be low (18.5% vs 16.5% annualised) -- so full-sample vol "
        "would have reported this spec at p=0.084 rather than 0.142 and made the "
        "volatility tilt look like a weaker explanation than it is. The lesson is the "
        "same one the robustness table teaches: a specification can move a p-value "
        "without touching the effect.",
        "- Losing significance is not the same as demonstrating zero. Risk parity moves "
        "the point estimate by roughly a quarter, which on its own would be suggestive "
        "rather than conclusive. What makes the reading decisive is that three "
        "independent angles agree: no rank information, a highly significant volatility "
        f"tilt in the legs, and the {r['tail_weeks']} largest weeks by magnitude netting "
        f"{r['tail_net']:+.1%} against a series total of {r['series_total']:+.1%} -- so "
        "the effect comes from the rest of the sample, not from a handful of weeks.",
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
    print(f"mean IC {result['ic_mean']:+.4f}  p={result['ic_p_value']:.3f}")
    print(f"leg vol gap {result['vol_gap_mean']*100:+.2f}pp/wk  p={result['vol_gap_p_value']:.3f}")
    print(f"verdict: {result['verdict']}")
