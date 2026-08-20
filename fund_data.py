"""
Minimal Next.js JSON feed client for one website.

Public interface:
    BASE                       -- site root, taken from site_config
    NotAFundPage               -- raised for /funds/ URLs that aren't funds
    discover_build_id()        -> str
    fetch_fund(build_id, slug) -> dict  (pageProps.fundData)

The site's buildId rotates on every deploy, so it is rediscovered per run and
never hardcoded. Page URLs can also start redirecting when the site renames
something, so fetch_fund follows the redirect rather than giving up. Both behaviours matter because this tool ships without a maintainer.
"""

import json
import re

import site_config
from http_client import get_session

BASE = site_config.SITE_BASE

_ITEM_PATH_RE = re.compile(re.escape(site_config.ITEM_PATH) + r"([a-z0-9-]+)")
_MAX_REDIRECTS = 3


class NotAFundPage(Exception):
    """A /funds/ URL that doesn't serve fund data (marketing page, retired fund)."""


def _get(url: str) -> bytes:
    resp = get_session().get(url, timeout=30)
    resp.raise_for_status()
    return resp.content


def discover_build_id() -> str:
    """Discover the current Next.js buildId from the homepage HTML.

    The regex runs on a fresh GET each call; no hardcoded hash is ever stored.
    """
    html = _get(BASE + "/").decode("utf-8", "replace")
    m = re.search(r'"buildId":"([^"]+)"', html)
    if not m:
        raise RuntimeError(f"Could not find buildId on {site_config.SITE_NAME}")
    return m.group(1)


def fetch_fund(build_id: str, slug: str) -> dict:
    """Return pageProps.fundData for a fund, following fund-to-fund redirects.

    A renamed fund's old URL answers with a Next.js redirect instead of fund
    data. When that redirect points at another /funds/ page, it is followed so
    the fund is still found under its new slug. Redirects to anywhere else
    (a marketing page, the fund listing) mean this URL is not a fund, which
    raises NotAFundPage so callers can report it rather than treat it as an
    unexplained failure.
    """
    seen: set[str] = set()

    for _ in range(_MAX_REDIRECTS):
        if slug in seen:
            raise NotAFundPage(f"redirect loop at '{slug}'")
        seen.add(slug)

        url = (
            f"{BASE}/_next/data/{build_id}/en-CA"
            f"{site_config.ITEM_PATH}{slug}.json?id={slug}"
        )
        page_props = json.loads(_get(url).decode("utf-8", "replace")).get("pageProps", {})

        if "fundData" in page_props:
            return page_props["fundData"]

        target = page_props.get("__N_REDIRECT")
        if not target:
            raise NotAFundPage(f"no fund data at '{slug}'")

        match = _ITEM_PATH_RE.search(target)
        if not match:
            raise NotAFundPage(f"'{slug}' redirects to '{target}', not a fund page")
        slug = match.group(1)

    raise NotAFundPage(f"too many redirects starting from '{slug}'")
