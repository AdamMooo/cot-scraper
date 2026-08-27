# Managed Money flow: the cross-sectional test

Generated 2026-08-27.

## The question

Does Managed Money FLOW rank next week's relative returns, beyond what the same week's price move already tells you? Portfolio: equal-weighted terciles, long lowest-signal, short highest-signal, 1-week entry lag, 1-week hold. Sign convention: a price-pressure effect (heavy spec inflow -> weaker next week) shows as a positive spread and a negative IC.

**574 portfolio-weeks**, 2014-12-30 to 2025-12-23, averaging 23.4 commodities per week. The 260-week percentile warmup is spent inside the 2010-start Managed Money history, which is why the sample starts ~2015 rather than 2010.

## Head-to-head: the three specs that decide it

| Signal | Weeks | Mean weekly | Annualised | p |
|---|---|---|---|---|
| Managed Money flow | 574 | +0.067% | +3.5% | 0.469 |
| Pure short-term reversal (no CFTC data) | 574 | +0.396% | +20.6% | 0.000 |
| Flow orthogonalised vs formation-week return | 574 | +0.066% | +3.4% | 0.539 |

The flow and reversal spread series correlate at only +0.05 week to week: the +0.133 contemporaneous flow/return correlation is too weak, once pushed through within-commodity percentiles and tercile cuts, to make the two portfolios overlap much. So the orthogonalisation barely changes flow -- and it did not need to, because flow has nothing to remove reversal FROM. Both flow rows are flat before and after the control.

## Rank information coefficient

Per-week Spearman correlation between signal and forward return; negative is the effect's sign. Ranking caps any single week's contribution, so a genuine ordering survives here and a magnitude artifact does not.

| Signal | Mean IC | p |
|---|---|---|
| Flow | +0.0002 | 0.987 |
| Reversal | -0.0236 | 0.031 |
| Orthogonalised flow | +0.0010 | 0.916 |

## Volatility tilt check

Trailing-vol gap between the flow portfolio's legs: +0.03pp/wk (p=0.535, long leg more volatile in 50% of weeks). Risk-parity legs: +1.9% annualised, p=0.725, against the matched equal-weighted control's +3.5%, p=0.478.

## The reversal side-finding, treated with the same suspicion

The benchmark that uses no CFTC data at all prints +20.6% annualised at p=0.000, and its IC (-0.0236, p=0.031) is modest next to that spread -- the same big-spread/small-IC shape that, in the legacy study, meant the money lived in magnitudes rather than ordering. Its own vol-tilt numbers: leg vol gap +0.02pp/wk (p=0.611); risk-parity legs +17.7% (p=0.003) against a matched equal-weighted +20.6% (p=0.000). Short-term reversal is also the strategy classically killed by transaction costs (weekly turnover approaches 100%) and inflated by measurement noise in closes. It is reported here as the yardstick flow failed against, not as a discovery -- promoting it to a finding would need the full cross_section.py treatment on its own terms, and that is a different project from 'does CFTC positioning data help'.

## Tail contribution

The 20 largest weeks by magnitude net +4.3% against a series total of +38.4%.

## Jackknife (baseline flow spread)

| Dropped | Weeks | Mean weekly | Annualised | p |
|---|---|---|---|---|
| Rough Rice | 574 | +0.007% | +0.3% | 0.953 |
| Live Cattle | 574 | +0.011% | +0.6% | 0.914 |
| Cocoa | 574 | +0.012% | +0.6% | 0.897 |
| NY Harbor ULSD | 574 | -0.017% | -0.9% | 0.870 |
| Palladium | 574 | -0.025% | -1.3% | 0.829 |
| Feeder Cattle | 574 | +0.026% | +1.4% | 0.798 |
| Wheat (SRW) | 574 | +0.024% | +1.2% | 0.796 |
| Coffee | 574 | +0.045% | +2.3% | 0.677 |
| Natural Gas | 574 | +0.055% | +2.9% | 0.622 |
| Soybean Oil | 574 | +0.050% | +2.6% | 0.609 |
| Sugar | 574 | +0.054% | +2.8% | 0.606 |
| Soybean Meal | 574 | +0.055% | +2.8% | 0.578 |
| RBOB Gasoline | 574 | +0.055% | +2.9% | 0.550 |
| Gold | 574 | +0.061% | +3.2% | 0.542 |
| Wheat (HRW) | 574 | +0.071% | +3.7% | 0.519 |
| Corn | 574 | +0.072% | +3.8% | 0.497 |
| Platinum | 574 | +0.068% | +3.5% | 0.490 |
| Lean Hogs | 574 | +0.065% | +3.4% | 0.488 |
| Copper | 574 | +0.082% | +4.2% | 0.405 |
| Cotton | 574 | +0.083% | +4.3% | 0.400 |
| Silver | 574 | +0.100% | +5.2% | 0.336 |
| Soybeans | 574 | +0.100% | +5.2% | 0.335 |
| WTI Crude | 574 | +0.101% | +5.3% | 0.330 |
| Class III Milk | 574 | +0.130% | +6.8% | 0.184 |

## Verdict

**no detectable cross-sectional information in Managed Money flow at all.**

Caveat: price-only returns, excludes roll yield and costs; measures information, not tradability.
