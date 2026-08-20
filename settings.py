"""
Persisted user settings. Currently just where downloads get saved.

Lets someone point the tool at a synced SharePoint or OneDrive folder, which
show up as ordinary local paths once synced, instead of wherever the .exe
happens to sit.

Public interface:
    DEFAULT_DOWNLOAD_ROOT
    get_download_root() -> Path
    set_download_root(path: Path) -> None
"""

import json
from pathlib import Path

from paths import APP_DIR, SETTINGS_FILE, support_dir

DEFAULT_DOWNLOAD_ROOT = APP_DIR / "Documents"


def _settings_path() -> Path:
    return support_dir() / SETTINGS_FILE


def _load() -> dict:
    path = _settings_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def get_download_root() -> Path:
    """Return the folder downloads should be saved under.

    Falls back to the default if nothing has been chosen, or if the saved
    folder has since been moved or deleted.
    """
    raw = _load().get("download_root")
    if raw:
        path = Path(raw)
        if path.is_dir():
            return path
    return DEFAULT_DOWNLOAD_ROOT


def set_download_root(path: Path) -> None:
    settings = _load()
    settings["download_root"] = str(path)
    _settings_path().write_text(json.dumps(settings, indent=2), encoding="utf-8")
