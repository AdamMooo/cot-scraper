# Cross-sectional test: relative positioning vs relative returns

Generated 2026-08-25.

## Why this test

The time-series study (FINDINGS.md) was starved of sample: positioning is so persistent that 40 years yields roughly 8 independent episodes per commodity. This test uses the portfolio-week as the observation instead, so the whole cross-section contributes once per week: **1,348 weekly observations** (2000-03-07 to 2025-12-23), averaging 23.2 commodities per week.

## Result

**Nominally significant, but fragile.** The baseline spec clears p<0.05, yet only 0 of 5 robustness specifications do. Treat this as "not established", not as a finding.

| Metric | Value |
|---|---|
| Portfolio | equal-weighted terciles, long lowest positioning percentile, short highest |
| Holding period | 1 week |
| Weekly observations | 1,348 |
| Mean weekly spread | +0.113% |
| 95% CI (block bootstrap) | +0.005% to +0.227% |
| p-value | 0.047 |
| Positive weeks | 50.4% |
| Annualised spread | +5.9% |
| Annualised vol | 18.0% |
| Return/vol ratio | 0.33 |

## Robustness

The baseline number above is one specification. These are the checks that decide whether it means anything.

| Specification | Weeks | Mean weekly | Annualised | p | What it tests |
|---|---|---|---|---|---|
| Quintiles instead of terciles | 1,348 | +0.109% | +5.7% | 0.174 | a monotonic signal should sharpen, not blur, under a more extreme sort |
| Weekly returns clipped at +/-10% | 1,348 | +0.097% | +5.1% | 0.057 | tests whether a few large moves carry the result |
| Weekly returns clipped at +/-5% | 1,348 | +0.035% | +1.8% | 0.381 | same, more aggressively |
| First half (2000-03 to 2013-01) | 674 | +0.110% | +5.7% | 0.187 | out-of-sample stability |
| Second half (2013-01 to 2025-12) | 674 | +0.116% | +6.0% | 0.140 | out-of-sample stability |

## Reading this honestly

- price-only returns, excludes roll yield and costs; measures information, not tradability. Roll yield is the dominant term in real commodity futures returns and is entirely absent here, so the annualised figure is not a backtest of a strategy.
- The portfolio is formed on the prior week's signal and held the following week. CFTC publishes Friday for Tuesday's positions, so the real information lag is longer than modelled; this is generous to the signal, not conservative.
- Inference uses a stationary block bootstrap (mean block 13 weeks) because the weekly spread series is autocorrelated. An i.i.d. t-test on the same data would report a smaller p-value and would be wrong.
- The effect shrinking sharply when weekly returns are clipped means it lives in the tails. Two candidate explanations, and they are not distinguishable with this data: a genuine premium for bearing spike risk, or artifacts in Yahoo's front-month continuous series, which is not roll-adjusted, so every roll injects a price gap that is not a real return. Since term structure and positioning are correlated, roll artifacts would not wash out at random. Resolving this needs a roll-adjusted or roll-aware return series, which is the single highest-value next step.
- If the CI straddles zero, or the robustness table mostly fails, the honest conclusion is that this dataset does not establish a positioning-based cross-sectional signal, which is consistent with the time-series result and with the literature.
