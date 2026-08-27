"""
Weekly futures prices from Yahoo Finance's public chart endpoint (no API key).

Two traps worth knowing, both found by testing rather than assumed:

  - `range=max` with `interval=1wk` silently returns MONTHLY bars (267 bars
    for 26 years). Explicit `period1`/`period2` epochs are required to get
    real weekly data (1,362 bars for the same span).
  - History starts mid-2000 for these continuous contracts, not 1986. So
    while positioning goes back 40 years, any price-linked study is capped
    at ~26 years. That is the binding constraint on the forward-return work
    and it is reported rather than hidden.

Series are cached to .cot-cache/prices/ because the study re-runs often and
there is no reason to re-hit Yahoo for history that cannot change.

Public interface:
    weekly_closes(ticker)        -> [(iso_date, close)] ascending
    daily_closes(ticker)         -> [(iso_date, close)] ascending
    close_asof(series, date)     -> close on/just before date, or None
    pct_change(series, d0, d1)   -> fractional change between two dates
"""

import bisect
import json
import time
from datetime import date, datetime, timedelta, timezone

from http_client import get_session
from paths import support_dir

_EPOCH_START = int(datetime(1995, 1, 1, tzinfo=timezone.utc).timestamp())
# COT dates are Tuesdays and nearly always trading days, but a holiday or a
# thin week can leave no close exactly on the date, so a short look-back is
# allowed. Wider than this and we would be silently comparing stale prices.
_MAX_STALE_DAYS = 7


def _cache_dir():
    d = support_dir().parent / ".cot-cache" / "prices"
    d.mkdir(parents=True, exist_ok=True)
    return d


def weekly_closes(ticker: str, use_cache: bool = True) -> list[tuple[str, float]]:
    """Full weekly close history for a ticker, ascending by date."""
    return _closes(ticker, "1wk", f"{ticker.replace('=', '_')}.json", use_cache)


def daily_closes(ticker: str, use_cache: bool = True) -> list[tuple[str, float]]:
    """Full daily close history, for realized-vol work; weekly bars are too
    coarse to measure the vol of a single week."""
    return _closes(ticker, "1d", f"{ticker.replace('=', '_')}_daily.json", use_cache)


def _closes(ticker: str, interval: str, cache_name: str, use_cache: bool) -> list[tuple[str, float]]:
    cache_file = _cache_dir() / cache_name
    if use_cache and cache_file.exists():
        try:
            return [(d, c) for d, c in json.loads(cache_file.read_text())]
        except (OSError, ValueError):
            pass

    period2 = int((datetime.now(timezone.utc) + timedelta(days=1)).timestamp())
    try:
        resp = get_session().get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
            params={"period1": _EPOCH_START, "period2": period2, "interval": interval},
            timeout=45,
        )
        resp.raise_for_status()
        result = resp.json()["chart"]["result"][0]
        stamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
    except Exception:
        return []

    series = [
        (datetime.fromtimestamp(ts, timezone.utc).date().isoformat(), float(c))
        for ts, c in zip(stamps, closes)
        if c is not None
    ]
    series.sort()
    try:
        cache_file.write_text(json.dumps(series))
    except OSError:
        pass
    time.sleep(0.3)  # be polite to an endpoint that owes us nothing
    return series


def close_asof(series: list[tuple[str, float]], target: str) -> float | None:
    """Close on `target`, else the most recent close within _MAX_STALE_DAYS."""
    if not series:
        return None
    dates = [d for d, _ in series]
    i = bisect.bisect_right(dates, target) - 1
    if i < 0:
        return None
    found, close = series[i]
    if (date.fromisoformat(target) - date.fromisoformat(found)).days > _MAX_STALE_DAYS:
        return None
    return close


def pct_change(series: list[tuple[str, float]], start: str, end: str) -> float | None:
    """Fractional price change between two dates, or None if either is unavailable."""
    a = close_asof(series, start)
    b = close_asof(series, end)
    if a is None or b is None or a == 0:
        return None
    return (b - a) / a
