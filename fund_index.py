"""
Live fund index. Replaces a hand-maintained fund list with one built from the
site itself, so new fund launches show up automatically instead of silently
going missing (the hardcoded list this started from was already ~12 funds stale
against the live sitemap when this was written, 2026-08-19).

Public interface:
    FundEntry            -- {"name": str, "slug": str, "tickers": list[str]}
    get_fund_index(log, force_refresh=False) -> list[FundEntry]
"""

import json
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TypedDict

import fund_data
import site_config
from http_client import get_session
from paths import FUND_LIST_FILE, SKIPPED_FILE, support_dir

SITEMAP_URL = fund_data.BASE + "/sitemap.xml"
_ITEM_PATH_RE = re.compile(re.escape(site_config.ITEM_PATH) + r"([a-z0-9-]+)/?$")
_MAX_WORKERS = 10

# A refresh that comes back with far fewer items than usual is much more
# likely to mean the site's sitemap or JSON structure changed than that the
# site really removed nearly everything. Since this tool gets no updates
# after launch, guard against a broken refresh overwriting a good cache.
# Raise this if the site you point at legitimately has many pages.
_MIN_PLAUSIBLE_FUND_COUNT = 20


class FundEntry(TypedDict):
    name: str
    slug: str
    tickers: list[str]


def _fetch_slugs_from_sitemap() -> list[str]:
    """Return every fund slug listed in the live sitemap, in sitemap order."""
    resp = get_session().get(SITEMAP_URL, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    slugs: list[str] = []
    seen: set[str] = set()
    for elem in root.iter():
        if not elem.tag.endswith("loc") or not elem.text:
            continue
        m = _ITEM_PATH_RE.search(elem.text.strip())
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            slugs.append(m.group(1))
    return slugs


def _fetch_slugs_from_html() -> list[str]:
    """Fallback slug source: scrape /funds/<slug> links out of the site's HTML.

    Used only if sitemap.xml is unreachable or stops listing fund pages. Less
    precise than the sitemap (a listing page may paginate), but it means a
    single site change can't leave this tool with no way to find funds at all.
    """
    slugs: list[str] = []
    seen: set[str] = set()
    for path in (site_config.ITEM_PATH, "/"):
        try:
            html = get_session().get(fund_data.BASE + path, timeout=30).text
        except Exception:
            continue
        for match in re.finditer(_ITEM_PATH_RE.pattern.rstrip("/?$"), html):
            slug = match.group(1)
            if slug not in seen:
                seen.add(slug)
                slugs.append(slug)
    return slugs


def _fetch_entry(build_id: str, slug: str) -> FundEntry | str:
    """Return the fund's entry, or a string explaining why it isn't a fund.

    Returning the reason rather than None lets _build_fund_index account for
    every page it looked at, so the totals it reports always add up.
    """
    try:
        fd = fund_data.fetch_fund(build_id, slug)
    except fund_data.NotAFundPage as exc:
        return f"{slug}: {exc}"
    except Exception as exc:
        return f"{slug}: could not be read ({exc})"

    name = fd.get("name") or slug.replace("-", " ").title()
    tickers = sorted({
        s.get("code") for s in (fd.get("series", {}) or {}).values() if s.get("code")
    })
    return {"name": name, "slug": slug, "tickers": tickers}


def _build_fund_index(log) -> list[FundEntry]:
    log(f"Getting the list from {site_config.SITE_NAME} ...")
    build_id = fund_data.discover_build_id()

    try:
        slugs = _fetch_slugs_from_sitemap()
    except Exception as exc:
        log(f"Sitemap unavailable ({exc}). Scanning site links instead ...")
        slugs = []
    if not slugs:
        log("No fund pages in the sitemap. Scanning site links instead ...")
        slugs = _fetch_slugs_from_html()

    entries: list[FundEntry] = []
    skipped: list[str] = []
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        futures = {pool.submit(_fetch_entry, build_id, slug): slug for slug in slugs}
        for future in as_completed(futures):
            result = future.result()
            if isinstance(result, str):
                skipped.append(result)
            else:
                entries.append(result)

    entries.sort(key=lambda e: e["name"])

    # Only the fund count is reported. Some /funds/ URLs are marketing pages
    # with no documents, and mentioning a larger "pages checked" number just
    # invites the question of where the difference went.
    if skipped:
        _log_skipped(skipped)

    return entries


def _log_skipped(skipped: list[str]) -> None:
    """Record non-fund pages, for whoever looks into this later."""
    try:
        (support_dir() / SKIPPED_FILE).write_text("\n".join(sorted(skipped)), encoding="utf-8")
    except OSError:
        pass


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
    """Slugs from the saved list, for spotting funds that appeared since."""
    return {e["slug"] for e in (_load_cache() or [])}


def refresh_and_find_new(log=print) -> tuple[list[FundEntry], list[FundEntry]]:
    """Re-read the site and return (all funds, funds not in the saved list).

    Called on every launch so a newly launched fund shows up on its own. The
    person using this should never have to know that a refresh button exists.
    """
    known = cached_slugs()
    entries = get_fund_index(log=log, force_refresh=True)
    new = [e for e in entries if e["slug"] not in known] if known else []
    return entries, new


def get_fund_index(log=print, force_refresh: bool = False) -> list[FundEntry]:
    """Return the current fund list. Cached on disk after the first fetch.

    Falls back to the disk cache if a forced refresh's network call fails, or
    if it succeeds but returns an implausibly small list (more likely a site
    structure change breaking the parser than a mass fund delisting). This
    tool has no maintainer to fix that after the fact, so it must never let a
    broken refresh quietly overwrite a working cache.
    """
    cached = None if force_refresh else _load_cache()
    if cached is not None:
        log(f"Loaded {len(cached)} funds from cache.")
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
                f"Warning: the site returned only {len(entries)} items. "
                f"The site may have changed. Keeping the last known-good list of "
                f"{len(cached)} funds instead."
            )
            return cached
        log(f"Warning: only found {len(entries)} funds, so this list may be incomplete.")

    _save_cache(entries)
    log(f"Fund list ready: {len(entries)} funds.")
    return entries
