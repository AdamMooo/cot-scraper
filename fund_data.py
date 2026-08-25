"""
CFTC Commitments of Traders (COT) report categories and their download URLs.

Unlike the fund site this tool started from, there is no per-item webpage to
fetch and no slug space to discover from a sitemap: CFTC publishes the same
seven report categories on two static pages, and both the current-week URL
and the historical zip-file naming for each were confirmed against the live
pages on 2026-08-25 (link text and section headings, not guessed from
filenames). That taxonomy is fixed the same way fund_data.BASE is fixed on
the original site -- it only needs updating if CFTC adds or retires a report
category, not on every run.

What *is* rediscovered every run is which years actually have a historical
archive, by scraping HistoricalCompressed/index.htm fresh each time. The
current year is always served from the live current-week file, not a zip,
even when a same-year zip also exists -- CFTC keeps the current-week file
continuously up to date, so it is the fresher of the two.

Public interface:
    BASE                        -- site root, taken from site_config
    CATEGORIES                  -- (slug, name, current_path, hist_prefix) tuples
    NotAFundPage                -- raised for an unrecognised category slug
    discover_build_id()         -> str  (fetches and caches the historical page)
    fetch_fund(build_id, slug)  -> dict (name, series, documents.fund)
"""

import re
from datetime import date

import site_config
from http_client import get_session

BASE = site_config.SITE_BASE

_HISTORICAL_PAGE = BASE + "/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm"

# The historical prefix is matched as "<prefix>_?(\d{4})\.zip". CFTC is
# inconsistent about the underscore before the year (deahistfo_1995.zip vs
# deahistfo2004.zip) but always keeps a bare 4-digit year right before
# ".zip", which conveniently also excludes the bundled multi-year archives
# (e.g. deacot1986_2016.zip, dea_cit_txt_2006_2016.zip): the digits there are
# followed by another "_", not ".zip", so they never match.
CATEGORIES = [
    ("legacy_futures_only", "Legacy Report (Futures Only)",
     "/dea/newcot/deafut.txt", "/files/dea/history/deacot"),
    ("legacy_combined", "Legacy Report (Futures and Options Combined)",
     "/dea/newcot/deacom.txt", "/files/dea/history/deahistfo"),
    ("disaggregated_futures_only", "Disaggregated Report (Futures Only)",
     "/dea/newcot/f_disagg.txt", "/files/dea/history/fut_disagg_txt_"),
    ("disaggregated_combined", "Disaggregated Report (Futures and Options Combined)",
     "/dea/newcot/c_disagg.txt", "/files/dea/history/com_disagg_txt_"),
    ("tff_futures_only", "Traders in Financial Futures Report (Futures Only)",
     "/dea/newcot/FinFutWk.txt", "/files/dea/history/fut_fin_txt_"),
    ("tff_combined", "Traders in Financial Futures Report (Futures and Options Combined)",
     "/dea/newcot/FinComWk.txt", "/files/dea/history/com_fin_txt_"),
    ("supplemental_cit", "Supplemental Report (Commodity Index Traders)",
     "/dea/newcot/deacit.txt", "/files/dea/history/dea_cit_txt_"),
]
_BY_SLUG = {slug: (name, current_path, hist_prefix) for slug, name, current_path, hist_prefix in CATEGORIES}

_cache: dict[str, str] = {}


class NotAFundPage(Exception):
    """Raised for a category slug this build doesn't know about."""


def _get_text(url: str) -> str:
    resp = get_session().get(url, timeout=30)
    resp.raise_for_status()
    return resp.content.decode("utf-8", "replace")


def discover_build_id() -> str:
    """Fetch and cache the historical archive page.

    Called once at the start of a run (index build or download) so every
    category sees one consistent snapshot of what years are available,
    rather than each category re-fetching the same page separately.
    """
    _cache["historical"] = _get_text(_HISTORICAL_PAGE)
    return "cftc"  # no real build id on this site; kept for interface parity


def fetch_fund(build_id: str, slug: str) -> dict:
    """Return a fund-shaped payload: name, empty series, and a document dict
    of {year_string: {"url", "extract"}} under documents.fund.

    "extract" marks a historical year as a zip that needs its one .txt
    member pulled out, versus the current year's plain text file.
    """
    entry = _BY_SLUG.get(slug)
    if entry is None:
        raise NotAFundPage(f"unknown report category '{slug}'")
    name, current_path, hist_prefix = entry

    if "historical" not in _cache:
        discover_build_id()

    documents: dict[str, dict] = {}
    pattern = re.compile(re.escape(hist_prefix) + r"_?(\d{4})\.zip")
    for match in pattern.finditer(_cache["historical"]):
        documents[match.group(1)] = {"url": BASE + match.group(0), "extract": True}

    documents[str(date.today().year)] = {"url": BASE + current_path, "extract": False}

    return {"name": name, "series": {}, "documents": {"fund": documents}}
