# cot-scraper

A Windows app that downloads every CFTC Commitments of Traders (COT) report,
current week plus the full historical archive back to whenever each report
type started, filed one folder per report category, one plain `.txt` file
per year. Built for someone later lining these up against price data, not
just reading the current week.

It builds to a single `.exe` you can hand to somebody non-technical, needs no
Python or credentials on their machine, and is written to keep working for a
long time with nobody maintaining it. Forked from a small internal base kit
for this exact shape of tool (search box, tick boxes, progress bar, log,
skip-what's-already-there, remembered download folder).

![the frog](app_icon.ico)

## What you get

Seven report categories, each a folder, each containing one `.txt` file per
year plus the current year:

- Legacy Report (Futures Only / Futures and Options Combined)
- Disaggregated Report (Futures Only / Futures and Options Combined)
- Traders in Financial Futures Report (Futures Only / Futures and Options Combined)
- Supplemental Report (Commodity Index Traders)

For each ticked category: every year CFTC has published a historical archive
for, from 1986 (Legacy) or later (the newer report types only go back to
2006-2010), plus the current year. The current year always comes from CFTC's
live, continuously-updated current-week file rather than that year's zip
archive, since the zip is not guaranteed to be as fresh.

Re-runs skip years already on disk. The download folder is chosen once and
remembered.

## Why this differs from the base kit it's forked from

CFTC is a static site, not a Next.js JSON feed: there's no per-page endpoint
to poll and no sitemap of "items" to crawl. The site publishes the same seven
report categories on two fixed pages, confirmed against the live pages'
section headings and link text (not guessed from filenames) on 2026-08-25.
That's why `fund_data.CATEGORIES` is a short hardcoded table rather than
something crawled — CFTC's report taxonomy essentially doesn't change,
unlike a fund roster. What *is* still rediscovered fresh every run is which
years actually have an archive, by scraping
`HistoricalCompressed/index.htm` each time (`fund_data.fetch_fund`).

Historical years arrive as a `.zip` with one `.txt` inside; `downloader.py`
extracts it and saves the plain text, so nothing needs manual unzipping
before it's usable. `downloader._DOC_NAMES` and `_ACRONYMS` are empty here —
document keys are just year strings, and those already read fine as-is.

## Weekly automation

`weekly_update.py` + `.github/workflows/weekly-cot-update.yml` run this unattended
every Friday via GitHub Actions: download the current year's Legacy (Futures Only)
report, extend the historical cache, compute positioning highlights (`analysis.py`),
commit the updated current-year file and the new report to the repo, and email the
report (`notify.py`, Gmail SMTP). See `CLAUDE.md` for the analysis scope and the
non-commodity exclusion list, and `weekly_update.py`'s own docstring for the
cache-vs-tracked-data split.

### One-time setup

Needs three GitHub Actions secrets on this repo, set once from your own terminal
(not something to script into the repo, since it's your Gmail credential):

1. Create a Google App Password at <https://myaccount.google.com/apppasswords>
   (needs 2FA already enabled on the Google account sending the mail).
2. Set the three secrets:
   ```
   gh secret set GMAIL_USER --repo AdamMooo/cot-scraper --body "your-gmail-address@gmail.com"
   gh secret set GMAIL_APP_PASSWORD --repo AdamMooo/cot-scraper
   gh secret set MAIL_TO --repo AdamMooo/cot-scraper --body "Adam.Morris0201@gmail.com"
   ```
   The middle one is left without `--body` on purpose — run it, then paste the app
   password when it waits for input, so it never lands in shell history.
3. Push this repo to `AdamMooo/cot-scraper` (it currently only exists locally with
   these changes). `workflow_dispatch` is enabled, so you can trigger a test run
   from the Actions tab immediately rather than waiting for Friday.

## Running and building

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

.venv\Scripts\python gui.py          # the app
.venv\Scripts\python scraper.py      # same engine, console version
.venv\Scripts\python build_exe.py    # -> dist/<APP_NAME>.exe
```

`requirements.txt` is build-only beyond `requests`. Pillow is used solely by
`generate_icon.py` to redraw `app_icon.ico`, and `build_exe.py` passes
`--exclude-module PIL` so it can never end up inside the shipped `.exe`.

## Why it should keep working

- **Retries with backoff** on every request (`http_client.py`).
- **A bad refresh cannot destroy a good list.** If discovering the category
  list fails outright, the last known-good list is kept.
- **Interrupted downloads cannot be mistaken for finished ones.** Files are
  written as `.part` and renamed only once complete — this covers the
  zip-extraction path too, since the final `.txt` is only written after the
  zip has been fully downloaded and read.
- **One category failing never ends the batch.**
- **Bundled multi-year archives are skipped automatically.** CFTC also
  publishes a few multi-year "hist" zips (e.g. `deacot1986_2016.zip`) that
  duplicate data already in the per-year files; the year-matching pattern in
  `fund_data.py` only matches a bare 4-digit year immediately before `.zip`,
  which these bundles never are, so they're never fetched.

## Sharing the .exe

It is unsigned, so Windows SmartScreen shows "Windows protected your PC" on
first run and the recipient has to click More info, then Run anyway. Tell
them that up front. Slack usually carries an `.exe` fine; Exchange strips it
from email, so use a link if Slack is blocked.

## Notes

- Windows only. It uses `os.startfile`, PowerShell for shortcut creation, and
  the hidden-file attribute.
- The app writes only beside its own executable: a hidden `App Files` folder
  holding the saved list and the chosen download folder.
- Text format only. No `.xls`/`.xlsx` variants are downloaded (deliberate —
  CFTC offers both for every category; text is smaller and easier to load
  into pandas/Excel later).
- The icon is pixel art deliberately. A taskbar icon is 24 physical pixels
  wide, and smoothly drawn art at that size smears; art authored on the pixel
  grid and scaled by whole numbers stays sharp.
