"""
Where the app keeps its own files.

Everything the app needs to remember goes in one hidden folder beside the
executable, so the person using it sees the app and their documents, not a
scattering of .json files with programmer names.

Public interface:
    APP_DIR          -- folder the .exe (or this script) lives in
    support_dir()    -> hidden folder for the app's own files
    FUND_LIST_FILE   -- saved fund list
    SETTINGS_FILE    -- chosen download folder
    SKIPPED_FILE     -- pages that turned out not to be funds
"""

import ctypes
import sys
from pathlib import Path

# PyInstaller onefile unpacks to a temp dir that is deleted on exit, so
# anything meant to survive a restart is anchored to the .exe's own folder.
APP_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)

_SUPPORT_DIR = APP_DIR / "App Files"
_FILE_ATTRIBUTE_HIDDEN = 0x02


def support_dir() -> Path:
    """Return the app's own folder, creating and hiding it on first use."""
    _SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        ctypes.windll.kernel32.SetFileAttributesW(str(_SUPPORT_DIR), _FILE_ATTRIBUTE_HIDDEN)
    except (AttributeError, OSError):
        pass  # not Windows, or the call is unavailable; hiding is cosmetic
    return _SUPPORT_DIR


FUND_LIST_FILE = "Fund list.json"
SETTINGS_FILE = "Settings.json"
SKIPPED_FILE = "Pages without documents.txt"
