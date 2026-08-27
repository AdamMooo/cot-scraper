Last updated: 2026-08-27 | Status: FULLY LIVE — secrets set, HTML email confirmed sending from CI. Research program COMPLETE: five studies (levels, cross-section, MM flow, commercial flow, vol-vs-HAR), all nulls — no investable information in COT positioning, for returns or for vol. The report now carries the three uses the data does support: attribution, OI/fragility watch, structural context (see "Weekly automation" and research/APPLICATIONS.md)

## Repo Card

- **Run (GUI, manual/ad-hoc use):** `python gui.py`
- **Run (console, manual/ad-hoc use):** `python scraper.py`
- **Build (GUI):** `python build_exe.py` -> `dist/COT Report Downloader.exe`
- **Run (weekly automation, what actually matters now):** `python weekly_update.py`, driven by `.github/workflows/weekly-cot-update.yml` on GitHub Actions, every Friday
- **Runtime:** Python 3.13, `requests` only at runtime (`.venv/` not yet created for this repo)
- **External deps:** none for scraping (unauthenticated static pages on cftc.gov); Gmail SMTP for the weekly email, via GitHub Actions secrets
- **Workflow:** no GSD, no `.planning/` - small standalone utility

## Two ways to use this repo

Built first as a handoff GUI tool (search box, tick boxes, exe), then pivoted the
same day to also run unattended: a GitHub Actions cron job that pulls the week's
new data, computes positioning highlights, commits the update, and emails a
report. **The automation is the actual point now** -- the GUI still works for an
ad-hoc manual pull of any category/year, but nobody needs to run it for the
weekly report to happen. See "Weekly automation" below for that path, and
`README.md` for the one-time Gmail/GitHub-secrets setup.

## What It Does

Downloads all seven CFTC Commitments of Traders (COT) report categories: Legacy
(Futures Only / Combined), Disaggregated (Futures Only / Combined), Traders in
Financial Futures / TFF (Futures Only / Combined), and the Supplemental/CIT
report. For each ticked category: one `.txt` file per year of historical
archive CFTC has published, plus the current year. See `fund_data.CATEGORIES`
for the exact current-week URL and historical zip-prefix pair per category,
confirmed against the live site's section headings and link text on
2026-08-25 (not guessed from filenames - see git history for how each was
verified).

Historical years arrive from CFTC as a `.zip` containing one `.txt` file;
`downloader._download_and_extract_zip` pulls out the text and discards the
zip, so nothing needs manual unzipping. The current year always comes from
the live current-week file (`fund_data.fetch_fund`'s `extract: False` entry),
not that year's zip, even if CFTC has already posted one - the live file is
kept continuously current, the zip is not guaranteed to be.

Text format only, by design (see README "Notes") - `.xls`/`.xlsx` variants
that CFTC also publishes for every category are never fetched.

## Constraints

- **Platform:** Windows paths throughout (pathlib), same as the base kit
- **No auth, no rate limiting encountered** - static Drupal site
- **The category list is fixed in code, not crawled.** Unlike a fund roster,
  CFTC's report taxonomy essentially never changes, so `fund_data.CATEGORIES`
  is a hardcoded table (7 tuples) rather than something discovered from a
  sitemap. What *is* rediscovered fresh every run is which years have a
  historical archive - `fund_data.fetch_fund` scrapes
  `HistoricalCompressed/index.htm` live each time
- **Bundled multi-year zips are excluded by construction, not a skip-list.**
  CFTC also publishes a few "hist" range zips (`deacot1986_2016.zip`,
  `dea_cit_txt_2006_2016.zip`, etc.) that duplicate the per-year files. The
  year-matching regex in `fund_data.fetch_fund` only matches a bare 4-digit
  year immediately before `.zip`; a bundle's `_2016.zip` tail never matches,
  so it's never fetched. Don't add a separate exclusion list - if a category
  ever needs one, fix the regex instead
- **`fund_data.discover_build_id()` doesn't discover a real build id.** CFTC
  isn't Next.js. The function is kept (same name, same call sites in
  `fund_index.py`/`downloader.py`) purely so this fork didn't need to touch
  those two files' control flow; it fetches and caches the historical page
  once per run so every category shares one snapshot
- **Untrusted-input sanitizing (`downloader.safe_name`) is still applied**
  to category names and year strings even though both are effectively
  code-controlled here, for consistency with the shared `downloader.py`
  engine and in case a future category is added carelessly

## Key Files

Unchanged from the base kit: `paths.py`, `http_client.py`, `settings.py`,
`gui.py`, `scraper.py`, `shortcut.py`, `frog.py`, `frog_art.py`,
`generate_icon.py`, `build_exe.py`. All site-specific behavior lives in three
files, same as the base kit's own design intent:

| File | Purpose |
|------|---------|
| `site_config.py` | `SITE_BASE`, `SITE_NAME`, `APP_NAME`, `ITEM_WORD`/`ITEM_WORD_PL` - concrete CFTC values |
| `fund_data.py` | `CATEGORIES` (the 7 report types), `discover_build_id` (fetches+caches the historical page), `fetch_fund` (builds the {year: {url, extract}} document dict for one category) |
| `fund_index.py` | Wraps `fund_data.CATEGORIES` in the same cached-list-with-refresh-banner shape the GUI expects. No crawling - the list can't shrink except from a code bug, hence `_MIN_PLAUSIBLE_FUND_COUNT = 7` |
| `downloader.py` | `_download_and_extract_zip` (unzips a historical year and saves its one `.txt` member), `_DOC_NAMES`/`_ACRONYMS` emptied (doc keys are plain year strings, no mapping needed). Skip-if-exists only applies to `extract: True` (historical, immutable) entries -- the current year's file is always re-fetched and overwritten, since it's CFTC's continuously-updated feed, not a static document |
| `contracts.py` | The 24-commodity universe, each as a **chain** of CFTC names. CFTC renames contracts when exchanges merge or specs change, and treating each name as its own market shattered 40-year histories into fragments: copper read as 205 weeks instead of 1,898, cocoa was split 6 ways, and crude was being read off a secondary ICE listing while priced against NYMEX. Deliberately excludes co-trading contracts (CORN MidAmerica alongside CBOT) and size variants (MICRO GOLD alongside GOLD), which would double-count |
| `prices.py` | Weekly closes from Yahoo's public chart endpoint. Two traps found by testing: `range=max` silently returns **monthly** bars, so explicit `period1`/`period2` epochs are required; and history starts mid-2000, which caps any price-linked study at ~26 years even though positioning goes back to 1986. Cached to `.cot-cache/prices/` |
| `study.py` | Time-series forward-return study. Offline research step, not part of the weekly job. See "The empirical finding" below before touching it |
| `cross_section.py` | Cross-sectional test: rank all commodities against each other weekly, long least-crowded vs short most-crowded. Exists because the time-series test is sample-starved (8 episodes per commodity); this gets 1,348 portfolio-weeks. The nominally-significant spread turns out to be a volatility tilt, not positioning -- see "The cross-sectional attempt" below before touching it |
| `managed_money.py` | Diagnostic on the Disaggregated report's Managed Money columns: verifies the column indices against every year-file, then measures level-vs-flow persistence and the flow/return correlation. Ranks no signal and makes no claim about returns -- it exists to say what the eventual test has to control for. See "Managed Money" below |
| `mm_flow.py` | The test `managed_money.py` specified, run 2026-08-27: Managed Money flow ranked cross-sectionally, orthogonalised against the formation-week return, raced head-to-head against pure short-term reversal, with all of `cross_section.py`'s controls carried over (entry lag, point-in-time percentiles, IC, risk-parity legs, jackknife). **Verdict: flow has zero cross-sectional information** (IC +0.0002, p=0.99), and the no-CFTC reversal benchmark beats it decisively. This closed the research question. See "Managed Money" below and `research/MM-FLOW.md` |
| `hedger_flow.py` | The KRT follow-up `research/APPLICATIONS.md` ranked #2: COMMERCIAL flow (legacy columns 11/12, verified against the 1986 and 2025 headers) through the same harness as `mm_flow.py`, targeting the one positioning premium that survives post-2004 replication (Kang-Rouwenhorst-Tang 2020's liquidity premium, Marechal 2023). **Verdict: null after a 1-week publication lag** -- +1.4%/yr p=0.71, IC -0.0008, orthogonalised +0.2%/yr p=0.96. Note the sign conventions differ from mm_flow (hedgers are contrarians; the effect would print POSITIVE spread/IC). Reversal itself is weaker on this longer 2005+ sample (+8.4%/yr, p=0.073) than on mm_flow's 2015+ (+20.6%) -- the reversal side-finding is sample-dependent too. `research/HEDGER-FLOW.md` |
| `vol_forecast.py` | The follow-up ranked #1 (no published commodity version exists): does crowding forecast next week's realized vol incrementally to a HAR baseline (Corsi 2009; log RV on its 1wk/4wk/13wk history, RV from daily closes via `prices.daily_closes`, per-commodity OLS in pure Python)? **Verdict: primary null** -- partial corr -0.0013, pooled p=0.85, mean dR2 +0.002 against HAR's 0.223. The pre-specified SECONDARY (extremeness \|pct-50\|) prints +0.02 at p=0.004 but is economically negligible (~0.02 partial corr) and narrow (positive in 15/24, sign test p=0.31) -- **flagged, not promoted**; promoting it would need its own pre-specified test. Also documents that the cross-sectional vol tilt is a BETWEEN-commodity fact: within-commodity, crowding vs own-week vol is only +0.011. `research/VOL-FORECAST.md` |
| `roll_check.py` | Data-quality diagnostic for `prices.py`: bucket weekly \|return\| by day-of-month to find contract-roll gaps in Yahoo's non-roll-adjusted continuous series. Flags 3 of 24 (Class III Milk, Lean Hogs, Live Cattle). Standalone, no effect on the weekly job |

## Weekly automation

Added the same session as the download engine above, once the actual goal turned
out to be "collect and analyze every week," not "hand someone an exe."

- **`weekly_update.py`** -- the entry point. Downloads into `.cot-cache/`
  (gitignored; full history, restored across CI runs by `actions/cache` so the
  ~300MB historical backfill is only ever fetched once), then *merges* (not
  copies -- see the current-year accumulation point below) this week's
  snapshot into `data/<category>/<year>.txt` (git-tracked; small, grows one
  row per market per week), writes `reports/<date>.md` and `reports/latest.md`
  (git-tracked), then emails the report. A failure anywhere sends a "FAILED"
  email before re-raising, so a broken run is never silent
- **`analysis.py`** -- v1 scope is one report, one metric: Legacy (Futures
  Only), net non-commercial position vs. each market's own full history
  (percentile) and vs. last week (change), shown next to what price actually
  did the same week (`prices.py`) -- comparing the two, not positioning in
  isolation, is the actual point (the user's words: "we need comparisons to
  the actual price of the futures we are talking about to understand what
  influence these reports and insights they provide. That's the whole
  point"). Several corrections were needed once this was tested against
  real data, not just written and assumed correct:
  - **Stale-market filter**: only markets reported as of the most recent date
    anyone has are included. Without this, a market that stopped being
    reported decades ago trivially scores "100th percentile" against its own
    short, ancient history
  - **Ticker allow-list, not a keyword exclusion list**: which markets get
    analyzed is driven by `prices.MARKET_TICKERS`, ~26 benchmark commodities
    with a real Yahoo Finance ticker, matched against the market name's
    portion before " - <exchange>". An earlier version tried excluding
    non-commodities by keyword/exchange and kept missing cases (abbreviated
    currency names, DJIA variants, "EURO SHORT TERM RATE" not matching
    "EURODOLLAR", etc.) -- requiring a real ticker is what actually pins the
    report to "the commodity market" *and* is what makes the price
    comparison possible at all, so it replaced the exclusion approach
    entirely rather than living alongside it
  - **Current-year accumulation, not overwrite**: CFTC's own current-year
    text file is only ever this week's single snapshot per market, not a
    running year-to-date file (confirmed 2026-08-25 by checking row counts
    directly -- this was a real bug caught by testing, not an assumption
    that happened to be right). `merge_current_year_snapshot` merges each
    week's snapshot into `data/<category>/<year>.txt` keyed on
    `(market, as_of)`, which is what lets the current year build up a real
    week-over-week history at all. Without this, every automated run would
    have silently overwritten last week's row with this week's
  - **Gap-detection guard**: comparing "latest" against whatever's
    technically "previous" only makes sense when that previous row is
    actually ~1 week old. Early in the current year (or after a missed run),
    the only "previous" row on file might be from the end of last year,
    months away -- `_MAX_PLAUSIBLE_GAP_DAYS` makes the report say
    "n/a (no prior week yet)" instead of showing a multi-month move
    formatted like a one-week one
  - `_MIN_OPEN_INTEREST` was dropped once the ticker allow-list existed --
    every whitelisted benchmark commodity already clears any reasonable
    liquidity bar, so a separate threshold added nothing
  - **Attribution, open interest and fragility (added 2026-08-27, per the
    applications survey).** `_flow_read` names what the week's move was made
    of in the headline and bullets ("specs bought the rally" / "a rally
    against spec selling") -- descriptive attribution, the use the +0.133
    same-week flow/return correlation actually supports. The table gained an
    "OI (wk)" column, and a "Fragility watch" section fires when a market is
    at a positioning extreme AND its open-interest change is in the bottom
    decile of that market's own history (self-calibrated, no magic
    threshold) -- the one-sided-crowd-plus-shrinking-market shape the squeeze
    episode record points at (nickel 2022, cocoa 2024; see
    research/APPLICATIONS.md). None of it forecasts; all of it describes
  - **The report leads with a narrative, not a table.** A data table (even a
    filtered, price-annotated one) isn't analysis -- the user's words after
    the first version: "I DONT JUST WANT THE BENCHMARKS I WANT AN ACTUAL
    ANALYSIS OF IT". `_key_takeaways`/`_crowding_read` name which markets are
    at a genuine positioning extreme (top/bottom decile, `_EXTREME_HIGH`/
    `_EXTREME_LOW`) and say in plain English whether price is *confirming*
    the crowd (momentum, but historically the kind of stretch that unwinds
    sharply) or *diverging* from it (often the first sign a crowded trade is
    starting to break). The `## Full data` table stays underneath for anyone
    who wants to check the underlying numbers, but it's no longer the point
    of the email
- **`prices.py`** -- Yahoo Finance's public, unofficial, no-API-key chart
  endpoint (`query1.finance.yahoo.com/v8/finance/chart/<ticker>`), plain
  `requests` through the shared session, no new dependency. `daily_closes`
  (added 2026-08-27 for `vol_forecast.py`'s realized-vol measurement) shares
  the fetch path with `weekly_closes`, cached as `<ticker>_daily.json`. Looks up the
  close at/before each of the two report dates being compared (COT dates are
  Tuesdays and nearly always trading days, but a holiday can shift things by
  a day or two, hence the small look-back window) rather than counting
  trading days back, so the price window always matches the actual
  positioning window being compared
- **`notify.py`** -- Gmail SMTP, reading `GMAIL_USER`/`GMAIL_APP_PASSWORD`/`MAIL_TO`
  from the environment (GitHub Actions secrets in CI). Never hardcode these.
  As of 2026-08-27 the HTML part is properly rendered, not a `<pre>` dump of
  raw markdown: `_markdown_to_html` handles exactly the constructs
  `build_report` emits (headings, bullets, bold, pipe tables, `---`), with
  all styles inline because Gmail strips `<style>` blocks, numeric cells
  right-aligned, and +/- values coloured green/red. The plain-text part
  stays raw markdown. If `build_report` ever emits a new markdown construct,
  extend the renderer to match
- **`.github/workflows/weekly-cot-update.yml`** -- cron `30 21 * * 5` (Friday,
  comfortably after CFTC's 3:30pm ET release regardless of DST),
  `workflow_dispatch` enabled for manual test runs, `permissions: contents:
  write` so the job can commit its own output back to the repo

Extending to another report category or metric: add a second `TARGET_SLUG`-like
constant (or loop `fund_data.CATEGORIES`) in `weekly_update.py`, and give
`analysis.py` a second `build_report`-shaped function for that report's own
column layout -- Disaggregated/TFF split "commercial" into more categories
(Managed Money, Producer/Merchant, Swap Dealer), so it isn't a drop-in reuse of
the Legacy column indices.

## The empirical finding (read this before "improving" the report)

`study.py` tested whether crowded positioning predicts forward returns.
**It does not.** 138 per-commodity tests: zero reach nominal p<0.05 (about 7
expected by chance). Pooled across commodities, where the sample is actually
big enough to have power: 185 episodes across 87 distinct quarters, mean
excess return +0.65% at 4 weeks, reversion hit rates 42-56%, no p-value below
0.26. Results in `research/FINDINGS.md`, machine-readable in
`research/forward_returns.json`.

Consequences that must not be quietly undone:

- **The weekly report describes, it does not forecast.** An earlier version
  said crowded positioning "could unwind sharply, historically the kind of
  stretch that snaps back." That is an unfalsifiable claim the data actively
  contradicts. `analysis._predictive_power_note` puts the measured hit rate
  in the email footer for exactly this reason. Do not reintroduce predictive
  language, and if someone asks for a "signal" or a trade recommendation, the
  honest answer is that this dataset does not support one.
- **The reason it is a null is sample size, and that is the interesting part.**
  40 years x 24 commodities looks like 45,000 observations, but positioning is
  a highly persistent stock variable, so it collapses to 3-12 independent
  *episodes* per commodity per tail. Any future analysis that reports n in the
  hundreds or thousands for a single commodity has almost certainly forgotten
  to collapse overlapping weeks and is producing inflated significance.

Four guards in `study.py` are load-bearing; removing any of them turns the
null into a false positive:

1. **Point-in-time percentiles** (`point_in_time_percentiles`) rank each week
   against only prior weeks. Full-history ranking is look-ahead bias.
2. **Episode collapsing** (`episode_starts`, `_MIN_EPISODE_GAP`) makes the
   observation count the number of events, not weeks.
3. **Circular block bootstrap** preserves return autocorrelation under the
   null; an i.i.d. assumption understates the error bars.
4. **Quarter-clustered resampling** for the pooled test, because commodities
   crowd together (grains as a bloc) and same-quarter episodes are not
   independent draws.

### The cross-sectional attempt, and why it is also not a finding

`cross_section.py` was the follow-up: rank all 24 commodities against each
other weekly, long the least-crowded tercile, short the most-crowded, which
raises the observation count from ~8 episodes per commodity to **1,348
portfolio-weeks**. That is the version of this question with real statistical
power, and it is how the commodity factor literature tests positioning.

Baseline result looks like something: +0.113% per week, +5.9% annualised,
p=0.047. **It is not a positioning effect.** What it actually is was
identified on 2026-08-25, and the diagnosis matters more than the verdict
because the first version of this file reached the right verdict by the
wrong route.

**What it is: a volatility tilt.** The least-crowded leg is systematically
more volatile than the most-crowded leg -- +0.37pp per week, p=0.000,
holding in 69% of weeks. Equal weighting sizes by dollar, not by risk, so
the portfolio was long high-vol and short low-vol commodities two weeks in
three. There is a mechanism, not just a correlation: volatility clusters,
and speculators cut net length *after* adverse moves, so a low crowding
percentile mechanically coincides with elevated trailing vol. The signal is
partly a lagged volatility proxy. Scaling each leg to equal risk
(`vol_scaled_leg`) takes the estimate from +6.6% to +5.0% annualised and p
from 0.030 to 0.146.

**The decisive test is the rank information coefficient, not the spread.**
Mean weekly Spearman correlation between crowding percentile and forward
return is about -0.005, p=0.42 -- right sign, indistinguishable from zero,
in both halves. Ranking caps how much any one extreme return contributes, so
a genuine monotonic ordering survives it and a magnitude artifact does not.
There is no cross-sectional ordering to find. Standard-literature terms for
reading further: information coefficient and Grinold's fundamental law
(IR = IC * sqrt(breadth)); Frazzini-Pedersen betting-against-beta for the
general "the tilt was the return" result; Moreira-Muir for vol management.

**Losing significance is not proving zero.** Risk parity moves the point
estimate by roughly a quarter, which alone would be suggestive rather than
conclusive. The reading is decisive because three independent angles agree:
no rank information, a highly significant vol tilt in the legs, and the 20
largest weeks by magnitude netting **-20.8%** against a series total of
+152.6%, so the effect lives in the rest of the sample rather than in a
handful of weeks (`_tail_contribution`). Do not restate that angle as the
largest single positive and negative weeks, +16.2% and -16.2% -- those are
near-mirror images of each other by construction and say nothing about the
tail's contribution; an earlier version of this file quoted them as if they
were the net figure.

**Roll contamination was the wrong suspect, and this file previously named
it the highest-value next step. It is not.** `roll_check.py` localises it:
bucket weekly |return| by day-of-month, and a calendar-fixed expiry makes a
roll gap land in a consistent bucket. Three of 24 series are contaminated --
Class III Milk 2.97x (0.35% mid-month against 6.06% at month-end; its front
contract settles to an announced monthly price so it sits pinned, then jumps
contracts), Lean Hogs 1.51x and Live Cattle 1.38x, and each peak bucket
matches that contract's actual expiry rule. The rest of the universe is flat
to within 1.25x. **Removing the three makes the raw effect stronger, not
weaker** (+6.3% annualised, p=0.037; milk alone out, +7.0%, p=0.034). Roll
gaps were adding noise, not manufacturing the result. A roll-adjusted feed
would sharpen the analysis; it would not change the conclusion.

**Three of the original five robustness specs were misread as failures.**
This is the reusable lesson, kept visible on purpose. A p-value is an effect
size over a standard error, and a spec can raise it by shrinking the
numerator (evidence against the effect) or inflating the denominator
(evidence about nothing). Compare *means*, not p-values:

| Original check | mean/wk | p | What it actually tested |
|---|---|---|---|
| Quintiles instead of terciles | +0.109% | 0.179 | power, not monotonicity -- a quintile leg holds ~4 names against a tercile's ~8, so it is less diversified and noisier. The mean is *unchanged*; only the standard error moved. |
| First half alone | +0.110% | 0.179 | power -- halving the sample multiplies the SE by ~sqrt(2), so an effect at p=0.045 in full is *expected* near p=0.15 in half |
| Second half alone | +0.116% | 0.148 | same; the halves differ from each other by 0.3% annualised, i.e. nothing (Gelman-Stern: a difference in significance is not significance in difference) |
| Returns clipped at +/-5% | +0.035% | 0.384 | too aggressive to be an outlier test -- it binds on **19%** of commodity-weeks, compressing the whole distribution in the volatile half of the universe. The +/-10% version binds on 4% and leaves the estimate at +5.1% |

The robustness table now tags each spec `effect size` / `power` /
`distorted` and only counts the effect-size rows -- **2 of 4 of those clear
p<0.05** (risk parity 0.146 and the +/-10% winsorisation 0.058 do not; the
matched equal-weighted control 0.030 and ex-roll-contaminated 0.037 do). It
also adds a
leave-one-commodity-out jackknife -- the original varied buckets, clipping
and time but never cross-section *membership*, the axis a 24-name portfolio
is most exposed on. 23 of 24 single drops leave p<0.05; only Coffee (0.083)
is a real single-name dependency. Watch the mechanical artifact there:
dropping any name takes the tercile cut from 24//3=8 to 23//3=7, so most
drops nudge the mean up for reasons having nothing to do with the dropped
contract.

Two corrections found here are worth not re-breaking:

- **Entry lag.** CFTC data is as-of Tuesday, published Friday. Forming a
  portfolio on the as-of date and holding Tuesday-to-Tuesday trades three of
  seven days on unpublished information. `_ENTRY_LAG_WEEKS = 1` fixes it, and
  it cost a quarter of the raw effect (p 0.006 -> 0.046). Do not "simplify"
  this away.
- **Point-in-time trailing vol.** The risk-parity spec uses the 52 weeks
  strictly before entry (`_VOL_WINDOW`, sliced `[:entry]`). Full-sample vol
  is the easier thing to write and is look-ahead bias of exactly the kind
  `point_in_time_percentiles` exists to prevent: it would let the portfolio
  know in advance which weeks were calm. Measured 2026-08-26, and the channel
  is not the obvious one: the point estimate is **unchanged** (+0.0959% vs
  +0.0964%/wk), because ~81% of the +0.37pp leg vol gap is a durable
  cross-sectional ranking a static estimate still captures and only ~19% is
  the time-varying "vol is high right now" component. The damage is entirely
  in the standard error -- a rolling 1/vol scaler injects estimation noise and
  amplifies weeks whose trailing window happened to be low (18.5% vs 16.5%
  annualised) -- so full-sample vol would have printed this spec at p=0.084
  instead of 0.142, making the vol tilt look like a weaker explanation than it
  is. Note the shape of the error: the look-ahead sits in the *control*, and a
  weakened control inflates the residual effect, so it still flatters the
  signal. And note it moved a p-value without moving the mean, which is the
  robustness-table lesson again.

### Managed Money: what was measured before modelling it

`managed_money.py` (2026-08-26) is the measure-before-you-model step for the
Disaggregated report, and it changed the plan the paragraph above used to
state. It is a diagnostic, not a signal test -- it deliberately ranks nothing.
Read `research/MANAGED-MONEY.md` before building the test.

Verified against the real files, all of which would have been silent failures:

- **Managed Money is columns 13/14, not the legacy report's 8/9.** In this
  layout 8/9 are Producer/Merchant, so reusing the legacy indices analyses
  commercial hedgers under a Managed Money label. Same indices in all 17
  year-files, 191 columns each.
- **The 2010-2012 files' header label is wrong.** They declare column 2 as
  `Report_Date_as_MM_DD_YYYY` while every value in them is ISO `YYYY-MM-DD`,
  same as 2013+. Coding to the declared name writes a parser that rejects
  valid data. The current-year file has no header row at all.
- **History starts 2010-01-05, not 2009** -- the report launched in 2009 but
  CFTC's per-year archive for this prefix begins at 2010. 836 weeks against
  the legacy study's 1,348. The "2009-present" figure was wrong.
- `contracts.py`'s rename chains work unchanged: 24 of 24 stitch.

**Finding 1: test the flow, not the level.** Mean AR(1) of Managed Money
net/OI is **+0.968 as a level, +0.268 as a weekly change**. Under the standard
n(1-rho)/(1+rho) adjustment that is ~13 effective observations per commodity
against ~475 -- about 36x the power. The level figure independently reproduces
the "3-12 episodes per commodity" arithmetic above from a different direction,
and it is the reason not to simply re-run the level test on a cleaner proxy:
**a better speculation measure does not fix a sample-size problem, and
differencing does.**

**Finding 2: flow's booby trap is short-term reversal, not the vol tilt.**
Managed Money flow correlates **+0.133 with the same week's return** -- specs
add length in weeks price rose, which is the documented mechanism. Weekly
commodity returns mean-revert, so a flow signal inherits short-term reversal
for free and will present as a positioning discovery. Against the next week's
return it is **-0.030, negative in 18 of 24 commodities** (two-sided sign test
p=0.023, computed by `_sign_test_p`, not by hand). Right direction for a
price-pressure story; nowhere near enough to accept on a raw tercile spread.

### The flow test ran 2026-08-27 (`mm_flow.py`), and it closed the question

The test above was run exactly as specified -- cross-sectional, both controls,
everything `cross_section.py` carries (entry lag, point-in-time percentiles,
IC, risk-parity legs, block bootstrap, leave-one-out jackknife). 574
portfolio-weeks, 2014-12-30 to 2025-12-23, ~23.4 commodities per week (the
260-week percentile warmup is spent inside the 2010-start history, hence
~2015). Results in `research/MM-FLOW.md` / `research/mm_flow.json`.

**Managed Money flow has zero cross-sectional information.** Not
underpowered-null like the level tests -- zero: tercile spread +3.5%/yr at
p=0.47, and the rank IC is **+0.0002 at p=0.99**, the flattest number this
repo has produced. Orthogonalisation barely changes it (+3.4%, p=0.54)
because there turned out to be nothing to remove reversal *from*: the flow
and reversal spread series correlate at only +0.05 -- the +0.133
contemporaneous correlation was too weak to survive percentile-and-tercile
processing. Every jackknife drop is flat (best p=0.195). This was the
highest-powered version of the question (~36x the level test's effective
sample), so the null is now a measurement, not an absence of evidence.

**The head-to-head made the point brutally: the benchmark with no CFTC data
won.** Pure short-term reversal -- rank on the formation week's own return,
long losers, short winners -- prints +20.6%/yr at p=0.000 on the identical
weeks and identical construction. So the week-to-week structure that exists
in this universe lives in *prices*, and the CFTC positioning column adds
nothing on top. Treat that reversal number with the suspicion this repo has
earned: it did survive its own vol-tilt check (leg vol gap +0.02pp/wk
p=0.61; risk-parity +17.7%/yr p=0.003, so it is NOT the cross_section.py
artifact), but its IC (-0.024) is modest against the size of the spread,
it is gross of costs on a strategy with ~100% weekly turnover, and weekly
reversal is the classic strategy that measurement noise inflates and
transaction costs kill. It is recorded as the yardstick flow failed
against, not as a discovery. Chasing it would be a different project --
one about price data, with no CFTC scraper required.

**Where this leaves the repo:** the research question -- does COT
positioning tell you which commodities to favour or avoid -- is answered
three ways: levels don't forecast (time-series, `study.py`), the
cross-sectional level spread was a volatility tilt (`cross_section.py`),
and flow, the highest-powered framing, is exactly zero (`mm_flow.py`).
The weekly email describes positioning and cites these numbers in its
footer (`analysis._predictive_power_note` now includes the flow IC). Do
not reopen this without new data (real roll-adjusted returns, different
holding horizons, or a genuinely different signal family); another
re-ranking of the same columns is not going to find anything these three
didn't.

**`research/APPLICATIONS.md`** (2026-08-27, hand-written synthesis of a
three-lane literature/practice survey) records what the data IS for --
attribution, crowding-as-fragility, structural monitoring -- with evidence
grades, where our results sit in the literature (they reproduce the
post-2015 consensus; Kang-Rouwenhorst-Tang 2020's two-premium decomposition
explains why naive tests null out), and the only two follow-up tests that
qualified as new questions rather than re-ranking. **Both ran the same day
and both are nulls** (`hedger_flow.py`, `vol_forecast.py` -- see the Key
Files table above for the numbers). Every test this research program named
has now been run: levels, cross-section, MM flow, commercial flow, and
vol forecasting. The only loose thread on record is the vol test's tiny,
narrow extremeness secondary (p=0.004 but ~0.02 partial corr, 15/24
breadth), explicitly flagged-not-promoted. Read APPLICATIONS.md before
proposing any new use of this data.

## Do Not Touch

- This started as a fork of a generic base kit (same shape used elsewhere for
  other document-listing sites). Don't wire imports back to that base kit in
  either direction; if the base kit gains a generic improvement worth having
  here, port it by hand.

---

**Hub:** [[cot-scraper/cot-scraper|COT Report Downloader]]
