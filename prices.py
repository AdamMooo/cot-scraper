"""
Weekly futures price, from Yahoo Finance's public (unofficial, no API key)
chart endpoint. This exists so the report can show what price actually did
over the same week a positioning change covers -- comparing the two is the
actual point of this tool, not positioning in isolation.

MARKET_TICKERS is deliberately an allow-list, not a filter applied after the
fact: only base commodity names with a stable, liquid, publicly quoted
futures ticker are in it, matched against the market name's portion before
" - <exchange>". Everything CFTC lists that isn't a recognizable benchmark
commodity (rates, FX, equity indices, crypto, thin basis/power/RIN/REC
contracts) is simply absent, which is what keeps the weekly report to
markets worth reading about instead of CFTC's full ~370-line universe.
Verified against Yahoo on 2026-08-25; a ticker that stops resolving just
drops that one market from price comparison (see price_change), it doesn't
break the run.

Public interface:
    MARKET_TICKERS      -- {base market name: Yahoo Finance ticker}
    ticker_for(market)   -> ticker | None
    daily_closes(ticker) -> {date_str: close}
    price_change(closes, as_of, prior_as_of) -> (latest_close, pct_change) | None
"""

from datetime import date, datetime, timedelta, timezone

from http_client import get_session

MARKET_TICKERS: dict[str, str] = {
    "CORN": "ZC=F",
    "SOYBEANS": "ZS=F",
    "SOYBEAN MEAL": "ZM=F",
    "SOYBEAN OIL": "ZL=F",
    "WHEAT-SRW": "ZW=F",
    "WHEAT-HRW": "KE=F",
    "ROUGH RICE": "ZR=F",
    "COTTON NO. 2": "CT=F",
    "SUGAR NO. 11": "SB=F",
    "COCOA": "CC=F",
    "COFFEE C": "KC=F",
    "LEAN HOGS": "HE=F",
    "LIVE CATTLE": "LE=F",
    "FEEDER CATTLE": "GF=F",
    "CRUDE OIL, LIGHT SWEET-WTI": "CL=F",
    "NAT GAS NYME": "NG=F",
    "HENRY HUB": "NG=F",
    "GASOLINE RBOB": "RB=F",
    "NY HARBOR ULSD": "HO=F",
    "GOLD": "GC=F",
    "MICRO GOLD": "GC=F",
    "SILVER": "SI=F",
    "COPPER- #1": "HG=F",
    "PLATINUM": "PL=F",
    "PALLADIUM": "PA=F",
    "MILK, Class III": "DC=F",
}


def ticker_for(market: str) -> str | None:
    """market is the full CFTC name, e.g. "CORN - CHICAGO BOARD OF TRADE"."""
    base = market.rsplit(" - ", 1)[0]
    return MARKET_TICKERS.get(base)


def daily_closes(ticker: str, days: int = 120) -> dict[str, float]:
    """Return {ISO date: close} for the last `days` calendar days, empty on failure."""
    try:
        resp = get_session().get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
            params={"range": f"{days}d" if days <= 60 else "6mo", "interval": "1d"},
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
    except Exception:
        return {}

    out: dict[str, float] = {}
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        day = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        out[day] = close
    return out


def price_change(closes: dict[str, float], as_of: str, prior_as_of: str) -> tuple[float, float] | None:
    """Latest close at/before as_of, and its % change from the close at/before prior_as_of.

    COT as_of dates are Tuesdays and almost always trading days, but a
    market holiday can shift things by a day, so this looks back up to a
    week for the nearest available close rather than requiring an exact
    date match.
    """
    latest = _closest_close(closes, as_of)
    prior = _closest_close(closes, prior_as_of)
    if latest is None or prior is None or prior == 0:
        return None
    return latest, (latest - prior) / prior * 100


def _closest_close(closes: dict[str, float], target: str) -> float | None:
    target_date = date.fromisoformat(target)
    for back in range(8):
        day = (target_date - timedelta(days=back)).isoformat()
        if day in closes:
            return closes[day]
    return None
