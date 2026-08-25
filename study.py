"""
Does extreme speculative positioning predict forward returns?

This is the research step the weekly email was missing. Instead of asserting
"crowded long, could unwind" (unfalsifiable), it measures what actually
happened after every historical instance of crowded positioning, so the
weekly report can cite a base rate instead of a narrative.

Method (standard-literature name: a conditional forward-return study, i.e.
an event study where the "event" is a positioning percentile crossing):

    1. Stitch each commodity's rename chain into one 40-year series
       (contracts.py) -- without this, percentiles are computed against
       fragments and every reading looks extreme.
    2. At each week t, rank net non-commercial positioning against ONLY the
       weeks up to t (expanding window). This is the point that kills most
       naive backtests: ranking 2005 against a distribution that includes
       2020 is look-ahead bias, and it inflates results in a way that never
       survives live use.
    3. Flag weeks in the top/bottom decile of that point-in-time
       distribution.
    4. Collapse consecutive flagged weeks into EPISODES and keep only each
       episode's first week. Positioning is a slow-moving stock variable, so
       "247 crowded weeks" may be a dozen distinct events; using weeks as
       observations would overstate the sample size by ~20x and, because
       overlapping forward windows share most of their price path, would
       inflate t-stats by roughly sqrt(horizon).
    5. Measure the forward return from each episode start over 4/13/26
       weeks, and compare to the unconditional mean over the same window.
    6. Test significance with a circular block bootstrap (block length =
       horizon), which preserves the return series' own autocorrelation
       under the null rather than assuming independence.
    7. Correct for multiple testing across commodities (Benjamini-Hochberg),
       because 24 commodities x 3 horizons x 2 tails is 144 tests and ~7
       will clear p<0.05 by chance alone.

Known limitations, stated rather than buried:
    - Price history starts mid-2000, so the tested window is ~26 years even
      though positioning goes back to 1986. Percentiles still use the full
      history; only the return measurement is capped.
    - "Non-commercial" is not a stable category. Index-fund participation
      grew sharply after 2004 and CFTC split the report in 2009 precisely
      because the legacy bucket had become a poor proxy for speculation.
      Pre- and post-2006 episodes are not strictly the same experiment.
    - Episodes cluster across correlated commodities (grains crowd together),
      so the pooled test's effective sample is smaller than its episode
      count. The distinct-quarter count is reported so this is visible.
    - The published literature on hedging pressure and COT-based timing
      mostly finds weak or no predictive power. A null result here is the
      expected outcome, not a bug.

Run:  python study.py          (writes research/forward_returns.json + FINDINGS.md)
"""

import bisect
import json
import random
import statistics
from datetime import date
from pathlib import Path

import analysis
import contracts
import prices

HORIZONS = (4, 13, 26)  # weeks: ~1 month, ~1 quarter, ~6 months
DECILE_HIGH = 90.0
DECILE_LOW = 10.0
_WARMUP_WEEKS = 260  # 5y of history before any percentile is emitted
_MIN_EPISODE_GAP = 26  # weeks clear of the bucket before a new episode counts
_BOOTSTRAP_ITERS = 2000
_SEED = 20260825

REPO_ROOT = Path(__file__).resolve().parent
RESEARCH_DIR = REPO_ROOT / "research"


def point_in_time_percentiles(values: list[float]) -> list[float | None]:
    """Percentile of each value against only the values at or before it.

    O(n log n) via an incrementally sorted history. Returns None for the
    warmup period, where a percentile would be computed against too few
    observations to mean anything.
    """
    out: list[float | None] = []
    history: list[float] = []
    for value in values:
        bisect.insort(history, value)
        if len(history) < _WARMUP_WEEKS:
            out.append(None)
        else:
            out.append(100.0 * bisect.bisect_right(history, value) / len(history))
    return out


def episode_starts(dates: list[str], flags: list[bool]) -> list[int]:
    """Indices of the first week of each distinct run of True flags.

    A run only counts as a new episode if the bucket was clear for
    _MIN_EPISODE_GAP weeks beforehand; otherwise a series oscillating around
    the decile boundary would manufacture dozens of pseudo-events.
    """
    starts = []
    last_flagged = -10**9
    for i, flag in enumerate(flags):
        if not flag:
            continue
        if i - last_flagged > _MIN_EPISODE_GAP:
            starts.append(i)
        last_flagged = i
    return starts


def _forward_returns(series, dates: list[str], horizon: int) -> list[float | None]:
    """Fractional price change from each week to `horizon` weeks later."""
    out: list[float | None] = []
    for i in range(len(dates)):
        j = i + horizon
        out.append(prices.pct_change(series, dates[i], dates[j]) if j < len(dates) else None)
    return out


def _block_bootstrap_p(pool: list[float], observed_mean: float, n: int, block: int, rng) -> float:
    """Two-sided p-value for `observed_mean` under a circular block bootstrap.

    Blocks preserve the local autocorrelation of the return series, so the
    null distribution reflects how extreme a mean of n observations can look
    purely from this series' own persistence.
    """
    if not pool or n <= 0:
        return float("nan")
    baseline = statistics.fmean(pool)
    gap = abs(observed_mean - baseline)
    size = len(pool)
    hits = 0
    for _ in range(_BOOTSTRAP_ITERS):
        drawn = []
        while len(drawn) < n:
            start = rng.randrange(size)
            drawn.extend(pool[(start + k) % size] for k in range(min(block, n - len(drawn))))
        if abs(statistics.fmean(drawn) - baseline) >= gap:
            hits += 1
    return hits / _BOOTSTRAP_ITERS


def _benjamini_hochberg(pvalues: list[float], alpha: float = 0.05) -> list[bool]:
    """Which p-values survive BH false-discovery-rate control at `alpha`."""
    indexed = sorted((p, i) for i, p in enumerate(pvalues) if p == p)  # drop NaN
    survive = [False] * len(pvalues)
    m = len(indexed)
    cutoff = 0
    for rank, (p, _) in enumerate(indexed, start=1):
        if p <= alpha * rank / m:
            cutoff = rank
    for rank, (_, idx) in enumerate(indexed, start=1):
        if rank <= cutoff:
            survive[idx] = True
    return survive


def _quarter(iso: str) -> str:
    return f"{iso[:4]}Q{(int(iso[5:7]) - 1) // 3 + 1}"


def _cluster_bootstrap_p(records: list[tuple[str, float]], rng) -> tuple[float, float]:
    """Mean excess return and its p-value, resampling whole calendar quarters.

    Per-commodity episode counts are far too small to test (3-12 events), so
    the only sample big enough to detect anything is the pool across all
    commodities. But pooling breaks independence a second way: grains crowd
    together, energy crowds together, so episodes in the same quarter are
    driven by the same macro event and are emphatically not independent
    draws. Resampling at the QUARTER level (all episodes in a drawn quarter
    move together) is what keeps the error bars honest -- an episode-level
    bootstrap here would understate them badly.
    """
    if not records:
        return float("nan"), float("nan")
    by_quarter: dict[str, list[float]] = {}
    for quarter, value in records:
        by_quarter.setdefault(quarter, []).append(value)
    quarters = list(by_quarter)
    observed = statistics.fmean([v for _, v in records])

    crossings = 0
    for _ in range(_BOOTSTRAP_ITERS):
        drawn: list[float] = []
        for _ in range(len(quarters)):
            drawn.extend(by_quarter[quarters[rng.randrange(len(quarters))]])
        # Fraction of resampled means on the opposite side of zero from the
        # observed mean; doubled for a two-sided test.
        if (statistics.fmean(drawn) <= 0) if observed > 0 else (statistics.fmean(drawn) >= 0):
            crossings += 1
    return observed, min(1.0, 2 * crossings / _BOOTSTRAP_ITERS)


def run() -> dict:
    rng = random.Random(_SEED)
    by_market = analysis.load_category_rows(REPO_ROOT / ".cot-cache" / "Legacy Report (Futures Only)")

    # (signal, horizon) -> [(quarter, excess return vs that commodity's own mean)]
    pooled: dict[tuple[str, int], list[tuple[str, float]]] = {}
    results = []
    for name, commodity in contracts.COMMODITIES.items():
        # Deciles are computed on net position as a share of open interest,
        # matching the weekly report. Ranking raw contract counts would let
        # multi-decade growth in market size masquerade as crowding.
        shares = contracts.net_share(contracts.stitch(by_market, commodity))
        if len(shares) < _WARMUP_WEEKS + max(HORIZONS) + 10:
            continue
        dates = [d for d, _ in shares]
        pcts = point_in_time_percentiles([v for _, v in shares])

        series = prices.weekly_closes(commodity.ticker)
        if not series:
            print(f"  no price history for {name} ({commodity.ticker}), skipping")
            continue

        for horizon in HORIZONS:
            fwd = _forward_returns(series, dates, horizon)
            # Only weeks with BOTH a usable percentile and a measurable
            # forward return are in the experiment at all.
            usable = [i for i in range(len(dates)) if pcts[i] is not None and fwd[i] is not None]
            if len(usable) < 100:
                continue
            pool = [fwd[i] for i in usable]
            usable_set = set(usable)

            for label, flags in (
                ("crowded_long", [pcts[i] is not None and pcts[i] >= DECILE_HIGH for i in range(len(dates))]),
                ("crowded_short", [pcts[i] is not None and pcts[i] <= DECILE_LOW for i in range(len(dates))]),
            ):
                starts = [i for i in episode_starts(dates, flags) if i in usable_set]
                if len(starts) < 3:
                    continue
                sample = [fwd[i] for i in starts]
                mean = statistics.fmean(sample)
                # De-mean by this commodity's own unconditional return so the
                # pooled test measures the *deviation* attributable to
                # crowding, not differences in baseline drift between
                # commodities.
                baseline = statistics.fmean(pool)
                pooled.setdefault((label, horizon), []).extend(
                    (_quarter(dates[i]), fwd[i] - baseline) for i in starts
                )
                # The mean-reversion hypothesis being tested: price falls
                # after crowded longs, rises after crowded shorts.
                if label == "crowded_long":
                    wins = sum(1 for r in sample if r < 0)
                else:
                    wins = sum(1 for r in sample if r > 0)
                results.append({
                    "commodity": name,
                    "sector": commodity.sector,
                    "ticker": commodity.ticker,
                    "signal": label,
                    "horizon_weeks": horizon,
                    "episodes": len(starts),
                    "first_episode": dates[starts[0]],
                    "last_episode": dates[starts[-1]],
                    "mean_fwd_return": mean,
                    "median_fwd_return": statistics.median(sample),
                    "unconditional_mean": statistics.fmean(pool),
                    "edge_vs_unconditional": mean - statistics.fmean(pool),
                    "reversion_hit_rate": wins / len(sample),
                    "p_value": _block_bootstrap_p(pool, mean, len(starts), horizon, rng),
                    "episode_quarters": len({dates[i][:4] + "Q" + str((int(dates[i][5:7]) - 1) // 3 + 1) for i in starts}),
                })
        print(f"  {name}: done")

    survive = _benjamini_hochberg([r["p_value"] for r in results])
    for r, s in zip(results, survive):
        r["survives_fdr_005"] = s

    pooled_results = []
    for (label, horizon), records in sorted(pooled.items()):
        mean_excess, p = _cluster_bootstrap_p(records, rng)
        if label == "crowded_long":
            wins = sum(1 for _, v in records if v < 0)
        else:
            wins = sum(1 for _, v in records if v > 0)
        pooled_results.append({
            "signal": label,
            "horizon_weeks": horizon,
            "episodes": len(records),
            "clusters_quarters": len({q for q, _ in records}),
            "mean_excess_return": mean_excess,
            "reversion_hit_rate": wins / len(records),
            "p_value_quarter_clustered": p,
        })

    return {
        "pooled": pooled_results,
        "generated": date.today().isoformat(),
        "method": "conditional forward-return study; point-in-time deciles; episode-level obs; circular block bootstrap; BH-FDR",
        "horizons_weeks": list(HORIZONS),
        "warmup_weeks": _WARMUP_WEEKS,
        "min_episode_gap_weeks": _MIN_EPISODE_GAP,
        "bootstrap_iters": _BOOTSTRAP_ITERS,
        "total_tests": len(results),
        "results": results,
    }


def _findings_markdown(out: dict) -> str:
    rows = sorted(out["results"], key=lambda r: r["p_value"])
    survivors = [r for r in rows if r["survives_fdr_005"]]
    nominal = [r for r in rows if r["p_value"] < 0.05]

    lines = [
        "# Does crowded COT positioning predict forward commodity returns?",
        "",
        f"Generated {out['generated']}. {out['total_tests']} tests "
        f"({len(contracts.COMMODITIES)} commodities x {len(out['horizons_weeks'])} horizons x 2 tails).",
        "",
        "## Headline",
        "",
        f"- **{len(nominal)}** tests reach nominal p<0.05. With {out['total_tests']} tests, "
        f"~{out['total_tests'] * 0.05:.0f} are expected by chance alone.",
        f"- **{len(survivors)}** survive Benjamini-Hochberg FDR control at 5%.",
        "",
        "Per-commodity episode counts are 3-12, so those tests have almost no power "
        "regardless of what is true. The pooled test below is the one with a real sample.",
        "",
        "## Pooled across all commodities",
        "",
        "Each episode's forward return is measured as a deviation from that commodity's own "
        "unconditional mean, then pooled. Inference resamples whole calendar quarters, because "
        "commodities crowd together (all grains at once) and episodes in the same quarter are "
        "not independent draws.",
        "",
        "| Signal | Horizon | Episodes | Distinct quarters | Mean excess return | Reversion hit rate | p (quarter-clustered) |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in out["pooled"]:
        lines.append(
            f"| {p['signal']} | {p['horizon_weeks']}w | {p['episodes']} | {p['clusters_quarters']} | "
            f"{p['mean_excess_return']*100:+.2f}% | {p['reversion_hit_rate']*100:.0f}% | "
            f"{p['p_value_quarter_clustered']:.3f} |")
    lines.append("")
    if survivors:
        lines += ["### Survives multiple-testing correction", "",
                  "| Commodity | Signal | Horizon | Episodes | Mean fwd | Uncond. | Edge | Reversion hit | p |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for r in survivors:
            lines.append(
                f"| {r['commodity']} | {r['signal']} | {r['horizon_weeks']}w | {r['episodes']} | "
                f"{r['mean_fwd_return']*100:+.1f}% | {r['unconditional_mean']*100:+.1f}% | "
                f"{r['edge_vs_unconditional']*100:+.1f}pp | {r['reversion_hit_rate']*100:.0f}% | {r['p_value']:.3f} |")
        lines.append("")
    else:
        lines += ["No test survives FDR correction. On this data, crowded positioning does not "
                  "predict forward returns at a level distinguishable from chance -- which is "
                  "consistent with the published literature on COT-based timing.", ""]

    lines += ["## All tests, most significant first", "",
              "| Commodity | Signal | Horizon | Episodes | Quarters | Mean fwd | Edge | Reversion hit | p | FDR |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(
            f"| {r['commodity']} | {r['signal']} | {r['horizon_weeks']}w | {r['episodes']} | "
            f"{r['episode_quarters']} | {r['mean_fwd_return']*100:+.1f}% | "
            f"{r['edge_vs_unconditional']*100:+.1f}pp | {r['reversion_hit_rate']*100:.0f}% | "
            f"{r['p_value']:.3f} | {'yes' if r['survives_fdr_005'] else 'no'} |")

    lines += ["", "## How to read this", "",
              "`Episodes` is the real sample size: consecutive crowded weeks collapsed into one "
              "event, requiring a 6-month clear gap to start a new one. `Quarters` shows how many "
              "distinct calendar quarters those episodes fall in -- if it is much lower than the "
              "episode count, the events are clustered and the effective sample is smaller still. "
              "`Edge` is the conditional mean minus the unconditional mean over the same window. "
              "`Reversion hit` is how often price moved *against* the crowd (down after crowded "
              "longs, up after crowded shorts); 50% is a coin flip. `p` comes from a circular "
              "block bootstrap that preserves the return series' autocorrelation.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    print("Running forward-return study ...")
    out = run()
    RESEARCH_DIR.mkdir(exist_ok=True)
    (RESEARCH_DIR / "forward_returns.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    (RESEARCH_DIR / "FINDINGS.md").write_text(_findings_markdown(out), encoding="utf-8")
    print(f"\n{out['total_tests']} tests written to research/")
