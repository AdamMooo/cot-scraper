"""
Is Yahoo's continuous front-month series contaminated by contract rolls?

Yahoo's `CL=F` is not a contract, it is a stitched series: it quotes whichever
contract is currently the front month. When the front rolls (Dec crude -> Jan
crude) the quote jumps from one contract's price to another's. Nobody earned
that jump -- it is the term-structure spread, not a return. In contango it
prints a spurious gain, in backwardation a spurious loss.

That matters more here than it would elsewhere, because hedging-pressure
theory (Keynes' normal backwardation) ties term structure to positioning:
speculators being net long is associated with backwardation. So the SIGN of
the fake jump correlates with the signal being tested, which makes roll gaps
a bias rather than noise -- they do not wash out.

The test: a contract's expiry is calendar-fixed, so a roll lands in a
consistent part of the month. Bucket weekly |returns| by the day-of-month
the bar ends on. A clean series is flat across buckets; a contaminated one
spikes in whichever bucket contains the front-month switch.

What it found on 2026-08-25 (26y of weekly bars, 24 commodities):

  - Class III Milk, 2.97x spike -- 0.35% mid-month against 6.06% at
    month-end. That series is a roll, not a market: milk's front contract
    settles to an announced monthly price so it sits pinned flat, then the
    series jumps contracts. Almost all of its "return" is fake.
  - Lean Hogs 1.51x (mid-month spike, matching the ~10th-business-day
    expiry) and Live Cattle 1.38x (month-end spike, matching the
    last-business-day expiry). Real, smaller, contamination.
  - Everything else <=1.25x, and the energy/metals/grains/softs complex
    <=1.17x. For monthly-cycle contracts like crude the test has real power
    (expiry is calendar-fixed around the 20th-22nd) and finds nothing.

So contamination is concentrated in three livestock/dairy contracts, not
spread across the universe -- which is why `cross_section` carries an
ex-contaminated robustness spec rather than this repo needing a paid
roll-adjusted price feed.

Two limits worth stating rather than hiding:

  - It only detects gaps large enough to beat weekly noise. Gold's ~0.3%
    bimonthly contango is invisible against 2.4% weekly vol, and should be:
    a gap that small cannot move a result.
  - It assumes the roll tracks expiry. If Yahoo switches on volume instead,
    the roll date wanders across buckets and the test loses power. A null
    here is therefore weaker evidence than a positive.

Run:  python roll_check.py
"""

import json
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path

import contracts

_BUCKETS = [(1, 7), (8, 14), (15, 21), (22, 28), (29, 31)]
# Below this the day-of-month profile is flat enough that any roll gap is
# small relative to weekly noise, i.e. too small to move a result.
_SUSPECT_RATIO = 1.30

REPO_ROOT = Path(__file__).resolve().parent
CACHE = REPO_ROOT / ".cot-cache" / "prices"


def _bucket(day: int) -> int:
    for i, (lo, hi) in enumerate(_BUCKETS):
        if lo <= day <= hi:
            return i
    return len(_BUCKETS) - 1


def day_of_month_profile(series: list[tuple[str, float]]) -> list[float] | None:
    """Mean |weekly return| per day-of-month bucket, or None if too short."""
    if len(series) < 200:
        return None
    buckets = defaultdict(list)
    for (_, prev), (end, close) in zip(series, series[1:]):
        if not prev:
            continue
        buckets[_bucket(date.fromisoformat(end).day)].append(abs((close - prev) / prev))
    if len(buckets) < len(_BUCKETS):
        return None
    return [statistics.fmean(buckets[i]) for i in range(len(_BUCKETS))]


def check_all() -> list[dict]:
    rows = []
    for name, commodity in contracts.COMMODITIES.items():
        cache_file = CACHE / f"{commodity.ticker.replace('=', '_')}.json"
        if not cache_file.exists():
            continue
        profile = day_of_month_profile(json.loads(cache_file.read_text()))
        if profile is None:
            continue
        ratio = max(profile) / statistics.median(profile)
        rows.append({
            "commodity": name,
            "ticker": commodity.ticker,
            "profile_pct": [p * 100 for p in profile],
            "peak_bucket": f"{_BUCKETS[profile.index(max(profile))][0]}-"
                           f"{_BUCKETS[profile.index(max(profile))][1]}",
            "spike_ratio": ratio,
            "suspect": ratio >= _SUSPECT_RATIO,
        })
    rows.sort(key=lambda r: -r["spike_ratio"])
    return rows


def suspect_commodities() -> set[str]:
    """Canonical names whose price series shows material roll contamination."""
    return {r["commodity"] for r in check_all() if r["suspect"]}


if __name__ == "__main__":
    rows = check_all()
    labels = " ".join(f"{lo}-{hi:>2}".rjust(7) for lo, hi in _BUCKETS)
    print(f"{'commodity':22}{labels}   ratio  peak")
    for r in rows:
        cells = " ".join(f"{p:7.2f}" for p in r["profile_pct"])
        flag = "  <-- suspect" if r["suspect"] else ""
        print(f"{r['commodity']:22}{cells} {r['spike_ratio']:7.2f}x {r['peak_bucket']:>6}{flag}")
    suspects = [r["commodity"] for r in rows if r["suspect"]]
    print(f"\n{len(suspects)} of {len(rows)} series suspect at >={_SUSPECT_RATIO}x: "
          f"{', '.join(suspects) if suspects else 'none'}")
