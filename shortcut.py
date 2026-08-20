"""
Creates a Start Menu shortcut to the app, which is what makes it pinnable.

Windows will only pin something it can find in the Start Menu, so an .exe
sitting loose in a Downloads folder can't be pinned to the taskbar until a
shortcut exists. This builds one through PowerShell's WScript.Shell rather
than pywin32, to avoid adding a dependency to the shipped app.

Public interface:
    can_create_shortcut() -> bool
    create_start_menu_shortcut() -> Path
"""

import os
import site_config
import subprocess
import sys
from pathlib import Path

APP_LINK_NAME = f"{site_config.APP_NAME}.lnk"


def _start_menu_dir() -> Path:
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def can_create_shortcut() -> bool:
    """True only for the frozen .exe. Shortcutting a .py has no useful meaning."""
    return getattr(sys, "frozen", False) and os.name == "nt" and "APPDATA" in os.environ


def create_start_menu_shortcut() -> Path:
    """Create (or overwrite) the Start Menu shortcut and return its path."""
    target = Path(sys.executable).resolve()
    link_path = _start_menu_dir() / APP_LINK_NAME
    link_path.parent.mkdir(parents=True, exist_ok=True)

    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut("
        f"'{link_path}'); "
        f"$s.TargetPath = '{target}'; "
        f"$s.WorkingDirectory = '{target.parent}'; "
        f"$s.IconLocation = '{target}'; "
        f"$s.Description = 'Downloads documents from {site_config.SITE_NAME}'; "
        "$s.Save()"
    )

    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        check=True,
        capture_output=True,
        timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return link_path
