"""
Builds gui.py into a single-file, windowed Windows .exe so a non-technical
colleague can double-click it (no Python install required, no console window).

The output is named for the person receiving it rather than for the repo. It
also sidesteps a nuisance: Windows caches icons per executable path, so a
rebuilt .exe at the same path keeps showing its old icon on any machine that
already ran an earlier build.

Run:
    .venv/Scripts/python.exe build_exe.py

Produces:
    dist/<APP_NAME>.exe
"""

import site_config
import subprocess
import sys
from pathlib import Path

APP_NAME = site_config.APP_NAME


def main() -> int:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            "--windowed",
            "--name",
            APP_NAME,
            "--icon",
            "app_icon.ico",
            "--add-data",
            "app_icon.ico;.",
            # Pillow is only used by generate_icon.py at development time. If it
            # ever gets pulled in it adds six megabytes to a file meant to be
            # shared over chat, so the build fails loudly rather than quietly
            # shipping it.
            "--exclude-module",
            "PIL",
            "gui.py",
        ]
    )
    if result.returncode != 0:
        print(f"Build failed (exit code {result.returncode})")
        return result.returncode

    exe_path = Path("dist") / f"{APP_NAME}.exe"
    print(f"\nBuilt: {exe_path.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
