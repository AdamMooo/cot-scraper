# Does crowded COT positioning predict forward commodity returns?

Generated 2026-08-25. 125 tests (24 commodities x 3 horizons x 2 tails).

## Headline

- **0** tests reach nominal p<0.05. With 125 tests, ~6 are expected by chance alone.
- **0** survive Benjamini-Hochberg FDR control at 5%.

Per-commodity episode counts are 3-12, so those tests have almost no power regardless of what is true. The pooled test below is the one with a real sample.

## Pooled across all commodities

Each episode's forward return is measured as a deviation from that commodity's own unconditional mean, then pooled. Inference resamples whole calendar quarters, because commodities crowd together (all grains at once) and episodes in the same quarter are not independent draws.

| Signal | Horizon | Episodes | Distinct quarters | Mean excess return | Reversion hit rate | p (quarter-clustered) |
|---|---|---|---|---|---|---|
| crowded_long | 4w | 173 | 81 | +0.23% | 50% | 0.720 |
| crowded_long | 13w | 172 | 79 | -0.30% | 54% | 0.851 |
| crowded_long | 26w | 173 | 80 | +3.03% | 52% | 0.250 |
| crowded_short | 4w | 136 | 70 | -0.34% | 49% | 0.571 |
| crowded_short | 13w | 135 | 69 | +0.68% | 51% | 0.557 |
| crowded_short | 26w | 131 | 67 | +0.44% | 44% | 0.828 |

No test survives FDR correction. On this data, crowded positioning does not predict forward returns at a level distinguishable from chance -- which is consistent with the published literature on COT-based timing.

## All tests, most significant first

| Commodity | Signal | Horizon | Episodes | Quarters | Mean fwd | Edge | Reversion hit | p | FDR |
|---|---|---|---|---|---|---|---|---|---|
| Lean Hogs | crowded_short | 4w | 5 | 5 | +10.9% | +10.1pp | 100% | 0.135 | no |
| Cocoa | crowded_short | 13w | 3 | 3 | +22.1% | +18.9pp | 67% | 0.147 | no |
| Cotton | crowded_short | 13w | 3 | 3 | -17.1% | -18.3pp | 33% | 0.169 | no |
| Sugar | crowded_short | 4w | 5 | 5 | +9.0% | +8.3pp | 100% | 0.175 | no |
| Feeder Cattle | crowded_long | 4w | 10 | 10 | +3.5% | +3.0pp | 20% | 0.194 | no |
| Sugar | crowded_long | 4w | 6 | 6 | +7.4% | +6.6pp | 17% | 0.229 | no |
| Corn | crowded_long | 4w | 9 | 9 | +5.4% | +4.8pp | 33% | 0.240 | no |
| Corn | crowded_long | 26w | 9 | 9 | +24.3% | +20.4pp | 44% | 0.244 | no |
| Cotton | crowded_short | 26w | 3 | 3 | -20.2% | -22.9pp | 0% | 0.247 | no |
| Natural Gas | crowded_short | 4w | 5 | 5 | -9.6% | -10.7pp | 20% | 0.270 | no |
| Sugar | crowded_long | 13w | 6 | 6 | +16.8% | +14.5pp | 0% | 0.311 | no |
| Live Cattle | crowded_long | 4w | 13 | 13 | +2.5% | +2.0pp | 23% | 0.316 | no |
| Copper | crowded_long | 4w | 5 | 5 | +5.1% | +4.3pp | 40% | 0.327 | no |
| Coffee | crowded_long | 4w | 9 | 9 | -3.7% | -4.4pp | 78% | 0.344 | no |
| Palladium | crowded_long | 4w | 4 | 4 | -5.5% | -6.6pp | 75% | 0.347 | no |
| Copper | crowded_short | 4w | 9 | 9 | -2.4% | -3.2pp | 56% | 0.350 | no |
| Soybean Oil | crowded_short | 26w | 7 | 7 | +20.2% | +16.0pp | 100% | 0.356 | no |
| RBOB Gasoline | crowded_long | 13w | 7 | 7 | -11.3% | -14.6pp | 43% | 0.386 | no |
| Cotton | crowded_short | 4w | 4 | 4 | -4.6% | -5.0pp | 25% | 0.391 | no |
| Corn | crowded_long | 13w | 9 | 9 | +11.2% | +9.2pp | 44% | 0.416 | no |
| Silver | crowded_long | 13w | 4 | 4 | -5.7% | -9.3pp | 100% | 0.428 | no |
| Cotton | crowded_long | 26w | 11 | 11 | +16.7% | +14.0pp | 27% | 0.429 | no |
| Lean Hogs | crowded_short | 13w | 5 | 5 | +15.8% | +13.6pp | 60% | 0.443 | no |
| Platinum | crowded_long | 13w | 8 | 8 | -4.9% | -6.7pp | 62% | 0.450 | no |
| Coffee | crowded_short | 26w | 7 | 7 | +20.8% | +15.9pp | 71% | 0.462 | no |
| Wheat (SRW) | crowded_short | 4w | 8 | 8 | -2.7% | -3.3pp | 25% | 0.463 | no |
| Copper | crowded_short | 13w | 9 | 9 | -4.6% | -7.4pp | 67% | 0.481 | no |
| Soybeans | crowded_long | 13w | 9 | 9 | +8.9% | +7.2pp | 22% | 0.488 | no |
| Soybean Oil | crowded_short | 4w | 7 | 7 | +3.5% | +2.9pp | 100% | 0.495 | no |
| Rough Rice | crowded_short | 26w | 8 | 8 | -7.4% | -10.2pp | 25% | 0.509 | no |
| NY Harbor ULSD | crowded_short | 4w | 10 | 10 | -2.3% | -3.1pp | 40% | 0.509 | no |
| Soybean Oil | crowded_short | 13w | 7 | 7 | +9.2% | +7.2pp | 86% | 0.512 | no |
| Soybeans | crowded_long | 26w | 9 | 9 | +13.9% | +10.6pp | 22% | 0.517 | no |
| Platinum | crowded_short | 4w | 6 | 6 | +3.0% | +2.3pp | 67% | 0.526 | no |
| Soybean Meal | crowded_long | 4w | 12 | 12 | -1.8% | -2.3pp | 58% | 0.528 | no |
| Gold | crowded_long | 26w | 9 | 9 | -0.7% | -6.8pp | 56% | 0.537 | no |
| Coffee | crowded_short | 4w | 7 | 7 | +3.9% | +3.1pp | 57% | 0.547 | no |
| Sugar | crowded_long | 26w | 6 | 6 | +18.0% | +13.7pp | 17% | 0.572 | no |
| Soybean Meal | crowded_short | 26w | 7 | 7 | +12.5% | +9.6pp | 71% | 0.581 | no |
| RBOB Gasoline | crowded_long | 26w | 7 | 7 | -6.2% | -12.0pp | 57% | 0.590 | no |
| Cotton | crowded_long | 13w | 11 | 11 | +7.0% | +5.8pp | 45% | 0.598 | no |
| Copper | crowded_short | 26w | 9 | 9 | -2.9% | -8.7pp | 44% | 0.601 | no |
| Soybean Meal | crowded_long | 13w | 12 | 12 | -3.9% | -5.4pp | 58% | 0.603 | no |
| NY Harbor ULSD | crowded_short | 13w | 10 | 10 | -4.1% | -6.6pp | 50% | 0.605 | no |
| Soybeans | crowded_long | 4w | 10 | 10 | +2.1% | +1.6pp | 50% | 0.608 | no |
| Feeder Cattle | crowded_short | 4w | 10 | 10 | -0.7% | -1.2pp | 30% | 0.609 | no |
| Gold | crowded_long | 13w | 9 | 9 | -0.4% | -3.5pp | 56% | 0.616 | no |
| Cocoa | crowded_short | 26w | 3 | 3 | +15.6% | +9.0pp | 33% | 0.620 | no |
| Class III Milk | crowded_long | 4w | 5 | 5 | +3.1% | +2.6pp | 20% | 0.625 | no |
| Silver | crowded_long | 4w | 4 | 4 | -2.0% | -3.2pp | 50% | 0.627 | no |
| Platinum | crowded_short | 13w | 6 | 6 | +6.1% | +4.3pp | 33% | 0.648 | no |
| Sugar | crowded_short | 26w | 4 | 4 | -7.2% | -11.5pp | 25% | 0.651 | no |
| Soybeans | crowded_short | 26w | 10 | 10 | +10.0% | +6.6pp | 60% | 0.677 | no |
| Live Cattle | crowded_long | 13w | 12 | 12 | +4.7% | +3.2pp | 25% | 0.680 | no |
| RBOB Gasoline | crowded_long | 4w | 8 | 8 | -1.8% | -2.8pp | 75% | 0.680 | no |
| Feeder Cattle | crowded_long | 26w | 10 | 10 | +8.7% | +5.1pp | 30% | 0.681 | no |
| Lean Hogs | crowded_long | 26w | 5 | 5 | +13.7% | +9.9pp | 0% | 0.681 | no |
| Class III Milk | crowded_short | 4w | 4 | 4 | -1.9% | -2.4pp | 25% | 0.696 | no |
| Platinum | crowded_long | 4w | 7 | 7 | -0.7% | -1.4pp | 57% | 0.700 | no |
| WTI Crude | crowded_long | 4w | 4 | 4 | -2.3% | -3.0pp | 75% | 0.713 | no |
| Corn | crowded_short | 13w | 12 | 12 | +5.7% | +3.7pp | 67% | 0.716 | no |
| Feeder Cattle | crowded_long | 13w | 10 | 10 | +4.5% | +2.8pp | 30% | 0.723 | no |
| NY Harbor ULSD | crowded_long | 13w | 10 | 10 | -2.0% | -4.5pp | 60% | 0.724 | no |
| Platinum | crowded_short | 26w | 6 | 6 | +8.2% | +4.5pp | 33% | 0.731 | no |
| Palladium | crowded_long | 26w | 6 | 6 | +14.9% | +8.4pp | 33% | 0.740 | no |
| WTI Crude | crowded_long | 26w | 4 | 4 | +12.2% | +7.3pp | 0% | 0.741 | no |
| Rough Rice | crowded_long | 26w | 9 | 9 | +6.9% | +4.1pp | 56% | 0.745 | no |
| Soybean Meal | crowded_long | 26w | 12 | 12 | -2.8% | -5.7pp | 67% | 0.746 | no |
| Coffee | crowded_long | 13w | 9 | 9 | -2.7% | -5.1pp | 56% | 0.748 | no |
| WTI Crude | crowded_long | 13w | 4 | 4 | -2.3% | -4.8pp | 75% | 0.749 | no |
| Feeder Cattle | crowded_short | 26w | 10 | 10 | +7.4% | +3.8pp | 70% | 0.756 | no |
| NY Harbor ULSD | crowded_short | 26w | 10 | 10 | -1.7% | -6.8pp | 50% | 0.760 | no |
| Soybeans | crowded_short | 13w | 10 | 10 | +4.0% | +2.3pp | 60% | 0.760 | no |
| Platinum | crowded_long | 26w | 8 | 8 | -0.1% | -3.8pp | 50% | 0.773 | no |
| Class III Milk | crowded_long | 26w | 5 | 5 | -2.2% | -5.3pp | 80% | 0.776 | no |
| Wheat (SRW) | crowded_short | 26w | 8 | 8 | -0.5% | -3.7pp | 50% | 0.796 | no |
| Cocoa | crowded_long | 26w | 6 | 6 | +10.5% | +3.9pp | 50% | 0.808 | no |
| Lean Hogs | crowded_long | 13w | 5 | 5 | +6.7% | +4.5pp | 20% | 0.809 | no |
| Lean Hogs | crowded_long | 4w | 5 | 5 | +2.1% | +1.4pp | 40% | 0.815 | no |
| Silver | crowded_short | 26w | 5 | 5 | +2.7% | -4.1pp | 60% | 0.824 | no |
| Cocoa | crowded_short | 4w | 3 | 3 | -0.5% | -1.5pp | 67% | 0.828 | no |
| Soybean Meal | crowded_short | 4w | 7 | 7 | -0.5% | -1.0pp | 29% | 0.829 | no |
| Live Cattle | crowded_long | 26w | 13 | 13 | +5.0% | +2.2pp | 38% | 0.829 | no |
| Silver | crowded_long | 26w | 4 | 4 | +2.6% | -4.2pp | 50% | 0.829 | no |
| Gold | crowded_long | 4w | 9 | 9 | +0.5% | -0.5pp | 67% | 0.830 | no |
| Live Cattle | crowded_short | 13w | 3 | 3 | +3.3% | +1.8pp | 33% | 0.837 | no |
| Class III Milk | crowded_long | 13w | 5 | 5 | -1.3% | -3.0pp | 60% | 0.837 | no |
| Soybean Meal | crowded_short | 13w | 7 | 7 | +3.7% | +2.2pp | 86% | 0.840 | no |
| Corn | crowded_short | 26w | 12 | 12 | +7.3% | +3.4pp | 67% | 0.847 | no |
| Soybean Oil | crowded_long | 26w | 9 | 9 | +6.9% | +2.6pp | 44% | 0.858 | no |
| Wheat (HRW) | crowded_short | 26w | 8 | 8 | -0.4% | -3.5pp | 50% | 0.869 | no |
| Sugar | crowded_short | 13w | 5 | 5 | -0.6% | -2.9pp | 20% | 0.876 | no |
| Class III Milk | crowded_short | 26w | 4 | 4 | +0.3% | -2.8pp | 50% | 0.876 | no |
| Natural Gas | crowded_short | 26w | 5 | 5 | +1.2% | -3.7pp | 60% | 0.888 | no |
| Cocoa | crowded_long | 13w | 6 | 6 | +4.6% | +1.4pp | 50% | 0.895 | no |
| Lean Hogs | crowded_short | 26w | 5 | 5 | +7.7% | +3.9pp | 80% | 0.898 | no |
| Wheat (HRW) | crowded_long | 13w | 8 | 8 | +0.1% | -1.5pp | 62% | 0.900 | no |
| Copper | crowded_long | 26w | 4 | 4 | +7.8% | +2.0pp | 50% | 0.905 | no |
| NY Harbor ULSD | crowded_long | 4w | 10 | 10 | +1.2% | +0.5pp | 40% | 0.910 | no |
| Live Cattle | crowded_short | 4w | 3 | 3 | +0.8% | +0.3pp | 67% | 0.911 | no |
| Wheat (HRW) | crowded_long | 4w | 8 | 8 | +0.0% | -0.5pp | 50% | 0.912 | no |
| Feeder Cattle | crowded_short | 13w | 10 | 10 | +2.6% | +0.9pp | 80% | 0.912 | no |
| Soybean Oil | crowded_long | 13w | 9 | 9 | +0.6% | -1.4pp | 56% | 0.917 | no |
| Class III Milk | crowded_short | 13w | 4 | 4 | +0.2% | -1.5pp | 50% | 0.922 | no |
| Soybeans | crowded_short | 4w | 10 | 10 | +0.2% | -0.3pp | 60% | 0.930 | no |
| Silver | crowded_short | 4w | 5 | 5 | +0.7% | -0.4pp | 60% | 0.938 | no |
| Cocoa | crowded_long | 4w | 6 | 6 | +0.6% | -0.4pp | 50% | 0.939 | no |
| Coffee | crowded_short | 13w | 7 | 7 | +3.5% | +1.2pp | 71% | 0.945 | no |
| Wheat (HRW) | crowded_short | 13w | 8 | 8 | +0.9% | -0.6pp | 50% | 0.946 | no |
| Rough Rice | crowded_short | 4w | 8 | 8 | +0.7% | +0.3pp | 50% | 0.948 | no |
| Rough Rice | crowded_long | 4w | 9 | 9 | +0.2% | -0.2pp | 44% | 0.952 | no |
| Palladium | crowded_long | 13w | 6 | 6 | +2.1% | -1.3pp | 33% | 0.953 | no |
| Rough Rice | crowded_short | 13w | 8 | 8 | +1.6% | +0.3pp | 62% | 0.961 | no |
| Wheat (SRW) | crowded_short | 13w | 8 | 8 | +1.2% | -0.5pp | 62% | 0.963 | no |
| Cotton | crowded_long | 4w | 11 | 11 | +0.5% | +0.1pp | 45% | 0.975 | no |
| Coffee | crowded_long | 26w | 9 | 9 | +4.2% | -0.7pp | 56% | 0.977 | no |
| Wheat (HRW) | crowded_long | 26w | 8 | 8 | +2.5% | -0.5pp | 38% | 0.979 | no |
| Natural Gas | crowded_short | 13w | 5 | 5 | +3.5% | +0.5pp | 40% | 0.983 | no |
| Silver | crowded_short | 13w | 5 | 5 | +3.2% | -0.3pp | 80% | 0.985 | no |
| Corn | crowded_short | 4w | 12 | 12 | +0.7% | +0.1pp | 50% | 0.986 | no |
| NY Harbor ULSD | crowded_long | 26w | 10 | 10 | +5.6% | +0.5pp | 50% | 0.988 | no |
| Wheat (HRW) | crowded_short | 4w | 8 | 8 | +0.4% | -0.1pp | 38% | 0.990 | no |
| Soybean Oil | crowded_long | 4w | 9 | 9 | +0.6% | -0.0pp | 56% | 0.997 | no |
| Copper | crowded_long | 13w | 4 | 4 | +2.9% | +0.0pp | 50% | 0.999 | no |
| Rough Rice | crowded_long | 13w | 9 | 9 | +1.3% | +0.0pp | 56% | 1.000 | no |

## How to read this

`Episodes` is the real sample size: consecutive crowded weeks collapsed into one event, requiring a 6-month clear gap to start a new one. `Quarters` shows how many distinct calendar quarters those episodes fall in -- if it is much lower than the episode count, the events are clustered and the effective sample is smaller still. `Edge` is the conditional mean minus the unconditional mean over the same window. `Reversion hit` is how often price moved *against* the crowd (down after crowded longs, up after crowded shorts); 50% is a coin flip. `p` comes from a circular block bootstrap that preserves the return series' autocorrelation.
