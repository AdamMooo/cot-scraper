"""
Report category index. Unlike a fund site's list of funds, CFTC's seven COT
report categories are a fixed taxonomy (see fund_data.CATEGORIES), not
something to crawl a sitemap for. What this module still gives the app is
the same cached-list-with-refresh-banner behaviour the GUI already expects,
in case that taxonomy ever changes underneath us.

Public interface:
    FundEntry            -- {"name": str, "slug": str, "tickers": list[str]}
    get_fund_index(log, force_refresh=False) -> list[FundEntry]
"""

import json
from pathlib import Path
from typing import TypedDict

import fund_data
import site_config
from paths import FUND_LIST_FILE, support_dir

# The category list is fixed in code, so a count below this only happens if
# fund_data.CATEGORIES itself is broken, not from a real site change.
_MIN_PLAUSIBLE_FUND_COUNT = 7


class FundEntry(TypedDict):
    name: str
    slug: str
    tickers: list[str]


def _build_fund_index(log) -> list[FundEntry]:
    log(f"Getting the list from {site_config.SITE_NAME} ...")
    fund_data.discover_build_id()

    entries: list[FundEntry] = [
        {"name": name, "slug": slug, "tickers": []}
        for slug, name, _current_path, _hist_prefix in fund_data.CATEGORIES
    ]
    entries.sort(key=lambda e: e["name"])
    return entries


def _cache_path() -> Path:
    return support_dir() / FUND_LIST_FILE


def _load_cache() -> list[FundEntry] | None:
    path = _cache_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _save_cache(entries: list[FundEntry]) -> None:
    try:
        _cache_path().write_text(json.dumps(entries, indent=2), encoding="utf-8")
    except OSError:
        pass  # the saved list is a convenience, not a requirement


def cached_slugs() -> set[str]:
    """Slugs from the saved list, for spotting categories that appeared since."""
    return {e["slug"] for e in (_load_cache() or [])}


def refresh_and_find_new(log=print) -> tuple[list[FundEntry], list[FundEntry]]:
    """Re-read the site and return (all reports, reports not in the saved list)."""
    known = cached_slugs()
    entries = get_fund_index(log=log, force_refresh=True)
    new = [e for e in entries if e["slug"] not in known] if known else []
    return entries, new


def get_fund_index(log=print, force_refresh: bool = False) -> list[FundEntry]:
    """Return the current report category list. Cached on disk after the first fetch.

    Falls back to the disk cache if a forced refresh fails outright, or comes
    back with fewer categories than expected -- more likely a code or network
    problem than CFTC actually retiring a report type.
    """
    cached = None if force_refresh else _load_cache()
    if cached is not None:
        log(f"Loaded {len(cached)} reports from cache.")
        return cached

    try:
        entries = _build_fund_index(log)
    except Exception as exc:
        cached = _load_cache()
        if cached is not None:
            log(f"Could not refresh from the site ({exc}). Using the saved list.")
            return cached
        raise

    if len(entries) < _MIN_PLAUSIBLE_FUND_COUNT:
        cached = _load_cache()
        if cached is not None and len(cached) >= _MIN_PLAUSIBLE_FUND_COUNT:
            log(
                f"Warning: only found {len(entries)} report categories. "
                f"Keeping the last known-good list of {len(cached)} instead."
            )
            return cached
        log(f"Warning: only found {len(entries)} report categories, so this list may be incomplete.")

    _save_cache(entries)
    log(f"Report list ready: {len(entries)} categories.")
    return entries
