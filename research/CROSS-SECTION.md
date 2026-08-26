# Cross-sectional test: relative positioning vs relative returns

Generated 2026-08-26.

## Why this test

The time-series study (FINDINGS.md) was starved of sample: positioning is so persistent that 40 years yields roughly 8 independent episodes per commodity. This test uses the portfolio-week as the observation instead, so the whole cross-section contributes once per week: **1,348 weekly observations** (2000-03-07 to 2025-12-23), averaging 23.2 commodities per week.

## Headline

The equal-weighted tercile spread earns +5.9% annualised at p=0.047. **That number is not a positioning effect.** Two independent tests below say what it actually is.

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

## Test 1: is there any rank information? (information coefficient)

The tercile spread is a magnitude-weighted statistic, so a handful of large returns can carry it. The information coefficient asks the same question in ranks -- each week, the Spearman correlation across the cross-section between crowding percentile and forward return. Ranking caps how much any single extreme return can contribute, so a genuine monotonic ordering survives here and a magnitude artifact does not. This is the standard factor-research diagnostic (Grinold's fundamental law: IR = IC x sqrt(breadth)).

| Metric | Value |
|---|---|
| Weeks | 1,347 |
| Mean IC | -0.0049 |
| IC standard deviation | 0.241 |
| Implied annual IR | -0.15 |
| p-value | 0.418 |

The IC carries the right sign but is indistinguishable from zero (p=0.42). **There is no monotonic cross-sectional ordering to find.** Whatever the tercile spread is measuring, it is not a consistent tendency for less-crowded commodities to out-rank more-crowded ones.

## Test 2: is the spread secretly a volatility bet?

Equal weighting sizes positions by dollar, not by risk, so a commodity with twice the volatility contributes twice the risk. If crowding correlates with volatility, the long-short spread carries a volatility exposure that has nothing to do with positioning.

| Metric | Value |
|---|---|
| Weeks | 1,315 |
| Mean trailing-vol gap, long leg minus short leg | +0.37pp/wk |
| p-value | 0.000 |
| Weeks the long leg is the more volatile | 69% |

The least-crowded leg is systematically the more volatile one (+0.37pp per week, p=0.000, in 69% of weeks). The portfolio was long high-vol and short low-vol commodities most of the time. There is a mechanism for it rather than just a correlation: volatility clusters, and speculators cut net length *after* adverse moves, so a low crowding percentile mechanically coincides with elevated trailing volatility. The signal is partly a lagged volatility proxy. The risk-parity row in the robustness table below removes this exposure.

## Robustness

Each row is tagged with what it can actually falsify, which the first version of this table got wrong. See "Reading a robustness table" below.

| Specification | Tests | Weeks | Mean weekly | Annualised | p | What it tests |
|---|---|---|---|---|---|---|
| Vol-scaled legs (risk parity) | effect size | 1,315 | +0.096% | +5.0% | 0.146 | removes the volatility tilt; the control row below is the matched comparison |
| Equal-weighted, same weeks as above | effect size | 1,315 | +0.126% | +6.6% | 0.030 | control for the risk-parity row, so the two differ only by weighting |
| Ex roll-contaminated (3 contracts) | effect size | 1,348 | +0.121% | +6.3% | 0.037 | drops the series roll_check flags; tests the original prime suspect |
| Returns winsorised at +/-10% (4% of obs) | effect size | 1,348 | +0.097% | +5.1% | 0.058 | genuine outlier trim: it binds on few enough observations to stay comparable |
| Quintiles instead of terciles | power | 1,348 | +0.109% | +5.7% | 0.179 | a quintile leg holds ~4 names against a tercile's ~8, so it is less diversified and noisier; a flat mean with a worse p is expected |
| First half (2000-03 to 2013-01) | power | 674 | +0.110% | +5.7% | 0.179 | halving the sample multiplies the standard error by ~sqrt(2) |
| Second half (2013-01 to 2025-12) | power | 674 | +0.116% | +6.0% | 0.148 | same; compare the two halves' MEANS to each other, not their p-values to 0.05 |
| Returns clipped at +/-5% (19% of obs) | distorted | 1,348 | +0.035% | +1.8% | 0.384 | binds on too much of the data to be an outlier test; it compresses the whole distribution in the volatile half of the universe |

Of the 4 effect-size specifications, 2 clear p<0.05. The power-limited and distorted rows are reported for continuity but are not counted, because a larger p-value there is the arithmetically expected outcome and not evidence of anything.

## Reading a robustness table

This section exists because the first version of this analysis counted "0 of 5 specifications survive" and concluded the effect was fragile. The conclusion was right; three fifths of the reasoning was not, and the error is worth keeping visible because it is easy to repeat.

**A p-value is an effect size divided by a standard error.** A specification can raise a p-value by shrinking the numerator (real evidence against the effect) or by inflating the denominator (no evidence about the effect at all). A robustness table that only prints p-values cannot tell you which happened. Compare the *means*.

- **Quintiles instead of terciles.** The original comment claimed a monotonic signal should sharpen under a more extreme sort. Under a finer sort the mean spread should rise *and* the volatility should rise, because a quintile leg holds ~4 names against a tercile's ~8 and is that much less diversified. Which effect wins is an open question, so a worse p-value is not a falsification. The quintile mean came in flat against baseline, which is mild evidence against monotonicity -- and far weaker than the p-value degradation made it look.
- **Each half of the sample.** Halving the sample multiplies the standard error by about sqrt(2), so an effect at p=0.045 in full is *expected* to land near p=0.15 in each half. Demanding that both halves independently clear p<0.05 is a much higher bar than the full-sample test, not a robustness check. The right question is whether the two halves' estimates differ from *each other*; here they differ by 0.3% annualised, which is nothing. This is the Gelman-Stern point that a difference in significance is not significance in difference.
- **Clipping at +/-5%.** This binds on a large share of the observations, not a few outliers -- weekly moves above 5% are routine in natural gas, crude and cocoa. It compresses the whole distribution in the volatile half of the universe rather than trimming tails, so the resulting estimate is not comparable. The +/-10% winsorisation is the meaningful version and it leaves the estimate largely intact.

The specifications that *do* carry evidence are the ones that change the weighting or the universe while leaving the sample size alone: risk parity against its matched equal-weighted control, and the ex-roll-contaminated universe.

## Jackknife: does one contract carry the result?

The original table varied buckets, clipping and time, but never cross-section membership -- the axis a 24-name portfolio is most exposed on. Each row drops one commodity and re-runs.

| Dropped | Weeks | Mean weekly | Annualised | p |
|---|---|---|---|---|
| Coffee | 1,339 | +0.106% | +5.5% | 0.083 |
| Lean Hogs | 1,348 | +0.122% | +6.3% | 0.048 |
| Wheat (SRW) | 1,348 | +0.125% | +6.5% | 0.043 |
| Gold | 1,348 | +0.126% | +6.6% | 0.041 |
| Silver | 1,348 | +0.125% | +6.5% | 0.038 |
| Copper | 1,348 | +0.127% | +6.6% | 0.038 |
| Class III Milk | 1,348 | +0.134% | +7.0% | 0.034 |
| WTI Crude | 1,348 | +0.131% | +6.8% | 0.032 |
| Rough Rice | 1,339 | +0.132% | +6.9% | 0.030 |
| Platinum | 1,339 | +0.133% | +6.9% | 0.026 |
| Soybean Meal | 1,348 | +0.139% | +7.2% | 0.025 |
| Soybean Oil | 1,339 | +0.139% | +7.3% | 0.024 |
| Palladium | 1,339 | +0.146% | +7.6% | 0.021 |
| Feeder Cattle | 1,348 | +0.143% | +7.4% | 0.021 |
| RBOB Gasoline | 1,348 | +0.137% | +7.1% | 0.019 |
| Cotton | 1,339 | +0.154% | +8.0% | 0.017 |
| NY Harbor ULSD | 1,348 | +0.148% | +7.7% | 0.013 |
| Wheat (HRW) | 1,348 | +0.163% | +8.5% | 0.013 |
| Live Cattle | 1,348 | +0.150% | +7.8% | 0.012 |
| Natural Gas | 1,348 | +0.151% | +7.9% | 0.011 |
| Soybeans | 1,348 | +0.155% | +8.1% | 0.011 |
| Corn | 1,348 | +0.164% | +8.5% | 0.009 |
| Cocoa | 1,339 | +0.170% | +8.8% | 0.008 |
| Sugar | 1,339 | +0.178% | +9.2% | 0.004 |

1 of 24 single drops push p above 0.05. Note the mechanical artifact: dropping any name takes the tercile cut from 24//3 = 8 to 23//3 = 7, so both legs get slightly more extreme and most drops nudge the mean up. Compare the drops against each other, not against the 24-name baseline.

## Roll contamination: the suspect that was wrong

Yahoo's continuous front-month series is not roll-adjusted, so every contract roll injects a price gap that nobody earned. That was named here as the leading explanation for the residual effect, and as the highest-value next step. It was the wrong suspect.

`roll_check.py` localises the contamination by bucketing weekly |return| by day-of-month: a calendar-fixed expiry makes a roll gap land in a consistent bucket. Three of 24 series are affected -- Class III Milk (2.97x, and its peak bucket matches its month-end settlement), Lean Hogs (1.51x, matching its ~10th-business-day expiry) and Live Cattle (1.38x, last business day). The rest of the universe is flat to within 1.25x, and for monthly-cycle contracts like crude the test has real power and finds nothing.

Removing the three contaminated contracts makes the raw effect **stronger**, not weaker (see the robustness table). Roll gaps were adding noise, not manufacturing the result. A roll-adjusted price feed would sharpen this analysis; it would not change its conclusion, so it is no longer the priority it was recorded as.

## Reading this honestly

- price-only returns, excludes roll yield and costs; measures information, not tradability. Roll yield is the dominant term in real commodity futures returns and is entirely absent here, so the annualised figure is not a backtest of a strategy.
- The portfolio is formed on the prior week's signal and held the following week. CFTC publishes Friday for Tuesday's positions, so the real information lag is longer than modelled; this is generous to the signal, not conservative.
- Inference uses a stationary block bootstrap (mean block 13 weeks) because the weekly spread series is autocorrelated. An i.i.d. t-test on the same data would report a smaller p-value and would be wrong.
- Trailing volatility for the risk-parity spec uses the 52 weeks strictly before entry. Full-sample volatility would be look-ahead bias of exactly the kind point-in-time percentiles exist to avoid, and measuring it (2026-08-26) shows where the damage lands: the point ESTIMATE is unchanged (+0.0959% vs +0.0964% per week), because ~81% of the leg vol gap is a durable cross-sectional ranking that a static estimate still sees. What changes is the standard error -- a rolling 1/vol scaler injects estimation noise and amplifies weeks whose trailing window happened to be low (18.5% vs 16.5% annualised) -- so full-sample vol would have reported this spec at p=0.084 rather than 0.142 and made the volatility tilt look like a weaker explanation than it is. The lesson is the same one the robustness table teaches: a specification can move a p-value without touching the effect.
- Losing significance is not the same as demonstrating zero. Risk parity moves the point estimate by roughly a quarter, which on its own would be suggestive rather than conclusive. What makes the reading decisive is that three independent angles agree: no rank information, a highly significant volatility tilt in the legs, and the 20 largest weeks by magnitude netting -20.8% against a series total of +152.6% -- so the effect comes from the rest of the sample, not from a handful of weeks.
