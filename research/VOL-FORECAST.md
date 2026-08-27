# Crowding and next week's volatility: the incremental test

Generated 2026-08-27.

Does the crowding percentile forecast next week's realized vol, incrementally to a HAR baseline? The applications survey found no published commodity version of this test. Baseline: HAR-style regression of log realized vol on its own 1-week, 4-week and 13-week history, per commodity, on the Tuesday COT grid, realized vol built from daily closes. The signal enters with the same one-week publication lag as every other test in this repo, and the baseline is allowed one week MORE information than the signal -- conservative against crowding.

## The trap, displayed

| Correlation with crowding percentile | Mean across commodities |
|---|---|
| Current week's log RV (contemporaneous) | +0.011 |
| Next week's log RV (raw, no baseline) | +0.007 |
| Next week's log RV, HAR residual (partial) | -0.001 |

The first two rows are the lagged-vol-proxy effect this repo already measured as the cross-sectional vol tilt: low crowding sits next to high vol, and vol persists, so crowding 'predicts' vol until vol's own history is allowed to speak. The third row is the question.

## Results

| Quantity | Value |
|---|---|
| Commodities | 24 |
| Pooled weekly observations | 1,328 |
| Mean HAR R-squared (baseline quality) | 0.223 |
| Mean delta R-squared from adding crowding | 0.0019 |
| Mean partial correlation | -0.0013 |
| Negative partials | 11 of 24 (sign test p=0.839) |
| PRIMARY: pooled weekly z-product mean | -0.0015 (p=0.853) |
| SECONDARY: extremeness form | +0.0201 (p=0.004), positive in 15 of 24 commodities (sign test p=0.307) |

Only the primary counts toward the verdict; the extremeness row is reported to keep the forking path visible rather than silent. If the extremeness form prints significant, note the scale before getting excited: a weekly z-product of ~0.02 is a partial correlation of ~0.02 against a baseline R-squared of ~0.22 -- statistically detectable in ~30k observations and economically negligible. Promoting it to a finding would need its own pre-specified test (breadth, subsample stability, and whether extremeness is proxying something simpler, like the persistence of trends).

## Per commodity

| Commodity | Rows | HAR R2 | dR2 | Coef | Partial corr | Raw lead | Contemp |
|---|---|---|---|---|---|---|---|
| Corn | 1,297 | 0.244 | +0.0071 | +0.00160 | +0.089 | +0.272 | +0.282 |
| Soybeans | 1,308 | 0.261 | +0.0041 | +0.00113 | +0.073 | +0.178 | +0.171 |
| Soybean Oil | 1,279 | 0.282 | +0.0001 | +0.00015 | +0.010 | +0.075 | +0.086 |
| Soybean Meal | 1,254 | 0.215 | +0.0040 | +0.00122 | +0.065 | +0.242 | +0.257 |
| Wheat (SRW) | 1,302 | 0.220 | +0.0000 | -0.00011 | -0.007 | +0.112 | +0.133 |
| Wheat (HRW) | 1,307 | 0.200 | +0.0009 | +0.00045 | +0.032 | +0.157 | +0.173 |
| Rough Rice | 1,344 | 0.188 | +0.0001 | +0.00013 | +0.008 | +0.073 | +0.067 |
| Cotton | 1,343 | 0.187 | +0.0000 | +0.00002 | +0.001 | -0.029 | -0.029 |
| Sugar | 1,321 | 0.202 | +0.0010 | +0.00058 | +0.035 | +0.157 | +0.175 |
| Coffee | 1,329 | 0.085 | +0.0003 | +0.00024 | +0.016 | +0.099 | +0.138 |
| Cocoa | 1,329 | 0.265 | +0.0010 | -0.00060 | -0.035 | -0.158 | -0.153 |
| Live Cattle | 1,206 | 0.153 | +0.0013 | -0.00079 | -0.038 | -0.126 | -0.151 |
| Feeder Cattle | 1,236 | 0.173 | +0.0006 | -0.00052 | -0.026 | -0.141 | -0.163 |
| Lean Hogs | 1,295 | 0.109 | +0.0062 | -0.00204 | -0.081 | -0.158 | -0.155 |
| Class III Milk | 925 | 0.042 | +0.0009 | +0.00119 | +0.031 | +0.023 | +0.024 |
| WTI Crude | 1,310 | 0.326 | +0.0033 | -0.00132 | -0.067 | -0.221 | -0.226 |
| Natural Gas | 1,309 | 0.329 | +0.0005 | -0.00059 | -0.028 | +0.005 | +0.015 |
| NY Harbor ULSD | 1,307 | 0.330 | +0.0000 | -0.00013 | -0.008 | -0.044 | -0.053 |
| RBOB Gasoline | 1,300 | 0.242 | +0.0001 | +0.00020 | +0.009 | +0.008 | +0.010 |
| Gold | 1,310 | 0.237 | +0.0015 | +0.00103 | +0.043 | +0.176 | +0.191 |
| Silver | 1,310 | 0.285 | +0.0003 | +0.00040 | +0.022 | +0.068 | +0.076 |
| Copper | 1,310 | 0.267 | +0.0002 | -0.00031 | -0.018 | -0.080 | -0.096 |
| Platinum | 1,177 | 0.280 | +0.0063 | -0.00148 | -0.088 | -0.248 | -0.242 |
| Palladium | 1,110 | 0.238 | +0.0046 | -0.00118 | -0.068 | -0.270 | -0.270 |

## Verdict

**crowding adds nothing to a HAR baseline -- the crowding/vol link is entirely vol's own clustering, seen through a lagged proxy.**
