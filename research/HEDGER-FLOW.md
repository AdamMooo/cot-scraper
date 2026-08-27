# Commercial (hedger) flow: the KRT liquidity premium under a realistic lag

Generated 2026-08-27.

Does COMMERCIAL (hedger) flow rank next week's relative returns after a realistic publication lag, beyond what the formation week's return tells you? Portfolio: equal-weighted terciles, long highest hedger flow, short lowest, 1-week entry lag, 1-week hold. Sign convention: hedgers are contrarians, so the KRT effect prints as a POSITIVE spread and a POSITIVE IC (opposite to mm_flow's convention).

**1,080 portfolio-weeks**, 2005-04-19 to 2025-12-23, averaging 23.1 commodities per week. The panel starts ~2005 (price history from 2000 plus the formation-return percentile's 260-week warmup), which still overlaps most of KRT's own 1994-2014 sample.

## Head-to-head

| Signal | Weeks | Mean weekly | Annualised | p |
|---|---|---|---|---|
| Commercial (hedger) flow | 1,080 | +0.027% | +1.4% | 0.708 |
| Pure short-term reversal (no CFTC data) | 1,080 | +0.162% | +8.4% | 0.073 |
| Hedger flow orthogonalised vs formation-week return | 1,080 | +0.004% | +0.2% | 0.956 |

The hedger-flow and reversal spread series correlate at +0.12 week to week. Hedgers buy what just fell, so unlike Managed Money flow (mm_flow.py, +0.05), meaningful overlap is expected here -- the orthogonalised row is what separates 'hedger flow is reversal in disguise' from 'hedger flow adds something'.

## Rank information coefficient

| Signal | Mean IC | Effect sign | p |
|---|---|---|---|
| Hedger flow | -0.0008 | + | 0.914 |
| Reversal | -0.0054 | - | 0.566 |
| Orthogonalised hedger flow | -0.0021 | + | 0.778 |

## Volatility tilt check (hedger-flow portfolio)

Leg vol gap +0.04pp/wk (p=0.217). Risk-parity legs -0.2%/yr (p=0.967) vs matched equal-weight +1.2%/yr (p=0.756).

## Tail contribution

The 20 largest weeks by magnitude net -24.8% against a series total of +29.0%.

## Jackknife (baseline hedger-flow spread)

| Dropped | Weeks | Mean weekly | Annualised | p |
|---|---|---|---|---|
| Wheat (SRW) | 1,080 | +0.004% | +0.2% | 0.970 |
| Coffee | 1,071 | -0.005% | -0.2% | 0.956 |
| WTI Crude | 1,080 | +0.006% | +0.3% | 0.935 |
| Feeder Cattle | 1,080 | +0.007% | +0.4% | 0.927 |
| Live Cattle | 1,080 | +0.009% | +0.5% | 0.908 |
| Gold | 1,080 | +0.009% | +0.5% | 0.902 |
| Rough Rice | 1,071 | -0.010% | -0.5% | 0.902 |
| RBOB Gasoline | 1,080 | -0.013% | -0.7% | 0.869 |
| Silver | 1,080 | +0.019% | +1.0% | 0.830 |
| Cocoa | 1,071 | -0.018% | -0.9% | 0.830 |
| Soybean Meal | 1,080 | +0.016% | +0.8% | 0.817 |
| NY Harbor ULSD | 1,080 | +0.018% | +1.0% | 0.806 |
| Platinum | 1,071 | +0.019% | +1.0% | 0.805 |
| Sugar | 1,071 | +0.021% | +1.1% | 0.795 |
| Palladium | 1,071 | +0.024% | +1.2% | 0.795 |
| Lean Hogs | 1,080 | +0.021% | +1.1% | 0.789 |
| Cotton | 1,071 | +0.021% | +1.1% | 0.768 |
| Copper | 1,080 | +0.023% | +1.2% | 0.761 |
| Corn | 1,080 | +0.025% | +1.3% | 0.742 |
| Wheat (HRW) | 1,080 | +0.031% | +1.6% | 0.703 |
| Natural Gas | 1,080 | +0.037% | +1.9% | 0.674 |
| Soybean Oil | 1,071 | +0.037% | +1.9% | 0.634 |
| Soybeans | 1,080 | +0.038% | +2.0% | 0.631 |
| Class III Milk | 1,080 | +0.062% | +3.2% | 0.416 |

## Verdict

**no detectable information in commercial flow after a 1-week publication lag -- KRT's liquidity premium does not survive realistic entry in this universe.**

Caveat: price-only returns, excludes roll yield and costs; measures information, not tradability.
