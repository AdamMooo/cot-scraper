# web-scraper

A base for building small, shareable Windows apps that pull every document off
a website's pages and file them one folder per page.

The point of it is the packaging and the durability, not the scraping. It builds
to a single `.exe` you can hand to somebody non-technical, it needs no Python or
credentials on their machine, and it is written to keep working for a long time
with nobody maintaining it.

![the frog](app_icon.ico)

## What you get

- A window with a search box, tick boxes, a progress bar and a log.
- The list of pages is read from the site **every launch**, never hardcoded, so
  new pages appear on their own and raise a banner naming them.
- Every document on each page is downloaded, whatever is posted that day. There
  is no fixed list of document types to keep in step with the site.
- Re-runs skip what is already on disk, and anything already downloaded is
  marked "saved" in the list.
- The download folder is chosen by the user and remembered, so it can point at a
  synced SharePoint or OneDrive folder and sync onward from there.
- Start Menu shortcut creation, so it can be pinned to the taskbar.

## Pointing it at a different site

Start with `site_config.py`. For a site that, like the one this was written
against, is a Next.js app serving its pages from a JSON data endpoint, that file
plus nothing else may be enough:

```python
SITE_BASE = "https://www.example.com"
SITE_NAME = "example.com"
ITEM_PATH = "/funds/"          # pages live at SITE_BASE + ITEM_PATH + "<slug>"
APP_NAME  = "Document Downloader"
ITEM_WORD, ITEM_WORD_PL = "fund", "funds"
```

For any other kind of site, three functions carry all the remaining assumptions:

| Function | Assumes | Change it when |
|---|---|---|
| `fund_data.discover_build_id` | Next.js, with a rotating `buildId` in the homepage HTML | The site is not Next.js. Delete it and its argument |
| `fund_data.fetch_fund` | `"/_next/data/<buildId>/en-CA<ITEM_PATH><slug>.json"` returns `pageProps.fundData` | Always, unless the site matches that shape |
| `fund_index._fetch_entry` | The payload has `name` and `series[].code` | The payload names things differently |
| `downloader._process_fund` | Documents live at `documents.fund` in the payload, as `{key: {url}}` | The payload nests documents elsewhere |

`downloader._DOC_NAMES` maps the site's internal document keys to readable
filenames. It is only cosmetic: unmapped keys fall back to a title-cased version
of the key, so a partial map is fine and a new document type never needs code.

Everything else is site-agnostic and worth leaving alone: the GUI, the download
engine, settings, paths, retrying, the icon and the frog.

## Why it should keep working

Written on the assumption that nobody will patch it after handover:

- **It reads the site's own data feed**, not the rendered HTML. A visual
  redesign does not break it, and there is no browser driver to keep in step
  with a browser version.
- **Two independent ways to find pages.** The sitemap first, then scraping the
  site's own links. Losing one does not stop it.
- **Renames are followed.** A page that starts redirecting is followed to its
  new home; a redirect out of the section is reported as "not one of these
  pages" rather than as a mystery failure.
- **A bad refresh cannot destroy a good list.** If a refresh returns
  implausibly little, the last known-good list is kept and the user is told.
- **Retries with backoff** on every request.
- **Failures stay visible.** "No documents anywhere" is counted separately from
  "already downloaded", so a site change can never read as "nothing new today".
- **Interrupted downloads cannot be mistaken for finished ones.** Files are
  written as `.part` and renamed only once complete.
- **One page failing never ends the batch.**
- **Values from the site are sanitised before becoming file paths**, so a
  hostile or malformed key cannot write outside the download folder.

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

## Sharing the .exe

It is unsigned, so Windows SmartScreen shows "Windows protected your PC" on
first run and the recipient has to click More info, then Run anyway. Tell them
that up front. Slack usually carries an `.exe` fine; Exchange strips it from
email, so use a link if Slack is blocked.

## Notes

- Windows only. It uses `os.startfile`, PowerShell for shortcut creation, and
  the hidden-file attribute.
- The app writes only beside its own executable: a hidden `App Files` folder
  holding the saved list and the chosen download folder.
- The icon is pixel art deliberately. A taskbar icon is 24 physical pixels wide,
  and smoothly drawn art at that size smears; art authored on the pixel grid and
  scaled by whole numbers stays sharp. `generate_icon.py` renders each icon size
  separately for the same reason.
