# Does crowded COT positioning predict forward commodity returns?

Generated 2026-08-25. 138 tests (24 commodities x 3 horizons x 2 tails).

## Headline

- **0** tests reach nominal p<0.05. With 138 tests, ~7 are expected by chance alone.
- **0** survive Benjamini-Hochberg FDR control at 5%.

Per-commodity episode counts are 3-12, so those tests have almost no power regardless of what is true. The pooled test below is the one with a real sample.

## Pooled across all commodities

Each episode's forward return is measured as a deviation from that commodity's own unconditional mean, then pooled. Inference resamples whole calendar quarters, because commodities crowd together (all grains at once) and episodes in the same quarter are not independent draws.

| Signal | Horizon | Episodes | Distinct quarters | Mean excess return | Reversion hit rate | p (quarter-clustered) |
|---|---|---|---|---|---|---|
| crowded_long | 4w | 185 | 87 | +0.65% | 51% | 0.336 |
| crowded_long | 13w | 182 | 86 | +0.04% | 56% | 0.983 |
| crowded_long | 26w | 182 | 85 | +1.55% | 55% | 0.531 |
| crowded_short | 4w | 178 | 79 | +0.72% | 53% | 0.261 |
| crowded_short | 13w | 178 | 79 | -0.13% | 46% | 0.887 |
| crowded_short | 26w | 176 | 78 | +0.31% | 42% | 0.835 |

No test survives FDR correction. On this data, crowded positioning does not predict forward returns at a level distinguishable from chance -- which is consistent with the published literature on COT-based timing.

## All tests, most significant first

| Commodity | Signal | Horizon | Episodes | Quarters | Mean fwd | Edge | Reversion hit | p | FDR |
|---|---|---|---|---|---|---|---|---|---|
| WTI Crude | crowded_short | 4w | 4 | 4 | -14.3% | -15.1pp | 0% | 0.054 | no |
| Sugar | crowded_long | 4w | 7 | 7 | +9.0% | +8.3pp | 43% | 0.119 | no |
| Lean Hogs | crowded_short | 4w | 11 | 11 | +8.8% | +8.0pp | 73% | 0.130 | no |
| Platinum | crowded_long | 4w | 6 | 6 | -4.9% | -5.5pp | 83% | 0.151 | no |
| Soybean Meal | crowded_long | 4w | 6 | 6 | +6.8% | +6.3pp | 50% | 0.202 | no |
| WTI Crude | crowded_short | 13w | 4 | 4 | -15.9% | -18.4pp | 0% | 0.211 | no |
| Coffee | crowded_short | 4w | 10 | 10 | +5.7% | +5.0pp | 80% | 0.253 | no |
| Soybeans | crowded_long | 4w | 8 | 8 | +4.8% | +4.3pp | 0% | 0.255 | no |
| Corn | crowded_long | 26w | 7 | 7 | +24.1% | +20.2pp | 57% | 0.263 | no |
| Class III Milk | crowded_long | 13w | 5 | 5 | -12.8% | -14.5pp | 80% | 0.267 | no |
| Class III Milk | crowded_short | 13w | 4 | 4 | -12.8% | -14.5pp | 25% | 0.273 | no |
| Sugar | crowded_long | 13w | 7 | 7 | +17.6% | +15.3pp | 29% | 0.277 | no |
| Class III Milk | crowded_short | 4w | 4 | 4 | -5.9% | -6.4pp | 0% | 0.289 | no |
| Sugar | crowded_short | 4w | 8 | 8 | +5.9% | +5.2pp | 75% | 0.301 | no |
| Class III Milk | crowded_short | 26w | 4 | 4 | -16.1% | -19.2pp | 25% | 0.305 | no |
| WTI Crude | crowded_long | 26w | 7 | 7 | +26.4% | +21.6pp | 14% | 0.316 | no |
| Soybean Oil | crowded_long | 4w | 10 | 10 | -2.7% | -3.3pp | 70% | 0.349 | no |
| Gold | crowded_long | 4w | 7 | 7 | -1.4% | -2.4pp | 71% | 0.371 | no |
| Cocoa | crowded_long | 4w | 9 | 9 | -2.9% | -3.9pp | 67% | 0.391 | no |
| Live Cattle | crowded_long | 4w | 11 | 11 | +2.3% | +1.8pp | 9% | 0.405 | no |
| Wheat (SRW) | crowded_long | 4w | 3 | 3 | -4.6% | -5.2pp | 100% | 0.417 | no |
| Corn | crowded_long | 4w | 7 | 7 | +3.9% | +3.3pp | 14% | 0.433 | no |
| Soybean Oil | crowded_short | 4w | 12 | 12 | +3.1% | +2.5pp | 67% | 0.435 | no |
| Rough Rice | crowded_long | 4w | 7 | 7 | +3.4% | +3.0pp | 29% | 0.452 | no |
| Soybean Oil | crowded_short | 13w | 12 | 12 | +9.1% | +7.1pp | 75% | 0.455 | no |
| Copper | crowded_short | 13w | 10 | 10 | -4.9% | -7.8pp | 40% | 0.461 | no |
| Palladium | crowded_short | 26w | 3 | 3 | +23.6% | +17.1pp | 33% | 0.468 | no |
| Silver | crowded_short | 4w | 4 | 4 | +5.5% | +4.3pp | 100% | 0.486 | no |
| Feeder Cattle | crowded_short | 4w | 12 | 12 | -1.1% | -1.6pp | 33% | 0.489 | no |
| Natural Gas | crowded_long | 13w | 7 | 7 | -12.0% | -15.1pp | 100% | 0.495 | no |
| Silver | crowded_long | 4w | 10 | 10 | +3.8% | +2.6pp | 30% | 0.504 | no |
| Platinum | crowded_long | 13w | 5 | 5 | -4.3% | -6.1pp | 100% | 0.507 | no |
| Copper | crowded_short | 26w | 10 | 10 | -4.8% | -10.7pp | 40% | 0.513 | no |
| Soybeans | crowded_long | 13w | 7 | 7 | +8.1% | +6.4pp | 29% | 0.516 | no |
| Wheat (HRW) | crowded_long | 26w | 8 | 8 | +15.0% | +11.9pp | 50% | 0.518 | no |
| Cocoa | crowded_long | 26w | 9 | 9 | -5.6% | -12.2pp | 67% | 0.521 | no |
| Soybean Oil | crowded_short | 26w | 12 | 12 | +14.7% | +10.4pp | 83% | 0.528 | no |
| Cotton | crowded_short | 13w | 7 | 7 | -5.8% | -7.0pp | 43% | 0.537 | no |
| WTI Crude | crowded_long | 13w | 7 | 7 | +11.4% | +8.9pp | 29% | 0.538 | no |
| Platinum | crowded_long | 26w | 6 | 6 | -4.5% | -8.1pp | 67% | 0.538 | no |
| Palladium | crowded_long | 26w | 3 | 3 | +21.0% | +14.5pp | 0% | 0.540 | no |
| Soybeans | crowded_short | 4w | 9 | 9 | -1.6% | -2.1pp | 44% | 0.540 | no |
| Soybeans | crowded_short | 13w | 9 | 9 | +7.7% | +6.0pp | 67% | 0.542 | no |
| Cocoa | crowded_long | 13w | 9 | 9 | -3.6% | -6.8pp | 56% | 0.545 | no |
| Sugar | crowded_long | 26w | 7 | 7 | +19.0% | +14.7pp | 29% | 0.557 | no |
| Wheat (SRW) | crowded_long | 26w | 3 | 3 | -6.4% | -9.6pp | 67% | 0.559 | no |
| Class III Milk | crowded_long | 26w | 5 | 5 | -7.7% | -10.8pp | 80% | 0.565 | no |
| Cocoa | crowded_short | 4w | 6 | 6 | +3.9% | +2.9pp | 67% | 0.573 | no |
| WTI Crude | crowded_short | 26w | 4 | 4 | -7.6% | -12.4pp | 25% | 0.575 | no |
| Wheat (SRW) | crowded_long | 13w | 3 | 3 | -4.3% | -6.1pp | 100% | 0.580 | no |
| Corn | crowded_long | 13w | 7 | 7 | +8.5% | +6.6pp | 43% | 0.593 | no |
| WTI Crude | crowded_long | 4w | 7 | 7 | +3.6% | +2.9pp | 43% | 0.610 | no |
| Palladium | crowded_long | 13w | 3 | 3 | +11.5% | +8.1pp | 0% | 0.610 | no |
| Coffee | crowded_short | 13w | 10 | 10 | +9.5% | +7.1pp | 90% | 0.616 | no |
| Soybean Meal | crowded_short | 26w | 8 | 8 | +11.3% | +8.4pp | 75% | 0.616 | no |
| Live Cattle | crowded_short | 13w | 5 | 5 | -2.7% | -4.2pp | 40% | 0.617 | no |
| Cocoa | crowded_short | 13w | 6 | 6 | +9.0% | +5.8pp | 83% | 0.618 | no |
| Live Cattle | crowded_short | 26w | 4 | 4 | -2.8% | -5.7pp | 25% | 0.626 | no |
| Rough Rice | crowded_short | 26w | 8 | 8 | -4.4% | -7.2pp | 50% | 0.629 | no |
| Coffee | crowded_short | 26w | 10 | 10 | +15.6% | +10.7pp | 70% | 0.632 | no |
| Feeder Cattle | crowded_long | 13w | 8 | 8 | +5.6% | +3.8pp | 25% | 0.635 | no |
| Rough Rice | crowded_short | 4w | 8 | 8 | -1.3% | -1.7pp | 38% | 0.653 | no |
| Live Cattle | crowded_long | 26w | 11 | 11 | +7.4% | +4.6pp | 18% | 0.661 | no |
| Coffee | crowded_long | 13w | 10 | 10 | -4.1% | -6.5pp | 60% | 0.662 | no |
| Platinum | crowded_short | 13w | 8 | 8 | +5.4% | +3.6pp | 38% | 0.667 | no |
| Cotton | crowded_short | 26w | 7 | 7 | -4.9% | -7.5pp | 43% | 0.673 | no |
| Rough Rice | crowded_long | 26w | 7 | 7 | +8.8% | +5.9pp | 57% | 0.677 | no |
| Gold | crowded_long | 26w | 7 | 7 | +1.8% | -4.3pp | 43% | 0.681 | no |
| Natural Gas | crowded_short | 4w | 9 | 9 | +4.1% | +3.1pp | 56% | 0.691 | no |
| Soybean Meal | crowded_long | 13w | 6 | 6 | +5.7% | +4.2pp | 50% | 0.698 | no |
| Cotton | crowded_long | 4w | 10 | 10 | +1.9% | +1.5pp | 30% | 0.700 | no |
| Soybeans | crowded_short | 26w | 8 | 8 | +8.8% | +5.4pp | 75% | 0.721 | no |
| Feeder Cattle | crowded_long | 26w | 8 | 8 | +8.4% | +4.8pp | 38% | 0.721 | no |
| Copper | crowded_long | 26w | 8 | 8 | -0.4% | -6.2pp | 50% | 0.721 | no |
| Rough Rice | crowded_short | 13w | 8 | 8 | -1.7% | -2.9pp | 38% | 0.727 | no |
| Cocoa | crowded_short | 26w | 6 | 6 | +11.8% | +5.2pp | 100% | 0.740 | no |
| Natural Gas | crowded_long | 4w | 7 | 7 | -1.8% | -2.8pp | 71% | 0.742 | no |
| Feeder Cattle | crowded_short | 26w | 12 | 12 | +7.5% | +3.9pp | 83% | 0.750 | no |
| Wheat (HRW) | crowded_long | 4w | 8 | 8 | +1.9% | +1.4pp | 50% | 0.757 | no |
| NY Harbor ULSD | crowded_short | 13w | 10 | 10 | +6.0% | +3.5pp | 60% | 0.762 | no |
| Soybeans | crowded_long | 26w | 7 | 7 | +7.8% | +4.4pp | 43% | 0.772 | no |
| Gold | crowded_long | 13w | 7 | 7 | +0.9% | -2.1pp | 57% | 0.778 | no |
| Natural Gas | crowded_long | 26w | 7 | 7 | -3.8% | -8.7pp | 57% | 0.786 | no |
| Cotton | crowded_long | 26w | 10 | 10 | +8.0% | +5.3pp | 40% | 0.794 | no |
| Lean Hogs | crowded_short | 13w | 11 | 11 | +6.2% | +4.0pp | 55% | 0.796 | no |
| Coffee | crowded_long | 26w | 10 | 10 | -1.5% | -6.4pp | 40% | 0.797 | no |
| Live Cattle | crowded_short | 4w | 5 | 5 | -0.3% | -0.7pp | 20% | 0.800 | no |
| Soybean Meal | crowded_short | 4w | 8 | 8 | -0.6% | -1.1pp | 50% | 0.802 | no |
| Soybean Meal | crowded_short | 13w | 8 | 8 | -1.6% | -3.1pp | 38% | 0.806 | no |
| Lean Hogs | crowded_long | 13w | 8 | 8 | -2.1% | -4.2pp | 75% | 0.806 | no |
| NY Harbor ULSD | crowded_long | 26w | 11 | 11 | +11.3% | +6.2pp | 45% | 0.809 | no |
| Platinum | crowded_short | 4w | 8 | 8 | +1.6% | +0.9pp | 62% | 0.809 | no |
| Palladium | crowded_short | 4w | 3 | 3 | -0.5% | -1.6pp | 67% | 0.810 | no |
| Copper | crowded_short | 4w | 10 | 10 | +0.1% | -0.7pp | 50% | 0.812 | no |
| Platinum | crowded_short | 26w | 8 | 8 | +6.5% | +2.8pp | 50% | 0.817 | no |
| NY Harbor ULSD | crowded_long | 4w | 12 | 12 | +1.9% | +1.1pp | 33% | 0.821 | no |
| Palladium | crowded_long | 4w | 3 | 3 | -0.3% | -1.3pp | 33% | 0.829 | no |
| Natural Gas | crowded_short | 26w | 9 | 9 | -2.0% | -6.8pp | 44% | 0.835 | no |
| NY Harbor ULSD | crowded_short | 4w | 10 | 10 | +1.7% | +0.9pp | 50% | 0.841 | no |
| Lean Hogs | crowded_long | 26w | 8 | 8 | -1.0% | -4.8pp | 62% | 0.853 | no |
| Lean Hogs | crowded_long | 4w | 8 | 8 | +1.8% | +1.0pp | 38% | 0.856 | no |
| Copper | crowded_long | 4w | 8 | 8 | +0.2% | -0.6pp | 75% | 0.862 | no |
| Wheat (HRW) | crowded_long | 13w | 8 | 8 | +3.3% | +1.7pp | 50% | 0.866 | no |
| Cotton | crowded_short | 4w | 7 | 7 | -0.3% | -0.7pp | 71% | 0.866 | no |
| Wheat (SRW) | crowded_short | 13w | 10 | 10 | +0.2% | -1.6pp | 60% | 0.868 | no |
| Corn | crowded_short | 13w | 12 | 12 | +0.4% | -1.6pp | 67% | 0.872 | no |
| Sugar | crowded_short | 13w | 8 | 8 | -0.4% | -2.7pp | 50% | 0.875 | no |
| Wheat (SRW) | crowded_short | 26w | 10 | 10 | +5.6% | +2.4pp | 60% | 0.875 | no |
| RBOB Gasoline | crowded_long | 13w | 7 | 7 | +5.7% | +2.5pp | 43% | 0.882 | no |
| Rough Rice | crowded_long | 13w | 7 | 7 | +2.4% | +1.2pp | 57% | 0.883 | no |
| RBOB Gasoline | crowded_long | 26w | 7 | 7 | +2.7% | -3.1pp | 43% | 0.889 | no |
| Wheat (SRW) | crowded_short | 4w | 10 | 10 | +1.2% | +0.6pp | 40% | 0.889 | no |
| Palladium | crowded_short | 13w | 3 | 3 | +1.2% | -2.2pp | 33% | 0.890 | no |
| Live Cattle | crowded_long | 13w | 11 | 11 | +2.7% | +1.2pp | 27% | 0.891 | no |
| Silver | crowded_short | 13w | 4 | 4 | +5.1% | +1.6pp | 75% | 0.896 | no |
| Feeder Cattle | crowded_short | 13w | 12 | 12 | +2.7% | +0.9pp | 75% | 0.896 | no |
| RBOB Gasoline | crowded_long | 4w | 8 | 8 | +0.1% | -0.8pp | 50% | 0.897 | no |
| NY Harbor ULSD | crowded_long | 13w | 12 | 12 | +4.2% | +1.6pp | 42% | 0.906 | no |
| Wheat (HRW) | crowded_short | 13w | 8 | 8 | +0.2% | -1.3pp | 38% | 0.906 | no |
| Silver | crowded_short | 26w | 4 | 4 | +9.2% | +2.3pp | 100% | 0.913 | no |
| Silver | crowded_long | 26w | 10 | 10 | +5.1% | -1.7pp | 60% | 0.925 | no |
| Soybean Oil | crowded_long | 13w | 10 | 10 | +0.7% | -1.2pp | 60% | 0.925 | no |
| Class III Milk | crowded_long | 4w | 5 | 5 | +0.0% | -0.5pp | 60% | 0.926 | no |
| Lean Hogs | crowded_short | 26w | 11 | 11 | +1.6% | -2.3pp | 45% | 0.929 | no |
| Corn | crowded_short | 26w | 12 | 12 | +2.0% | -1.9pp | 33% | 0.930 | no |
| Soybean Meal | crowded_long | 26w | 6 | 6 | +1.5% | -1.4pp | 50% | 0.936 | no |
| Wheat (HRW) | crowded_short | 4w | 8 | 8 | +0.9% | +0.4pp | 50% | 0.936 | no |
| Corn | crowded_short | 4w | 12 | 12 | +0.3% | -0.3pp | 58% | 0.936 | no |
| Feeder Cattle | crowded_long | 4w | 8 | 8 | +0.8% | +0.3pp | 38% | 0.938 | no |
| NY Harbor ULSD | crowded_short | 26w | 10 | 10 | +3.2% | -1.9pp | 50% | 0.942 | no |
| Copper | crowded_long | 13w | 8 | 8 | +3.4% | +0.5pp | 38% | 0.950 | no |
| Sugar | crowded_short | 26w | 8 | 8 | +5.6% | +1.4pp | 50% | 0.956 | no |
| Coffee | crowded_long | 4w | 10 | 10 | +0.9% | +0.2pp | 50% | 0.958 | no |
| Wheat (HRW) | crowded_short | 26w | 8 | 8 | +4.1% | +1.1pp | 50% | 0.962 | no |
| Silver | crowded_long | 13w | 10 | 10 | +4.0% | +0.5pp | 40% | 0.967 | no |
| Natural Gas | crowded_short | 13w | 9 | 9 | +3.9% | +0.8pp | 67% | 0.974 | no |
| Soybean Oil | crowded_long | 26w | 10 | 10 | +4.1% | -0.2pp | 70% | 0.994 | no |
| Cotton | crowded_long | 13w | 10 | 10 | +1.2% | +0.0pp | 50% | 1.000 | no |

## How to read this

`Episodes` is the real sample size: consecutive crowded weeks collapsed into one event, requiring a 6-month clear gap to start a new one. `Quarters` shows how many distinct calendar quarters those episodes fall in -- if it is much lower than the episode count, the events are clustered and the effective sample is smaller still. `Edge` is the conditional mean minus the unconditional mean over the same window. `Reversion hit` is how often price moved *against* the crowd (down after crowded longs, up after crowded shorts); 50% is a coin flip. `p` comes from a circular block bootstrap that preserves the return series' autocorrelation.
