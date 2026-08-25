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

Built, tested locally end-to-end, and **pushed to `AdamMooo/cot-scraper`**. The only thing
between it and a live Friday run is the three GitHub Actions secrets (Gmail App Password),
which have to be set from Adam's own terminal -- credential setup Claude won't do. See
`README.md` "One-time setup" for the exact commands.

The download/report half is finished. The research half is settled too, in the negative:
the positioning signal was tested three ways and the one nominally-significant result turns
out to be a volatility tilt rather than a signal. Two estimators in `cross_section.py`
(`spearman_ic`, `vol_scaled_leg`) are deliberately left as `NotImplementedError` holes for
Adam to write -- the scaffolding, plumbing and writeup around them are done and validated,
so the file does not run until those two are filled. Nothing imports `cross_section`, so
the Friday automation is unaffected.

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
  "nominally significant, fragile, not established". Two corrections found en route that must
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

The three GitHub Actions secrets (`GMAIL_USER`, `GMAIL_APP_PASSWORD`, `MAIL_TO`) aren't
set, so the Friday workflow will run the download and commit the report but fail at the
email step. Yahoo's continuous front-month series is not roll-adjusted, and
`roll_check.py` shows 3 of 24 series are materially contaminated (Class III Milk, Lean
Hogs, Live Cattle) -- but this is a data-quality wart, not a blocker: removing those three
makes the cross-sectional effect *stronger*, so roll gaps were adding noise rather than
manufacturing the result. A roll-adjusted feed would sharpen the analysis, nothing more. No `.venv` created for this repo -- ran against system Python 3.13 during
development. `build_exe.py` untested against this fork (not the current
priority). Analysis covers only the Legacy (Futures Only) report; Disaggregated/TFF
breakdowns (Managed Money vs. Producer positioning) are a possible fast follow, not done.

