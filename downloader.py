"""
Shared download engine.

Both the CLI (scraper.py) and the GUI (gui.py) call run_download() so there is
exactly one tested code path for "read a fund's page and save its documents".
A UI change can't silently produce different downloads than the CLI.

Public interface:
    DownloadResult                 -- counts plus per-fund problems
    friendly_doc_name(doc_type)    -> readable document name
    safe_name(raw, fallback)       -> one safe path segment
    run_download(...)              -> DownloadResult
"""

import re
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlparse

import fund_data
from http_client import get_session

# The feed names documents with internal keys. These are the readable names
# used for saved files, so the folders make sense to someone browsing them in
# Explorer or SharePoint. Unknown keys fall back to a tidied version of the
# key itself, so a document type added later still saves with a sane name.
_DOC_NAMES: dict[str, str] = {
    "fund_facts": "Fund Facts",
    "etf_facts": "ETF Facts",
    "mrfp": "Management Report of Fund Performance (MRFP)",
    "prospectus": "Prospectus",
    "financial_statements": "Financial Statements",
    "quarterly_portfolio_disclosure": "Quarterly Portfolio Disclosure",
    "pfic": "PFIC Annual Information Statement",
    "brochure": "Brochure",
    "commentary": "Commentary",
    "annual_information_form": "Annual Information Form",
    "offering_memorandum": "Offering Memorandum",
    "subscription_agreement": "Subscription Agreement",
    "amendment": "Amendment",
    "fund_review": "Fund Review",
    "quarterly_report": "Quarterly Report",
    "educational": "Educational Material",
    "etf_facts_-_carbon_offset": "ETF Facts (Carbon Offset)",
}

# Title-casing an unmapped key would render these as "Etf" or "Mrfp".
_ACRONYMS = {
    "Etf": "ETF", "Mrfp": "MRFP", "Pfic": "PFIC", "Aif": "AIF",
    "Nav": "NAV", "Esg": "ESG", "Us": "US", "Faq": "FAQ",
}

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# Windows refuses these as filenames regardless of extension.
_RESERVED_NAMES = frozenset({
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
})


class DownloadResult(NamedTuple):
    downloaded: int
    skipped: int
    failed: list[tuple[str, str]]
    funds_with_no_docs: int
    funds_attempted: int

    @property
    def looks_like_site_changed(self) -> bool:
        """True when nothing returned any document at all.

        Pages normally post several documents each, so a run where
        nothing anywhere has documents points at the site changing shape rather
        than at a genuinely empty result. Worth telling the user plainly,
        because otherwise it reads as a quiet "nothing new".
        """
        return self.funds_attempted > 0 and self.funds_with_no_docs == self.funds_attempted


def friendly_doc_name(doc_type: str) -> str:
    """Return a readable document name for a feed document key.

    Known keys get a proper name. Anything the site adds later falls back to a
    tidied version of the key, so a new document type still saves under a
    sensible filename instead of needing a code change.
    """
    if doc_type in _DOC_NAMES:
        return _DOC_NAMES[doc_type]

    words = [_ACRONYMS.get(w, w) for w in doc_type.replace("_", " ").strip().title().split()]
    return " ".join(words) or "Document"


def safe_name(raw: str, fallback: str) -> str:
    """Turn untrusted text into a single safe path segment.

    Fund names and document keys both come from the website, so they are
    treated as untrusted input: a value containing separators or ".." would
    otherwise be able to steer writes outside the chosen download folder.
    """
    cleaned = _INVALID_CHARS.sub("", raw).replace("..", "").strip()
    cleaned = cleaned.strip(". ")  # Windows drops trailing dots and spaces
    if not cleaned:
        return fallback
    if cleaned.upper() in _RESERVED_NAMES:
        return f"{cleaned} file"
    return cleaned[:120].strip()


def _file_extension(url: str) -> str:
    """Return the file's real extension from its URL path (default .pdf)."""
    suffix = Path(urlparse(url).path).suffix
    return suffix if len(suffix) <= 6 else ".pdf"


def _download_file(url: str, output_path: Path, log) -> bool:
    part_path = output_path.with_name(output_path.name + ".part")
    try:
        resp = get_session().get(url, timeout=60)
        resp.raise_for_status()

        # Write to a temp file and rename only once the whole body is on disk.
        # A half-written file left by a dropped connection would otherwise look
        # complete to the skip-if-exists check and never be retried.
        part_path.write_bytes(resp.content)
        part_path.replace(output_path)

        log(f"    Saved {output_path.name} ({len(resp.content):,} bytes)")
        return True
    except Exception as exc:
        log(f"    Could not download {output_path.name}: {exc}")
        try:
            part_path.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def _process_fund(
    fund_name: str,
    slug: str,
    build_id: str,
    download_root: Path,
    log,
    counters: dict,
    failed_list: list[tuple[str, str]],
) -> None:
    log(f"\n{fund_name}")

    try:
        fd = fund_data.fetch_fund(build_id, slug)
    except fund_data.NotAFundPage as exc:
        log(f"  Nothing to download here ({exc})")
        counters["no_docs"] += 1
        return
    except Exception as exc:
        reason = f"could not read the fund page ({exc})"
        log(f"  Problem: {reason}")
        failed_list.append((fund_name, reason))
        return

    fund_docs = (fd.get("documents", {}) or {}).get("fund", {}) or {}
    fund_folder = download_root / safe_name(fund_name, fallback=safe_name(slug, "fund"))

    any_doc = False
    for doc_type, entry in fund_docs.items():
        if not isinstance(entry, dict):
            continue
        url = entry.get("url")
        if not url:
            continue
        any_doc = True

        file_stem = safe_name(friendly_doc_name(doc_type), fallback="Document")
        output_path = fund_folder / f"{file_stem}{_file_extension(url)}"
        if output_path.exists():
            log(f"  Already have {output_path.name}")
            counters["skipped"] += 1
            continue

        try:
            fund_folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            # Most likely an over-long path inside a deep synced folder. Report
            # it against this fund and move on rather than ending the batch.
            reason = f"could not create its folder ({exc})"
            log(f"  Problem: {reason}")
            failed_list.append((fund_name, reason))
            return

        log(f"  Getting {file_stem} ...")
        if _download_file(url, output_path, log):
            counters["downloaded"] += 1
        else:
            failed_list.append((fund_name, f"could not download {file_stem}"))

    if not any_doc:
        log("  No documents posted here right now")
        counters["no_docs"] += 1


def run_download(
    funds: list[tuple[str, str]],
    download_root: Path,
    log=print,
    on_fund_done=None,
) -> DownloadResult:
    """Download every document posted for each (name, slug) pair.

    Calls log(str) for every progress line so a GUI can route it into a text
    widget, and on_fund_done(done, total) after each fund so a GUI can drive a
    progress bar. One fund failing never stops the rest of the batch.
    """
    log("Checking the website ...")
    build_id = fund_data.discover_build_id()
    download_root.mkdir(parents=True, exist_ok=True)

    counters = {"downloaded": 0, "skipped": 0, "no_docs": 0}
    failed: list[tuple[str, str]] = []

    for i, (fund_name, slug) in enumerate(funds, start=1):
        try:
            _process_fund(fund_name, slug, build_id, download_root, log, counters, failed)
        except Exception as exc:
            log(f"  Problem: unexpected error ({exc})")
            failed.append((fund_name, f"unexpected error ({exc})"))
        if on_fund_done is not None:
            on_fund_done(i, len(funds))

    return DownloadResult(
        downloaded=counters["downloaded"],
        skipped=counters["skipped"],
        failed=failed,
        funds_with_no_docs=counters["no_docs"],
        funds_attempted=len(funds),
    )
