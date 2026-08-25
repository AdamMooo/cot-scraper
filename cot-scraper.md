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

Built, tested locally end-to-end, **not yet pushed to GitHub or deployed** -- the GitHub
Actions secrets (Gmail App Password) still need setting from the user's own terminal
(credential setup Claude won't do), and nothing has been pushed to `AdamMooo/cot-scraper`
yet. See `README.md` "One-time setup" for the exact commands.

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

Not pushed to `AdamMooo/cot-scraper` yet, and the three GitHub Actions secrets
(`GMAIL_USER`, `GMAIL_APP_PASSWORD`, `MAIL_TO`) aren't set, so the workflow can't
successfully run until both happen. No `.venv` created for this repo -- ran against system
Python 3.13 during development. `build_exe.py` untested against this fork (not the current
priority). Analysis covers only the Legacy (Futures Only) report; Disaggregated/TFF
breakdowns (Managed Money vs. Producer positioning) are a possible fast follow, not done.

## Memory

[[project_cot_scraper|project memory]] in the purpose-doc-scraper session's memory store
has the cross-session summary of why this exists and the key design calls.
