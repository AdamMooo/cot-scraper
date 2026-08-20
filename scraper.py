"""
Console version of the document downloader.

Lists every page currently on the target site (read live, never a hardcoded
list), lets you pick which ones to fetch, then downloads every document
posted on each page into a folder named after it.

gui.py is the version that actually ships. This one exists for quick checks
from a terminal and shares the same download engine, so both behave alike.

Run:
    python scraper.py
"""

import sys

import site_config
from downloader import run_download
from fund_index import get_fund_index
from settings import get_download_root


def _parse_selection(raw: str, count: int) -> list[int]:
    """Parse "1,4,9" / "1-5" / "all" into a sorted, deduped list of 0-based indices."""
    raw = raw.strip().lower()
    if raw == "all":
        return list(range(count))

    indices: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            indices.update(range(int(start) - 1, int(end)))
        else:
            indices.add(int(part) - 1)

    return sorted(i for i in indices if 0 <= i < count)


def main() -> int:
    funds = get_fund_index(log=print)

    print(f"\n{site_config.APP_NAME}\n")
    for i, entry in enumerate(funds, start=1):
        label = entry["name"]
        if entry["tickers"]:
            label += f" ({', '.join(entry['tickers'])})"
        print(f"  {i:>3}. {label}")

    print()
    raw = input('Enter fund numbers (e.g. 1,4,9), a range (1-5), or "all": ')
    try:
        indices = _parse_selection(raw, len(funds))
    except ValueError:
        print("Could not parse that selection. Run the tool again.")
        return 1

    if not indices:
        print("No funds selected.")
        return 1

    selected = [(funds[i]["name"], funds[i]["slug"]) for i in indices]
    download_root = get_download_root()
    print(f"\nSaving to: {download_root}")
    result = run_download(selected, download_root, log=print)

    print(
        f"\nFinished. {result.downloaded} new, {result.skipped} already had, "
        f"{len(result.failed)} problem(s)."
    )
    if result.failed:
        print("\nWhat did not work:")
        for fund_name, reason in result.failed:
            print(f"  {fund_name}: {reason}")

    if result.looks_like_site_changed:
        print(
            "\nHeads up: none of these funds listed any documents. The website may "
            "have changed how it publishes them."
        )

    print(f"\nSaved in: {download_root}")
    return 1 if result.failed else 0


if __name__ == "__main__":
    exit_code = main()

    if getattr(sys, "frozen", False):
        print()
        input("Press Enter to close...")
    else:
        sys.exit(exit_code)
