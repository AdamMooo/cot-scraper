Last updated: 2026-08-25 | Status: manual GUI built; weekly cloud automation built, not yet pushed/deployed

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
| `cross_section.py` | Cross-sectional test: rank all commodities against each other weekly, long least-crowded vs short most-crowded. Exists because the time-series test is sample-starved (8 episodes per commodity); this gets 1,348 portfolio-weeks. Result is nominally significant but fails every robustness check, so also not a finding |

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
  `requests` through the shared session, no new dependency. Looks up the
  close at/before each of the two report dates being compared (COT dates are
  Tuesdays and nearly always trading days, but a holiday can shift things by
  a day or two, hence the small look-back window) rather than counting
  trading days back, so the price window always matches the actual
  positioning window being compared
- **`notify.py`** -- Gmail SMTP, reading `GMAIL_USER`/`GMAIL_APP_PASSWORD`/`MAIL_TO`
  from the environment (GitHub Actions secrets in CI). Never hardcode these
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
p=0.047. **It does not survive contact with the robustness table**, and the
table is the point:

| Check | p | Why it matters |
|---|---|---|
| Quintiles instead of terciles | 0.174 | a real monotonic signal should *sharpen* under a more extreme sort, not weaken |
| Returns clipped at +/-5%/wk | 0.381 | the effect mostly lives in large weekly moves |
| First half alone | 0.187 | neither half stands on its own |
| Second half alone | 0.140 | " |

0 of 5 robustness specs clear p<0.05. So the verdict is "nominally
significant, fragile, not established". The one genuinely encouraging feature
is that the magnitude is stable across halves (+5.7% vs +6.0% annualised),
which is what a small real effect starved of power would also look like.

Two corrections found here are worth not re-breaking:

- **Entry lag.** CFTC data is as-of Tuesday, published Friday. Forming a
  portfolio on the as-of date and holding Tuesday-to-Tuesday trades three of
  seven days on unpublished information. `_ENTRY_LAG_WEEKS = 1` fixes it, and
  it cost a quarter of the raw effect (p 0.006 -> 0.046). Do not "simplify"
  this away.
- **Yahoo's continuous series is not roll-adjusted.** Every roll injects a
  price gap that is not a real return, and because term structure correlates
  with positioning, those gaps do not wash out at random. Given the effect
  collapses when returns are clipped, this is the leading candidate
  explanation for whatever is left. Resolving it needs a roll-aware return
  series and is the highest-value next step before any further modelling.

Extending this properly: the Disaggregated report separates Managed Money
from Producer/Merchant and Swap Dealers, which is a cleaner speculation proxy
than the legacy non-commercial bucket (CFTC split the report in 2009 for that
reason). Testing Managed Money positioning on 2009-present is the obvious
next experiment, at the cost of a much shorter history. Do it inside the
cross-sectional framing, not the time-series one, or the sample will be too
small to say anything.

## Do Not Touch

- This started as a fork of a generic base kit (same shape used elsewhere for
  other document-listing sites). Don't wire imports back to that base kit in
  either direction; if the base kit gains a generic improvement worth having
  here, port it by hand.

---

**Hub:** [[cot-scraper/cot-scraper|COT Report Downloader]]
