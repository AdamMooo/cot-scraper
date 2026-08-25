"""
Weekly automated pull + analysis. Run by .github/workflows/weekly-cot-update.yml
every Friday, shortly after CFTC's COT release.

Downloads go into .cot-cache/ (gitignored, persisted across runs via GitHub
Actions cache) so the full historical backfill is only ever fetched once.
Only the current year's file is copied into data/ (git-tracked) each run,
which is what keeps the repo itself small: historical years don't change
once posted, so there's nothing worth committing about them every week.

v1 scope is one report category (see TARGET_SLUG below). See CLAUDE.md for
why, and for how to add more categories to this script later.
"""

import shutil
import sys
from datetime import date
from pathlib import Path

import analysis
import downloader
import fund_index
import notify

REPO_ROOT = Path(__file__).resolve().parent
CACHE_ROOT = REPO_ROOT / ".cot-cache"
DATA_ROOT = REPO_ROOT / "data"
REPORTS_ROOT = REPO_ROOT / "reports"

TARGET_SLUG = "legacy_futures_only"


def main() -> None:
    entries = fund_index.get_fund_index(log=print)
    target = next(e for e in entries if e["slug"] == TARGET_SLUG)

    result = downloader.run_download([(target["name"], target["slug"])], CACHE_ROOT, log=print)
    print(result)
    if result.failed:
        raise RuntimeError(f"{len(result.failed)} document(s) failed to download: {result.failed}")

    category_folder = downloader.safe_name(target["name"], fallback=downloader.safe_name(target["slug"], "fund"))
    category_dir = CACHE_ROOT / category_folder

    current_year_file = category_dir / f"{date.today().year}.txt"
    if not current_year_file.exists():
        raise RuntimeError(f"expected {current_year_file} after a successful download, but it's missing")

    tracked_dir = DATA_ROOT / category_folder
    tracked_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(current_year_file, tracked_dir / current_year_file.name)

    by_market = analysis.load_category_rows(category_dir)
    report_md = analysis.build_report(by_market, title=target["name"])

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
