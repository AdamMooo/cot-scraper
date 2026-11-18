"""
The "Your portfolio" lens: positioning in the markets that actually move the
user's holdings, with the link itself measured rather than asserted.

Holdings: VFV (S&P 500, unhedged, in CAD), XDIV (Canadian quality dividend),
ZLB (Canadian low volatility), VEE (emerging markets), VIU (developed ex-North
America). All Canadian-listed, priced in CAD.

Two data sources:

  - Financial markets come from the Traders in Financial Futures (TFF) report,
    which splits speculators into asset managers (slow, structural money) and
    leveraged funds (hedge funds, CTAs, the basis trade). The legacy report
    lumps them into one "non-commercial" figure, which for Treasuries nets a
    long against a short and means nothing. TFF history in CFTC's per-year
    archive starts 2010-07-20, so these percentiles rank against ~16 years,
    not the commodity section's ~40.
  - Commodity drivers (crude, copper, gold) reuse analysis.Reading from the
    legacy report.

Markets are keyed on CFTC_Contract_Market_Code (column 3), not name. The code
survives CFTC's Feb 2022 renames (10-YEAR U.S. TREASURY NOTES -> UST 10Y NOTE,
U.S. DOLLAR INDEX -> USD INDEX; verified continuous across the boundary), so
no rename chain is needed here.

Which holdings each market reaches is not hardcoded. `_sensitivities` measures
it every run: trailing-156-week OLS of each holding's weekly return on the
S&P 500 plus that one market, on Tuesday-to-Tuesday closes so the window
matches the positioning window. The S&P row is the plain beta; every other
row is the beta holding the S&P constant, which is what isolates e.g. the
currency effect on VFV from "risk-on lifts everything". Measured 2020-2026
when this was written: CAD is VFV's second driver (-0.92, t=-35); 10Y
Treasuries reach ZLB (+0.48) but not XDIV; natural gas reached nothing, so it
is not in the driver list. Descriptive, like the rest of the report: a beta
says how holdings co-moved, not what moves next.

Public interface:
    load_tff(category_dir)            -> {code: [(as_of, oi, am_net, lev_net)]}
    build_section(tff, commodity_rows) -> markdown str
"""

import csv
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import prices

HOLDINGS = {"VFV": "VFV.TO", "XDIV": "XDIV.TO", "ZLB": "ZLB.TO", "VEE": "VEE.TO", "VIU": "VIU.TO"}

_CODE_COL, _DATE_COL, _OI_COL = 3, 2, 7
_AM_LONG, _AM_SHORT, _LEV_LONG, _LEV_SHORT = 11, 12, 14, 15

# (display name, CFTC contract code, Yahoo ticker, note). The note covers
# the sign conventions that otherwise mislead.
_TFF_MARKETS = [
    ("S&P 500", "13874A", "ES=F", ""),
    ("VIX", "1170E1", "^VIX", "leveraged funds are structurally short VIX futures; a low "
                              "percentile is a large short-volatility book"),
    ("US 10Y Treasury", "043602", "ZN=F", "futures price moves opposite to yields"),
    ("US 2Y Treasury", "042601", "ZT=F", "futures price moves opposite to yields"),
    ("Canadian dollar", "090741", "6C=F", "futures rise when CAD strengthens, which lowers "
                                          "unhedged foreign holdings in CAD terms"),
    ("Japanese yen", "097741", "6J=F", "the carry-trade funding currency; the Aug 2024 unwind "
                                       "started here"),
    ("Euro", "099741", "6E=F", ""),
    ("US dollar index", "098662", "DX-Y.NYB", ""),
]
_COMMODITY_DRIVERS = {"WTI Crude": "CL=F", "Copper": "HG=F", "Gold": "GC=F"}
_BENCHMARK = "ES=F"

_BETA_WEEKS = 156
_MIN_T = 2.0
_EXTREME_HIGH, _EXTREME_LOW = 90, 10
_MAX_GAP_DAYS = 10

TffHistory = dict[str, list[tuple[str, int, int, int]]]


def load_tff(category_dir: Path) -> TffHistory:
    """Every TFF *.txt in the folder, pooled per contract code, de-duplicated by date."""
    seen: dict[str, dict[str, tuple[int, int, int]]] = {}
    for txt_file in sorted(category_dir.glob("*.txt")):
        with txt_file.open(encoding="utf-8", errors="replace", newline="") as f:
            for row in csv.reader(f):
                try:
                    oi = int(row[_OI_COL])
                    am = int(row[_AM_LONG]) - int(row[_AM_SHORT])
                    lev = int(row[_LEV_LONG]) - int(row[_LEV_SHORT])
                except (ValueError, IndexError):
                    continue  # header row or malformed line
                seen.setdefault(row[_CODE_COL].strip(), {})[row[_DATE_COL].strip()] = (oi, am, lev)
    return {code: [(d, *v) for d, v in sorted(rows.items())] for code, rows in seen.items()}


def _pct(values: list[float], x: float) -> float:
    return 100.0 * sum(1 for v in values if v <= x) / len(values)


def _ordinal(n: float) -> str:
    i = round(n)
    return f"{i}{'th' if 11 <= i % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(i % 10, 'th')}"


@dataclass
class _Read:
    as_of: str
    prior: str | None  # the previous report date, when it is a true one-week gap
    weeks: int
    am_share: float
    am_pct: float
    lev_share: float
    lev_pct: float
    lev_change: int | None
    am_change: int | None
    oi_collapsing: bool


def _read(series: list[tuple[str, int, int, int]]) -> _Read | None:
    rows = [r for r in series if r[1]]
    if len(rows) < 2:
        return None
    (d0, oi0, am0, lev0), (d1, oi1, am1, lev1) = rows[-2], rows[-1]
    has_prior = (date.fromisoformat(d1) - date.fromisoformat(d0)).days <= _MAX_GAP_DAYS
    oi_moves = sorted((b[1] - a[1]) / a[1] for a, b in zip(rows, rows[1:]))
    collapsing = has_prior and len(oi_moves) >= 50 and (oi1 - oi0) / oi0 <= oi_moves[len(oi_moves) // 10]
    am, lev = [r[2] / r[1] for r in rows], [r[3] / r[1] for r in rows]
    return _Read(d1, d0 if has_prior else None, len(rows), am[-1], _pct(am, am[-1]), lev[-1], _pct(lev, lev[-1]),
                 lev1 - lev0 if has_prior else None, am1 - am0 if has_prior else None, collapsing)


def _tuesday_returns(ticker: str, since: str) -> dict[str, float]:
    """Tuesday-to-Tuesday returns from daily closes: the COT as-of window."""
    closes = prices.daily_closes(ticker)
    tues = [d for d, _ in closes if d >= since and date.fromisoformat(d).weekday() == 1]
    out = {}
    for a, b in zip(tues, tues[1:]):
        r = prices.pct_change(closes, a, b)
        if r is not None:
            out[b] = r
    return out


def _ols(y: list[float], xs: list[list[float]]) -> list[tuple[float, float]]:
    """(beta, t) per regressor, intercept included, solved by Gaussian elimination."""
    n, k = len(y), len(xs) + 1
    X = [[1.0] + [x[i] for x in xs] for i in range(n)]
    xtx = [[sum(r[a] * r[b] for r in X) for b in range(k)] for a in range(k)]
    inv = [row[:] + [float(a == b) for b in range(k)] for a, row in enumerate(xtx)]
    for c in range(k):
        p = max(range(c, k), key=lambda r: abs(inv[r][c]))
        inv[c], inv[p] = inv[p], inv[c]
        piv = inv[c][c]
        inv[c] = [v / piv for v in inv[c]]
        for r in range(k):
            if r != c:
                f = inv[r][c]
                inv[r] = [v - f * w for v, w in zip(inv[r], inv[c])]
    inv = [row[k:] for row in inv]
    beta = [sum(inv[a][b] * sum(X[i][b] * y[i] for i in range(n)) for b in range(k)) for a in range(k)]
    resid = [y[i] - sum(beta[a] * X[i][a] for a in range(k)) for i in range(n)]
    s2 = sum(e * e for e in resid) / (n - k)
    return [(beta[a], beta[a] / math.sqrt(s2 * inv[a][a])) for a in range(1, k)]


def _sensitivities(as_of: str, drivers: dict[str, str]) -> dict[str, dict[str, float | None]]:
    """{market: {holding: beta or None if |t| < _MIN_T}} over the trailing window."""
    since = date.fromisoformat(as_of).replace(year=date.fromisoformat(as_of).year - 4).isoformat()
    bench = _tuesday_returns(_BENCHMARK, since)
    held = {h: _tuesday_returns(t, since) for h, t in HOLDINGS.items()}
    out: dict[str, dict[str, float | None]] = {}
    for name, ticker in drivers.items():
        x = bench if ticker == _BENCHMARK else _tuesday_returns(ticker, since)
        out[name] = {}
        for h, y in held.items():
            weeks = sorted(set(y) & set(bench) & set(x))[-_BETA_WEEKS:]
            if len(weeks) < _BETA_WEEKS // 2:
                out[name][h] = None
                continue
            regs = [[bench[w] for w in weeks]] + ([] if x is bench else [[x[w] for w in weeks]])
            beta, t = _ols([y[w] for w in weeks], regs)[-1]
            out[name][h] = beta if abs(t) >= _MIN_T else None
    return out


def _reach(betas: dict[str, float | None]) -> str:
    hit = [f"{h} {b:+.2f}" for h, b in betas.items() if b is not None]
    return f" (moves {', '.join(hit)})" if hit else " (no measurable link to your holdings)"


def _flag(*pcts: float) -> str:
    return " **Extreme.**" if any(p >= _EXTREME_HIGH or p <= _EXTREME_LOW for p in pcts) else ""


def _days_back(iso: str, days: int) -> str:
    return date.fromordinal(date.fromisoformat(iso).toordinal() - days).isoformat()


def build_section(tff: TffHistory, commodity_rows: list) -> str:
    reads = {name: (r, ticker, note) for name, code, ticker, note in _TFF_MARKETS
             if (r := _read(tff.get(code, [])))}
    if not reads:
        return ""
    by_name = {c.name: c for c in commodity_rows}
    commodities = {n: t for n, t in _COMMODITY_DRIVERS.items() if n in by_name}
    anchor = reads.get("S&P 500", next(iter(reads.values())))[0]
    sens = _sensitivities(anchor.as_of, {n: t for n, (_, t, _) in reads.items() if n != "VIX"}
                          | commodities)

    week_moves = []
    if anchor.prior:
        for h, t in HOLDINGS.items():
            move = prices.pct_change(prices.daily_closes(t), anchor.prior, anchor.as_of)
            if move is not None:
                week_moves.append(f"{h} {move*100:+.1f}%")

    extremes = [n for n, (r, _, _) in reads.items() if _flag(r.am_pct, r.lev_pct)] \
        + [n for n in commodities if _flag(by_name[n].pct)]
    lead = (f"{len(extremes)} of the {len(reads) + len(commodities)} markets below are at a "
            f"positioning extreme: {', '.join(extremes)}." if extremes else
            "None of the markets that move your holdings are at a positioning extreme this week.")
    if week_moves:
        lead += f" Your holdings over the same Tuesday-to-Tuesday window: {', '.join(week_moves)}."
    lines = ["## Your portfolio", "", lead, ""]

    for name, (r, ticker, note) in reads.items():
        closes = prices.daily_closes(ticker)
        wk = prices.pct_change(closes, r.prior, r.as_of) if r.prior else None
        q = prices.pct_change(closes, _days_back(r.as_of, 91), r.as_of)
        bits = [f"leveraged funds {r.lev_share*100:+.1f}% of OI ({_ordinal(r.lev_pct)} pct"
                + (f", {r.lev_change:+,} contracts this wk" if r.lev_change is not None else "") + ")",
                f"asset managers {r.am_share*100:+.1f}% ({_ordinal(r.am_pct)} pct)"]
        if wk is not None:
            bits.append(f"price {wk*100:+.1f}% wk" + (f", {q*100:+.1f}% 13wk" if q is not None else ""))
        if r.oi_collapsing:
            bits.append("open interest contracting at a bottom-decile pace")
        reach = _reach(sens[name]) if name in sens else ""
        lines.append(f"- **{name}**{reach}: {', '.join(bits)}.{_flag(r.am_pct, r.lev_pct)}"
                     + (f" Note: {note}." if note else ""))
    for name in commodities:
        c = by_name[name]
        bits = [f"specs {c.share*100:+.1f}% of OI ({_ordinal(c.pct)} pct of {c.weeks:,}wk)"]
        if c.price_pct is not None:
            bits.append(f"price {c.price_pct*100:+.1f}% wk")
        if c.trend_13w is not None:
            bits.append(f"{c.trend_13w*100:+.1f}% 13wk")
        lines.append(f"- **{name}**{_reach(sens[name])}: {', '.join(bits)}.{_flag(c.pct)}")

    lines += ["", f"Percentiles rank net position as a share of open interest against each "
              f"market's own history ({anchor.weeks:,} weeks for the financial markets, whose CFTC "
              f"archive starts in 2010). \"Moves\" is each holding's measured weekly sensitivity "
              f"over the last {_BETA_WEEKS} weeks: % move per 1% move in that market, holding the "
              f"S&P 500 constant (the S&P figure itself is the plain beta). A holding is listed only "
              f"where the link is statistically distinct from zero (|t| >= {_MIN_T:.0f}).", ""]
    return "\n".join(lines)
