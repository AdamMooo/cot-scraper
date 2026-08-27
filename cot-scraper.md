# COT Report Downloader

Weekly automated pull and analysis of CFTC Commitments of Traders (COT) data, plus a
manual GUI fallback for ad-hoc pulls. Runs unattended on GitHub Actions every Friday
after the report drops, downloads the new week's data, flags which commodities have the
most crowded (or fastest-moving) speculative positioning, and emails the result. The
point is "understand what's happening in the commodity market this week," not just
"download some files."

## Status

Built 2026-08-25. Started as a handoff GUI tool (fork of the same base kit as
[[purpose-doc-scraper/purpose-doc-scraper|Purpose Doc Scraper]]'s `web-scraper` fork),
then pivoted the same day once the actual goal came up: an unattended weekly pipeline with
analysis, not an exe for someone else to run. The GUI still works and wasn't removed, but
it's no longer the point.

**Fully live as of 2026-08-27.** The Gmail secrets are set (five successful
workflow_dispatch runs on 2026-08-25/26 prove it -- the commit step only runs after the
email step succeeds), and a manual test run confirmed the new HTML-formatted email sends
from CI. Friday's cron (21:30 UTC) needs nothing; the first email with real week-over-week
comparisons arrives on its own once CFTC posts the as-of 2026-08-25 data.

The download/report half is finished. The research half is settled too, in the negative:
the positioning signal was tested three ways and the one nominally-significant result turns
out to be a volatility tilt rather than a signal. `cross_section.py` runs end to end as of
2026-08-26 -- the two estimator holes (`spearman_ic`, `vol_scaled_leg`) are filled and the
diagnosis reproduces from source, so `research/CROSS-SECTION.md` and `cross_section.json`
are now generated output rather than a writeup ahead of its own code. Nothing imports
`cross_section`, so the Friday automation was never affected either way.

The research question is **closed** as of 2026-08-27. The Managed Money flow test
(`mm_flow.py`) -- the highest-powered framing available, ~36x the effective sample of the
level tests -- found exactly zero cross-sectional information (rank IC +0.0002, p=0.99),
and a benchmark using no CFTC data at all (pure short-term reversal) beat it decisively on
identical weeks. Three studies, three angles, same answer: COT positioning does not tell
you which commodities to favour or avoid. The weekly email describes positioning and
cites all of this in its footer. The email itself also renders as real HTML now instead
of a `<pre>` dump of raw markdown.

## Handoff Notes

Not a handoff tool anymore in the original sense -- it emails one person (the owner) a
report, it isn't given to a colleague. The unsigned-exe/SmartScreen caveats from the
original design only apply if the GUI path is ever used to hand this to someone else.

Scope narrowed and re-widened twice during design, both times for a real reason: first
"current week only" then widened to "current week + full historical" once it came up that
the actual goal is comparing positioning against price moves over time, which needs
history. Then the pivot from "exe" to "cloud automation" once "collects and analyses the
data" turned out to be the real ask, not just downloading. Text-only stuck throughout
(smaller, pandas-ready).

## Recent Changes

- 2026-08-27 (applications survey — what the data IS for): Ran a three-lane deep-research
  survey (return-prediction literature, positioning-as-risk literature, documented
  practitioner usage) and synthesised it into `research/APPLICATIONS.md`. Headlines: our
  three nulls reproduce the post-2015 peer-reviewed consensus (Sanders-Irwin, Gorton-
  Hayashi-Rouwenhorst, KRT's t=-0.43 on raw hedging-pressure levels); Kang-Rouwenhorst-Tang
  2020's two-premium decomposition explains *why* naive positioning tests null out (a
  short-horizon liquidity premium and a long-horizon insurance premium with opposite signs,
  mixed in any raw net-position measure); the classic Basu-Miffre hedging-pressure premium
  loses significance post-2004 in careful replication (Maréchal 2023) -- exactly our era;
  our vol-tilt finding is the public-data shadow of Cheng-Kirilenko-Xiong's convective risk
  flows; and documented practitioner usage (Kemp, Saxo, bank FICC weeklies, OFR, ECB)
  converges on exactly the three uses our measurements support: attribution, crowding-as-
  fragility, structural monitoring. The retail COT-Index/WILLCO tradition has never passed
  an independent test. Two legitimate follow-ups identified and ranked: crowding as a
  *vol* forecaster incremental to a HAR baseline (no published commodity version), and
  commercial flow raced against reversal (targets the one premium that survives post-2004).
  Fragility lesson from the episode record: watch open interest collapse, not just net
  length (nickel's short was 80% OTC-invisible; cocoa's blow-off showed as falling OI).

- 2026-08-27 (the flow test ran, and the research question is closed): Built and ran
  `mm_flow.py`, the test `managed_money.py`'s diagnostic specified: Managed Money flow,
  within-commodity point-in-time percentiles, ranked cross-sectionally, 1-week entry lag,
  with the two controls neither earlier study needed -- flow orthogonalised against the
  formation week's own return, and a head-to-head against pure lagged-return reversal --
  plus everything `cross_section.py` carries (IC, risk-parity legs, block bootstrap,
  jackknife). 574 portfolio-weeks, 2015-2025. **Flow is exactly zero**: spread +3.5%/yr
  p=0.47, rank IC +0.0002 p=0.99, unchanged by orthogonalisation, every jackknife drop
  flat. The orthogonalisation control turned out to have nothing to do: the flow and
  reversal portfolios correlate at only +0.05, so flow was not even repackaged reversal --
  just noise. **The no-CFTC benchmark won the head-to-head**: reversal prints +20.6%/yr at
  p=0.000 on identical weeks, survives its own vol-tilt check (risk-parity +17.7%/yr,
  p=0.003; leg vol gap +0.02pp/wk, p=0.61 -- so it is not the cross_section artifact), but
  is recorded as the yardstick flow failed against, not a discovery: modest IC (-0.024)
  against a big spread, gross of costs at ~100% weekly turnover, and the classic strategy
  measurement noise inflates. Also formatted the weekly email: `notify._markdown_to_html`
  renders headings/bullets/bold/tables with inline styles (Gmail strips `<style>`), numeric
  cells right-aligned, +/- coloured; the footer now cites the flow IC alongside the legacy
  hit rates. Results: `research/MM-FLOW.md` / `mm_flow.json`.

- 2026-08-26 (Managed Money, measured before modelled): Downloaded the Disaggregated (Futures
  Only) history and wrote `managed_money.py` -- a diagnostic that ranks nothing, because the
  last two attempts here each died on something cheap to measure up front. Four data facts
  verified against the real files, each of which would have failed silently: **Managed Money
  is columns 13/14, not the legacy report's 8/9** (8/9 here are Producer/Merchant, so the
  reuse would have analysed commercial hedgers under a Managed Money label); the 2010-2012
  files **declare** column 2 as `Report_Date_as_MM_DD_YYYY` while every value in them is ISO,
  so coding to the header label writes a parser that rejects valid data; history starts
  **2010-01-05, not 2009** (836 weeks, not the "2009-present" the docs claimed); and
  `contracts.py`'s rename chains stitch 24 of 24 unchanged. Then two findings that redesigned
  the experiment. **(1) Test the flow, not the level:** AR(1) of MM net/OI is +0.968 as a
  level and +0.268 differenced, so ~13 effective observations per commodity against ~475 --
  about 36x the power, and an independent re-derivation of this repo's "3-12 episodes"
  arithmetic from a different direction. A cleaner speculation proxy does not fix a
  sample-size problem; differencing does. **(2) Flow's booby trap is short-term reversal, not
  the vol tilt:** MM flow correlates +0.133 with the *same* week's return (specs add length
  after price rises -- the documented mechanism), and weekly commodity returns mean-revert, so
  a flow signal inherits reversal for free and would present as a discovery. Against the next
  week it is -0.030, negative in 18 of 24 names (sign test p=0.023). So the test now needs two
  controls neither previous study did: flow orthogonalised against the same week's own return,
  and a head-to-head against pure lagged-return reversal -- if reversal does as well, the CFTC
  column added nothing, and that is the result.

- 2026-08-26 (the analysis now runs from source): Wrote the two estimators the previous
  session had left as deliberate holes -- `spearman_ic` (tie-corrected Spearman via average
  ranks, returning `None` rather than 0 when a rank vector is constant, since folding an
  undefined correlation in as zero would bias the mean IC toward the null) and
  `vol_scaled_leg` -- and regenerated `research/CROSS-SECTION.md` + `.json`, which had been
  stale output from the *pre-diagnosis* run still saying "0 of 5 specs survive, fragile".
  Every headline figure the docs had recorded in advance reproduced: mean IC -0.0049
  (p=0.418), leg vol gap +0.37pp/wk (p=0.000), verdict "explained by a volatility tilt, not
  positioning". Bootstrap-noise-level drift on a handful of secondary p-values was synced
  into `CLAUDE.md` (e.g. Coffee's jackknife 0.104 -> 0.083, so 23 of 24 single-name drops
  hold rather than 22), and **one real error was found in the docs**: the "largest weeks net
  against the effect" angle had been written as "+16.2% and -16.2% ... largely cancel", which
  are the largest single positive and negative weeks and are near-mirror images by
  construction, saying nothing about the tail's contribution. The actual figure is that the
  20 biggest weeks by magnitude net **-20.8%** against a series total of +152.6%. That angle
  is now computed (`_tail_contribution`) rather than asserted, so it cannot rot again --
  which is the same lesson as the robustness-table misreading: a number quoted in prose and
  not produced by the script is a number nobody is checking. Only 2 of 4 effect-size specs
  clear p<0.05, not the 3 that had been expected.

- 2026-08-25 (diagnosis, and a correction to the same day's own conclusions): Re-audited the
  cross-sectional result instead of accepting it, and the verdict survived while the reasoning
  did not. **The +5.9%/yr spread is a volatility tilt, not positioning.** The least-crowded leg
  is systematically more volatile than the most-crowded (+0.37pp/wk, p=0.000, 69% of weeks) --
  with a mechanism, not a coincidence: vol clusters and speculators cut net length *after*
  adverse moves, so low crowding mechanically coincides with high trailing vol. Risk-parity
  legs take it to +5.0%, p~0.15. The decisive test is the rank information coefficient, which
  is flat (-0.005, p=0.42, both halves) -- there is no cross-sectional ordering to find.
  **Three of the five original robustness specs were misread as failures**: quintiles and both
  sample halves raised p by inflating the standard error, not by shrinking the effect (their
  means are 5.7/5.7/6.0% annualised, i.e. unchanged), and the +/-5% clip binds on 19% of
  observations so it compresses the distribution rather than trimming tails. Added
  `roll_check.py`, which retires the previously-stated top priority: roll contamination is
  real but confined to 3 of 24 series (Class III Milk, Lean Hogs, Live Cattle, each peaking in
  the bucket matching its own expiry rule), and removing them makes the effect *stronger*, so
  the gaps were adding noise rather than manufacturing the result. A roll-adjusted feed would
  sharpen the analysis, not change it. Also fixed docs that still said "not pushed to GitHub"
  and a roll-blocker claim written earlier in the same session.

- 2026-08-25 (research arc, and it is a null): Tested whether the positioning metric the
  weekly report is built on actually predicts anything. It does not, twice over. `study.py`
  (time-series, forward returns): 138 per-commodity tests, **zero** at nominal p<0.05 where
  ~7 were expected by chance; pooled, no p below 0.26. The reason is sample size and that's
  the interesting part -- 40 years x 24 commodities looks like 45,000 observations but
  positioning is a persistent stock variable, so it collapses to 3-12 independent *episodes*
  per commodity per tail. `cross_section.py` (rank all 24 against each other weekly, long
  least-crowded / short most-crowded) buys real power -- 1,348 portfolio-weeks -- and the
  baseline looks like something at +5.9%/yr, p=0.047, but **0 of 5 robustness specs survive**
  (quintiles 0.174, returns clipped at +/-5% 0.381, halves 0.187/0.140). Verdict recorded as
  "nominally significant, fragile, not established" -- **superseded the same day**: three of
  those five specs measured power rather than effect size and were miscounted, and the real
  explanation is the volatility tilt in the bullet above. Read that one, not this count. Two corrections found en route that must
  not be undone: an entry lag (CFTC is as-of Tuesday, published Friday -- forming on the
  as-of date traded 3 of 7 days on unpublished information, and fixing it cost a quarter of
  the raw effect), and normalizing net position by open interest instead of using raw
  contracts, which was ranking market growth. Consequence for the product: the weekly email
  **describes, it does not forecast** -- earlier predictive language ("could unwind sharply")
  was removed as an unfalsifiable claim the data contradicts, and the measured hit rate now
  sits in the email footer. Results in `research/FINDINGS.md` and `research/CROSS-SECTION.md`.

- 2026-08-25 (automation pivot): Added `weekly_update.py`, `analysis.py`, `notify.py`, and
  `.github/workflows/weekly-cot-update.yml` for the unattended Friday pipeline. Two curation
  bugs found and fixed during testing, both worth remembering: (1) a naive percentile
  calculation let markets that stopped reporting decades ago trivially score "100th
  percentile" against their own short history -- fixed by only including markets reported as
  of the most recent date in the data; (2) the Legacy report's ~150 thin ICE Futures Energy
  Div / Nodal Exchange power-grid and pipeline-basis contracts dominated the "most crowded"
  lists purely from having short, undiversified histories, alongside genuine rates/FX/
  equity/crypto instruments that predate the 2009 Disaggregated-report split -- both excluded
  via a manually curated list in `analysis.py`, verified against the actual 2026-08-25 data
  rather than guessed. Redesigned the report itself from a full ~50-340-row dump into a
  curated highlights summary (top movers, most crowded long/short) partway through, since a
  full dump wasn't actually "understanding," just more data.

- 2026-08-25 (build): Cloned from the `AdamMooo/cot-scraper` base kit (still had
  `example.com` placeholders in `site_config.py`). Verified CFTC's actual page structure
  directly (curl + grep on the live HTML, not guesswork) before writing `fund_data.CATEGORIES`
  - confirmed via section headings and link text which URL prefix belongs to which of the 7
  report types, and that a bare 4-digit-year-before-`.zip` regex naturally excludes CFTC's
  bundled multi-year archives without needing an explicit skip-list. Added zip-extraction to
  `downloader.py` since CFTC ships historical years as a zip with one `.txt` inside.

## Known Issues

Yahoo's continuous front-month series is not roll-adjusted, and
`roll_check.py` shows 3 of 24 series are materially contaminated (Class III Milk, Lean
Hogs, Live Cattle) -- but this is a data-quality wart, not a blocker: removing those three
makes the cross-sectional effect *stronger*, so roll gaps were adding noise rather than
manufacturing the result. A roll-adjusted feed would sharpen the analysis, nothing more. No `.venv` created for this repo -- ran against system Python 3.13 during
development. `build_exe.py` untested against this fork (not the current
priority). The weekly email covers only the Legacy (Futures Only) report; the
Disaggregated report's Managed Money columns were researched (`managed_money.py`,
`mm_flow.py`) and found to carry no signal, so there is no analytical reason to add them
to the email -- doing so would be a formatting exercise, not a fast follow.

