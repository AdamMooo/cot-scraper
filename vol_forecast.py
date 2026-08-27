"""
Does crowding forecast next week's realized volatility, beyond vol's own
persistence? The one open question the applications survey found unpublished
for commodities (research/APPLICATIONS.md, next-test #1).

Why the test is built this way:

  - The trap is documented in this repo's own results: specs cut length
    AFTER adverse moves and vol clusters, so the crowding percentile is
    partly a LAGGED vol proxy (the vol tilt that explained the entire
    cross-sectional "signal"). A raw correlation between crowding and future
    vol therefore rediscovers vol clustering. The only honest question is
    INCREMENTAL: does crowding add anything once future vol is first
    explained by vol's own history?
  - The baseline is HAR-style (Corsi 2009), adapted to the weekly COT grid:
    log RV regressed on its own last week, last ~month (4wk mean) and last
    ~quarter (13wk mean). HAR is the standard hard-to-beat RV forecaster;
    beating a weaker baseline would prove nothing.
  - Realized vol is built from DAILY closes inside each Tuesday-to-Tuesday
    COT week (sqrt of summed squared daily log returns, >= 3 returns
    required). Weekly bars cannot measure the vol OF a week.
  - Timing: the signal is the crowding percentile as of Tuesday dates[w]
    (published that Friday); the target is the vol of the FOLLOWING COT week
    dates[w+1] -> dates[w+2]; the HAR terms use realized vol through the week
    ending dates[w+1]. So the baseline is allowed MORE recent information
    than the signal -- conservative against crowding, same one-week entry
    lag as every other test in this repo.
  - Primary inference is a weekly pooled series: each week, the mean over
    commodities of z(HAR residual) * z(crowding), block-bootstrapped over
    weeks (mean block 13). Per-commodity partial correlations are reported
    with a sign test, but commodities share vol shocks, so the weekly pooled
    series is what respects the dependence structure.
  - Two signal forms, pre-specified: PRIMARY is the signed percentile
    (mechanism says LOW crowding follows washouts, so the expected sign is
    negative); SECONDARY is extremeness |pct-50| (either tail = elevated
    future vol). Only the primary counts toward the verdict; the secondary
    is reported to keep the forking path visible rather than silent.

Zero-vol weeks (Class III Milk sits pinned between monthly settlements) are
dropped because log(0) is undefined; milk contributes fewer rows, honestly.

Run:  python vol_forecast.py
"""

import bisect
import json
import math
import random
import statistics
from datetime import date
from pathlib import Path

import analysis
import contracts
import cross_section as xs
import prices
import study
from managed_money import _sign_test_p

_MIN_DAILY_RETURNS = 3
_MIN_ROWS = 200
_HAR_WEEK = 1
_HAR_MONTH = 4
_HAR_QUARTER = 13
_SEED = 20260827

REPO_ROOT = Path(__file__).resolve().parent
RESEARCH_DIR = REPO_ROOT / "research"


def _ols(X: list[list[float]], y: list[float]) -> tuple[list[float], list[float], float]:
    """Coefficients, residuals, R-squared via normal equations.

    k <= 5 and the regressors are logs of overlapping vol averages --
    correlated but far from collinear, so Gaussian elimination with partial
    pivoting is enough; no numpy in this repo.
    """
    k, n = len(X[0]), len(X)
    A = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    b = [sum(X[i][a] * y[i] for i in range(n)) for a in range(k)]
    for col in range(k):
        piv = max(range(col, k), key=lambda r: abs(A[r][col]))
        A[col], A[piv] = A[piv], A[col]
        b[col], b[piv] = b[piv], b[col]
        for r in range(col + 1, k):
            f = A[r][col] / A[col][col]
            for c in range(col, k):
                A[r][c] -= f * A[col][c]
            b[r] -= f * b[col]
    beta = [0.0] * k
    for r in range(k - 1, -1, -1):
        beta[r] = (b[r] - sum(A[r][c] * beta[c] for c in range(r + 1, k))) / A[r][r]
    resid = [y[i] - sum(X[i][c] * beta[c] for c in range(k)) for i in range(n)]
    ybar = statistics.fmean(y)
    sst = sum((v - ybar) ** 2 for v in y)
    return beta, resid, 1 - sum(v * v for v in resid) / sst if sst else 0.0


def _weekly_rv(daily: list[tuple[str, float]], dates: list[str]) -> list[float | None]:
    """rv[w] = realized vol of the COT week dates[w] -> dates[w+1].

    sqrt of summed squared daily log returns with the return dated by its
    own close date, so a week's vol uses exactly the closes inside it.
    """
    ds = [d for d, _ in daily]
    rets: list[float] = [0.0]
    for j in range(1, len(daily)):
        a, b = daily[j - 1][1], daily[j][1]
        rets.append(math.log(b / a) if a > 0 and b > 0 else 0.0)
    out: list[float | None] = []
    for w in range(len(dates) - 1):
        lo = bisect.bisect_right(ds, dates[w])
        hi = bisect.bisect_right(ds, dates[w + 1])
        chunk = rets[lo:hi]
        if len(chunk) < _MIN_DAILY_RETURNS:
            out.append(None)
        else:
            out.append(math.sqrt(sum(r * r for r in chunk)))
    return out


def _zscores(vals: list[float]) -> list[float] | None:
    m, s = statistics.fmean(vals), statistics.stdev(vals)
    return [(v - m) / s for v in vals] if s > 0 else None


def _build_panel():
    """Per commodity: aligned rows of (week, y, HAR terms, crowding pct)."""
    by_market = analysis.load_category_rows(REPO_ROOT / ".cot-cache" / "Legacy Report (Futures Only)")
    panels = {}
    for name, commodity in contracts.COMMODITIES.items():
        shares = contracts.net_share(contracts.stitch(by_market, commodity))
        if len(shares) < study._WARMUP_WEEKS + 20:
            continue
        dates = [d for d, _ in shares]
        pcts = study.point_in_time_percentiles([v for _, v in shares])
        daily = prices.daily_closes(commodity.ticker)
        if not daily:
            continue
        rv = _weekly_rv(daily, dates)

        weeks, y, X, sig = [], [], [], []
        for w in range(_HAR_QUARTER - 1, len(rv) - 1):
            window = rv[w - _HAR_QUARTER + 1: w + 1]
            target = rv[w + 1]
            if (pcts[w] is None or target is None or target <= 0
                    or any(v is None or v <= 0 for v in window)):
                continue
            weeks.append(dates[w])
            y.append(math.log(target))
            X.append([
                1.0,
                math.log(window[-_HAR_WEEK]),
                math.log(statistics.fmean(window[-_HAR_MONTH:])),
                math.log(statistics.fmean(window)),
            ])
            sig.append(pcts[w])
        if len(weeks) >= _MIN_ROWS:
            panels[name] = (weeks, y, X, sig)
    return panels


def run() -> dict:
    rng = random.Random(_SEED)
    panels = _build_panel()

    per_commodity = []
    pooled: dict[str, dict[str, tuple[float, float]]] = {}  # week -> name -> (z_resid, z_sig)
    for name, (weeks, y, X, sig) in panels.items():
        _, resid, r2_base = _ols(X, y)
        beta_aug, _, r2_aug = _ols([x + [s] for x, s in zip(X, sig)], y)

        partial = statistics.correlation(resid, sig)
        contemp = statistics.correlation(sig, [x[1] for x in X])  # pct vs log rv of its own week
        raw_lead = statistics.correlation(sig, y)

        zr, zs = _zscores(resid), _zscores(sig)
        if zr and zs:
            for w, a, b in zip(weeks, zr, zs):
                pooled.setdefault(w, {})[name] = (a, b)

        per_commodity.append({
            "commodity": name,
            "rows": len(y),
            "first_week": weeks[0],
            "last_week": weeks[-1],
            "har_r2": r2_base,
            "delta_r2": r2_aug - r2_base,
            "crowding_coef": beta_aug[4],
            "partial_corr": partial,
            "raw_corr_future_vol": raw_lead,
            "contemp_corr_current_vol": contemp,
        })

    # PRIMARY: weekly mean of z(resid)*z(pct) across commodities, block
    # bootstrap over weeks. This is the cross-product form of a pooled
    # partial correlation that respects the fact that commodities share
    # vol shocks within a week.
    weekly = [statistics.fmean(a * b for a, b in pooled[w].values())
              for w in sorted(pooled) if len(pooled[w]) >= xs._MIN_COMMODITIES]
    pooled_mean = statistics.fmean(weekly)
    pooled_p = xs._p_two_sided(weekly, rng)

    # SECONDARY: extremeness form, same machinery, plus per-commodity breadth
    # so a significant pooled number can be told apart from a few-name artifact.
    ext_pooled: dict[str, dict[str, tuple[float, float]]] = {}
    ext_partials: dict[str, float] = {}
    for name, (weeks, y, X, sig) in panels.items():
        _, resid, _ = _ols(X, y)
        ext = [abs(s - 50.0) for s in sig]
        ext_partials[name] = statistics.correlation(resid, ext)
        zr, ze = _zscores(resid), _zscores(ext)
        if zr and ze:
            for w, a, b in zip(weeks, zr, ze):
                ext_pooled.setdefault(w, {})[name] = (a, b)
    ext_weekly = [statistics.fmean(a * b for a, b in ext_pooled[w].values())
                  for w in sorted(ext_pooled) if len(ext_pooled[w]) >= xs._MIN_COMMODITIES]
    ext_mean = statistics.fmean(ext_weekly)
    ext_p = xs._p_two_sided(ext_weekly, rng)
    ext_positive = sum(1 for v in ext_partials.values() if v > 0)

    partials = [r["partial_corr"] for r in per_commodity]
    negative = sum(1 for v in partials if v < 0)

    effect = pooled_p < 0.05
    verdict = ("crowding carries a small amount of next-week vol information beyond HAR"
               if effect else
               "crowding adds nothing to a HAR baseline -- the crowding/vol link is entirely "
               "vol's own clustering, seen through a lagged proxy")

    return {
        "generated": date.today().isoformat(),
        "question": "Does the crowding percentile forecast next week's realized vol, "
                    "incrementally to a HAR baseline?",
        "commodities": len(per_commodity),
        "weekly_obs": len(weekly),
        "mean_har_r2": statistics.fmean(r["har_r2"] for r in per_commodity),
        "mean_delta_r2": statistics.fmean(r["delta_r2"] for r in per_commodity),
        "mean_partial_corr": statistics.fmean(partials),
        "partial_negative_count": negative,
        "partial_sign_test_p": _sign_test_p(negative, len(partials)),
        "mean_raw_corr_future_vol": statistics.fmean(r["raw_corr_future_vol"] for r in per_commodity),
        "mean_contemp_corr_current_vol": statistics.fmean(
            r["contemp_corr_current_vol"] for r in per_commodity),
        "pooled_weekly_mean": pooled_mean,
        "pooled_p_value": pooled_p,
        "extremeness_weekly_mean": ext_mean,
        "extremeness_p_value": ext_p,
        "extremeness_positive_count": ext_positive,
        "extremeness_sign_test_p": _sign_test_p(len(ext_partials) - ext_positive, len(ext_partials)),
        "extremeness_partials": ext_partials,
        "per_commodity": per_commodity,
        "verdict": verdict,
    }


def _markdown(r: dict) -> str:
    return "\n".join([
        "# Crowding and next week's volatility: the incremental test",
        "",
        f"Generated {r['generated']}.",
        "",
        f"{r['question']} The applications survey found no published commodity version of "
        "this test. Baseline: HAR-style regression of log realized vol on its own 1-week, "
        "4-week and 13-week history, per commodity, on the Tuesday COT grid, realized vol "
        "built from daily closes. The signal enters with the same one-week publication lag "
        "as every other test in this repo, and the baseline is allowed one week MORE "
        "information than the signal -- conservative against crowding.",
        "",
        "## The trap, displayed",
        "",
        "| Correlation with crowding percentile | Mean across commodities |",
        "|---|---|",
        f"| Current week's log RV (contemporaneous) | {r['mean_contemp_corr_current_vol']:+.3f} |",
        f"| Next week's log RV (raw, no baseline) | {r['mean_raw_corr_future_vol']:+.3f} |",
        f"| Next week's log RV, HAR residual (partial) | {r['mean_partial_corr']:+.3f} |",
        "",
        "The first two rows are the lagged-vol-proxy effect this repo already measured as "
        "the cross-sectional vol tilt: low crowding sits next to high vol, and vol "
        "persists, so crowding 'predicts' vol until vol's own history is allowed to speak. "
        "The third row is the question.",
        "",
        "## Results",
        "",
        "| Quantity | Value |",
        "|---|---|",
        f"| Commodities | {r['commodities']} |",
        f"| Pooled weekly observations | {r['weekly_obs']:,} |",
        f"| Mean HAR R-squared (baseline quality) | {r['mean_har_r2']:.3f} |",
        f"| Mean delta R-squared from adding crowding | {r['mean_delta_r2']:.4f} |",
        f"| Mean partial correlation | {r['mean_partial_corr']:+.4f} |",
        f"| Negative partials | {r['partial_negative_count']} of {r['commodities']} "
        f"(sign test p={r['partial_sign_test_p']:.3f}) |",
        f"| PRIMARY: pooled weekly z-product mean | {r['pooled_weekly_mean']:+.4f} "
        f"(p={r['pooled_p_value']:.3f}) |",
        f"| SECONDARY: extremeness form | {r['extremeness_weekly_mean']:+.4f} "
        f"(p={r['extremeness_p_value']:.3f}), positive in "
        f"{r['extremeness_positive_count']} of {r['commodities']} commodities "
        f"(sign test p={r['extremeness_sign_test_p']:.3f}) |",
        "",
        "Only the primary counts toward the verdict; the extremeness row is reported to "
        "keep the forking path visible rather than silent. If the extremeness form prints "
        "significant, note the scale before getting excited: a weekly z-product of ~0.02 is "
        "a partial correlation of ~0.02 against a baseline R-squared of "
        f"~{r['mean_har_r2']:.2f} -- statistically detectable in ~30k observations and "
        "economically negligible. Promoting it to a finding would need its own "
        "pre-specified test (breadth, subsample stability, and whether extremeness is "
        "proxying something simpler, like the persistence of trends).",
        "",
        "## Per commodity",
        "",
        "| Commodity | Rows | HAR R2 | dR2 | Coef | Partial corr | Raw lead | Contemp |",
        "|---|---|---|---|---|---|---|---|",
        *[f"| {row['commodity']} | {row['rows']:,} | {row['har_r2']:.3f} | "
          f"{row['delta_r2']:+.4f} | {row['crowding_coef']:+.5f} | {row['partial_corr']:+.3f} | "
          f"{row['raw_corr_future_vol']:+.3f} | {row['contemp_corr_current_vol']:+.3f} |"
          for row in r["per_commodity"]],
        "",
        "## Verdict",
        "",
        f"**{r['verdict']}.**",
        "",
    ])


if __name__ == "__main__":
    print("Running crowding -> volatility forecast test ...")
    result = run()
    RESEARCH_DIR.mkdir(exist_ok=True)
    (RESEARCH_DIR / "VOL-FORECAST.md").write_text(_markdown(result), encoding="utf-8")
    (RESEARCH_DIR / "vol_forecast.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\n{result['commodities']} commodities, {result['weekly_obs']:,} pooled weeks, "
          f"mean HAR R2 {result['mean_har_r2']:.3f}")
    print(f"contemporaneous corr {result['mean_contemp_corr_current_vol']:+.3f}   "
          f"raw lead {result['mean_raw_corr_future_vol']:+.3f}   "
          f"partial {result['mean_partial_corr']:+.4f}")
    print(f"PRIMARY pooled mean {result['pooled_weekly_mean']:+.4f}  p={result['pooled_p_value']:.3f}   "
          f"delta R2 {result['mean_delta_r2']:+.4f}")
    print(f"SECONDARY extremeness {result['extremeness_weekly_mean']:+.4f}  "
          f"p={result['extremeness_p_value']:.3f}  positive in "
          f"{result['extremeness_positive_count']}/{result['commodities']} "
          f"(sign p={result['extremeness_sign_test_p']:.3f})")
    print(f"verdict: {result['verdict']}")
