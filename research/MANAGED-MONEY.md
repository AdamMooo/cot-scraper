# Managed Money: what the data can support

Generated 2026-08-26. Report: Disaggregated Report (Futures Only), Managed Money.

This is the measure-before-you-model step, not the test. Two previous attempts in this repo (`study.py`, `cross_section.py`) each died on a problem that was cheap to measure up front and expensive to find afterwards, so this file establishes what the panel can support before any signal is ranked.

## Data verification

- Managed Money long/short are columns **13/14**, not the legacy report's 8/9 -- 8/9 here are Producer/Merchant, so reusing the legacy indices would have analysed commercial hedgers under a Managed Money label. Same indices in all 17 year-files, 191 columns each.
- The 2010-2012 files **declare** column 2 as `Report_Date_as_MM_DD_YYYY` while every value in them is ISO `YYYY-MM-DD`. The header label is wrong; the data is not. Coding to the declared name yields a parser that rejects valid data.
- History runs 2010-01-05 to 2026-08-18 -- it starts in 2010, not 2009, because CFTC's per-year archive for this prefix begins there even though the report itself launched in 2009.
- `contracts.py`'s rename chains work unchanged: 24 of 24 commodities stitch, out of 843 markets in the file.

## Finding 1: the level is hopeless, the flow is not

| Variable | Mean AR(1) | Effective independent obs per commodity |
|---|---|---|
| Net Managed Money / OI, level | +0.968 | 13 |
| Weekly change in that ratio (flow) | +0.268 | 475 |

Effective n uses the standard AR(1) adjustment n(1-rho)/(1+rho). The level figure is an independent confirmation, from a different direction, of the "3-12 independent episodes per commodity" arithmetic that explains every null in this repo: at rho=0.97, 836 weeks of history are worth about 13 observations. Differencing destroys that persistence and multiplies the effective sample by roughly 36x.

**This is the argument for testing flow rather than re-running the level test on a cleaner proxy.** A better speculation measure does not fix a sample-size problem; differencing does.

## Finding 2: flow's booby trap is short-term reversal, not the volatility tilt

| Correlation | Mean across commodities |
|---|---|
| Managed Money flow vs **same**-week return | +0.133 |
| Managed Money flow vs **next**-week return | -0.030 |

Flow is contemporaneously correlated with return at +0.133: managed money adds length in weeks when price rose. That is the documented mechanism, not an artifact -- and it is exactly what makes a flow signal dangerous. Weekly commodity returns mean-revert, so any flow signal inherits short-term reversal for free and will present as a positioning discovery.

Against the next week's return the correlation is -0.030, negative in 18 of 24 commodities -- a fair coin gives a split that lopsided or worse 2.3% of the time. The sign consistency is the more interesting half of that: the mean magnitude is far too small to accept on the evidence of a raw tercile spread, but a consistent sign across commodities that are not the same trade is what makes it worth testing properly at all.

## What the actual test therefore has to include

1. Rank on flow, cross-sectionally, with the one-week publication entry lag -- CFTC is as-of Tuesday, published Friday, and `cross_section.py` measured that shortcut as worth a quarter of its raw effect.
2. **Flow orthogonalised against the same week's own return**, as a spec of its own. This is the control specific to flow, and neither previous study needed it.
3. **A head-to-head against pure short-term reversal** -- rank on lagged return alone, no CFTC data involved. If reversal does as well, the positioning column added nothing, and that is the result.
4. Information coefficient and risk-parity legs reported alongside the raw spread from the start, per CLAUDE.md. A cleaner speculation proxy is if anything more likely to correlate with volatility than the legacy bucket was.

## Per commodity

| Commodity | Weeks | AR(1) level | AR(1) flow | Eff. n level | Eff. n flow | Flow vs same-wk | Flow vs next-wk |
|---|---|---|---|---|---|---|---|
| Corn | 836 | +0.979 | +0.302 | 9 | 448 | +0.125 | +0.022 |
| Soybeans | 836 | +0.974 | +0.261 | 11 | 489 | +0.178 | +0.062 |
| Soybean Oil | 836 | +0.964 | +0.312 | 15 | 437 | +0.213 | -0.031 |
| Soybean Meal | 836 | +0.977 | +0.352 | 10 | 401 | +0.210 | +0.019 |
| Wheat (SRW) | 836 | +0.961 | +0.158 | 16 | 607 | +0.149 | -0.019 |
| Wheat (HRW) | 836 | +0.982 | +0.363 | 8 | 390 | +0.159 | -0.025 |
| Rough Rice | 836 | +0.962 | +0.380 | 16 | 375 | +0.032 | -0.105 |
| Cotton | 836 | +0.978 | +0.276 | 9 | 474 | +0.067 | -0.042 |
| Sugar | 836 | +0.980 | +0.329 | 8 | 421 | +0.113 | -0.076 |
| Coffee | 836 | +0.984 | +0.312 | 7 | 438 | +0.180 | -0.045 |
| Cocoa | 836 | +0.979 | +0.298 | 9 | 452 | +0.079 | -0.057 |
| Live Cattle | 836 | +0.977 | +0.362 | 10 | 391 | +0.055 | +0.000 |
| Feeder Cattle | 836 | +0.978 | +0.275 | 9 | 475 | +0.071 | -0.001 |
| Lean Hogs | 836 | +0.960 | +0.342 | 17 | 409 | +0.118 | -0.012 |
| Class III Milk | 836 | +0.970 | +0.317 | 13 | 433 | +0.133 | +0.156 |
| WTI Crude | 836 | +0.948 | +0.160 | 22 | 604 | +0.205 | +0.008 |
| Natural Gas | 836 | +0.978 | +0.242 | 9 | 509 | +0.182 | -0.044 |
| NY Harbor ULSD | 835 | +0.960 | +0.186 | 17 | 573 | +0.051 | -0.061 |
| RBOB Gasoline | 489 | +0.929 | +0.166 | 18 | 349 | +0.073 | -0.077 |
| Gold | 836 | +0.962 | +0.182 | 16 | 578 | +0.183 | -0.056 |
| Silver | 836 | +0.942 | +0.231 | 25 | 521 | +0.183 | -0.051 |
| Copper | 836 | +0.953 | +0.225 | 20 | 528 | +0.151 | -0.043 |
| Platinum | 836 | +0.966 | +0.194 | 15 | 564 | +0.178 | -0.073 |
| Palladium | 836 | +0.992 | +0.212 | 3 | 542 | +0.108 | -0.179 |
