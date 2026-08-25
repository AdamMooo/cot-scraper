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

import io
import re
import zipfile
from pathlib import Path
from typing import NamedTuple

import fund_data
from http_client import get_session

# Document keys here are plain year strings ("2024"), which already read
# fine after title-casing, so no per-key display-name map is needed.
_DOC_NAMES: dict[str, str] = {}
_ACRONYMS: dict[str, str] = {}

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


def _download_and_extract_zip(url: str, output_path: Path, log) -> bool:
    """Download a yearly archive and save its one .txt member as plain text.

    CFTC ships each historical year as a zip with a single delimited .txt
    file inside. Saving the extracted text rather than the zip is what makes
    the output directly usable later without a manual unzip step.
    """
    part_path = output_path.with_name(output_path.name + ".part")
    try:
        resp = get_session().get(url, timeout=60)
        resp.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".txt")]
            if not names:
                raise ValueError("no .txt file inside the archive")
            data = zf.read(names[0])

        part_path.write_bytes(data)
        part_path.replace(output_path)

        log(f"    Saved {output_path.name} ({len(data):,} bytes)")
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
        output_path = fund_folder / f"{file_stem}.txt"
        # Only a historical (extract=True) year is immutable once posted. The
        # current year's plain-text file is CFTC's continuously-updated feed,
        # so it must never be treated as "already have it" -- it's re-fetched
        # and overwritten every run even if a file of that name exists.
        if entry.get("extract") and output_path.exists():
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
        download = _download_and_extract_zip if entry.get("extract") else _download_file
        if download(url, output_path, log):
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
