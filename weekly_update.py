"""
Weekly automated pull + analysis. Run by .github/workflows/weekly-cot-update.yml
every Friday, shortly after CFTC's COT release.

Downloads go into .cot-cache/ (gitignored, persisted across runs via GitHub
Actions cache) so the full historical backfill is only ever fetched once.
The current year is different: CFTC's own current-year file is only ever
this week's single snapshot per market, not a running year-to-date file, so
this script merges each week's snapshot into data/<category>/<year>.txt
(git-tracked) rather than overwriting it -- that accumulated file is what
gives analysis.py a real week-over-week history for the current year until
CFTC eventually posts it as a proper historical archive.

Two report categories: Legacy (the commodity section) and Traders in
Financial Futures (the portfolio section, see portfolio.py). Each run also
merges CFTC's current-year archive zip, so a missed week backfills itself.
"""

import shutil
import sys
from datetime import date
from pathlib import Path

import analysis
import downloader
import fund_data
import fund_index
import notify
import portfolio

REPO_ROOT = Path(__file__).resolve().parent
CACHE_ROOT = REPO_ROOT / ".cot-cache"
DATA_ROOT = REPO_ROOT / "data"
REPORTS_ROOT = REPO_ROOT / "reports"

COMMODITY_SLUG = "legacy_futures_only"
PORTFOLIO_SLUG = "tff_futures_only"


def _refresh(entry: dict) -> Path:
    """Download one category, accumulate its current year, return its cache folder."""
    result = downloader.run_download([(entry["name"], entry["slug"])], CACHE_ROOT, log=print)
    print(result)
    if result.failed:
        raise RuntimeError(f"{len(result.failed)} document(s) failed to download: {result.failed}")

    category_folder = downloader.safe_name(entry["name"], fallback=downloader.safe_name(entry["slug"], "fund"))
    category_dir = CACHE_ROOT / category_folder
    current_year_file = category_dir / f"{date.today().year}.txt"
    if not current_year_file.exists():
        raise RuntimeError(f"expected {current_year_file} after a successful download, but it's missing")

    tracked_file = DATA_ROOT / category_folder / current_year_file.name
    archive_url = fund_data.current_year_archive_url(entry["slug"])
    archive_file = category_dir / "current-year-archive.tmp"  # not *.txt, so never loaded twice
    if archive_url and downloader._download_and_extract_zip(archive_url, archive_file, print):
        analysis.merge_current_year_snapshot(archive_file, tracked_file)
        archive_file.unlink()
    analysis.merge_current_year_snapshot(current_year_file, tracked_file)
    # Sync the merged (accumulated) file back over the cache's copy so the
    # analysis below sees the full current-year history, not just this
    # week's single-row snapshot that run_download just wrote there.
    shutil.copy2(tracked_file, current_year_file)
    return category_dir


def main() -> None:
    # prices.py never refetches a ticker it has on disk, and .cot-cache/ is
    # restored by actions/cache, so a cached price file would freeze every
    # week's prices at whatever the run that saved the cache saw.
    shutil.rmtree(CACHE_ROOT / "prices", ignore_errors=True)
    entries = {e["slug"]: e for e in fund_index.get_fund_index(log=print)}
    commodity_dir = _refresh(entries[COMMODITY_SLUG])
    tff = portfolio.load_tff(_refresh(entries[PORTFOLIO_SLUG]))

    report_md = analysis.build_report(analysis.load_category_rows(commodity_dir),
                                      lead=lambda rows: portfolio.build_section(tff, rows))

    REPORTS_ROOT.mkdir(exist_ok=True)
    today = date.today().isoformat()
    (REPORTS_ROOT / f"{today}.md").write_text(report_md, encoding="utf-8")
    (REPORTS_ROOT / "latest.md").write_text(report_md, encoding="utf-8")

    notify.send_email(subject=f"COT Weekly Report - {today}", body_markdown=report_md)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"weekly_update failed: {exc}", file=sys.stderr)
        try:
            notify.send_email(
                subject="COT Weekly Report - FAILED",
                body_markdown=f"The weekly update failed and did not produce a report:\n\n{exc}",
            )
        except Exception as notify_exc:
            print(f"  (and the failure email could not be sent either: {notify_exc})", file=sys.stderr)
        raise
