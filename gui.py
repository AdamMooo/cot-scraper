"""
Fund document scraper, window version.

Type part of a name to filter, tick what you want, hit Download.
Built to hand to someone as a double-click .exe: no console window, nothing to
type but a search, and background threads so the window never freezes while
loading the fund list or downloading.

Run:
    python gui.py
"""

import ctypes
import os
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from downloader import run_download, safe_name
import site_config
from frog import build_frame
from fund_index import FundEntry, get_fund_index, refresh_and_find_new
from settings import get_download_root, set_download_root
from shortcut import can_create_shortcut, create_start_menu_shortcut

# One name everywhere: the window, the .exe filename and the Start Menu
# shortcut all read from site_config.
WINDOW_TITLE = site_config.APP_NAME
APP_VERSION = "1.0"

HELP_TEXT = f"""Basics

Search by name, tick what you want, click Download selected. Esc clears the
search. Select all takes everything currently listed, so you can grab the
whole list in one go if you want.

Everything on {site_config.SITE_NAME} is in the list. For each one you tick
you get every document posted on its page that day, whatever those happen to
be, not a fixed set.

Each one gets its own folder, and the files are named readably, so you end up
with something like "Some Item Name\\Prospectus.pdf".

Run it again whenever. Files you already have are skipped, so you only ever
download what is new. Anything you have already saved is marked "saved".


Where files go

By default, a "Documents" folder next to this app. The bar near the top
always shows where you are saving, and "Open folder" takes you straight there.


Saving into SharePoint

Sync the SharePoint library to this PC first, using the Sync button in
SharePoint or Teams. It then behaves like any normal folder, usually under
"OneDrive - <your company>".

Click Change folder, pick it, done. The app remembers, and OneDrive pushes
everything up to SharePoint for you.


New items

The list is read from the website every time you open the app, so anything
new appears on its own. When it does, you get a green bar at the top naming
it. "Check for new items" does the same thing on demand.


Keeping it handy

Easiest way, and it always works: while this app is open, find its icon in the
taskbar at the bottom of your screen, right click that icon, and choose
"Pin to taskbar". It stays there after you close the app.

On Windows 11 you may need to click "Show more options" first.

If you would rather have it in your Start Menu, use the File menu, then
"Add to Start Menu". That puts a shortcut into your own Start Menu folder, and offers to open that folder for you so you
can right click the shortcut and pin it from there.


If a download fails

The Progress box says which item and why. It is almost always a brief network
blip, so trying again later usually sorts it.
"""

# Bundled read-only resource (the icon): PyInstaller onefile extracts --add-data
# files to sys._MEIPASS, a temp dir that's fine to read from mid-run but never
# to write persistent state into (see downloader.py / settings.py for that split).
_RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
_ICON_PATH = _RESOURCE_DIR / "app_icon.ico"

_BRAND = "#215744"
_BRAND_LIGHT = "#cfe6da"
_NEW_BADGE = "#0a6b3d"


def _shorten_path(path: Path, max_len: int = 55) -> str:
    text = str(path)
    if len(text) <= max_len:
        return text
    return text[:3] + "..." + text[-(max_len - 6):]


class ScraperApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry("620x720")
        self.root.minsize(460, 460)

        # Windows groups taskbar buttons by AppUserModelID and falls back to a
        # generic host identity when a process does not declare one, which is
        # why a Tk window can end up with no icon of its own on the taskbar.
        # Declaring one makes Windows treat this as its own application and use
        # the window icon set below.
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                site_config.APP_NAME.replace(" ", "") + ".App"
            )
        except (AttributeError, OSError):
            pass  # not Windows, or the call is unavailable

        if _ICON_PATH.exists():
            try:
                # default=True so dialogs opened later inherit the same icon.
                self.root.iconbitmap(default=str(_ICON_PATH))
            except tk.TclError:
                pass  # icon is cosmetic, never worth failing startup over

        style = ttk.Style()
        for theme in ("vista", "clam"):
            if theme in style.theme_names():
                style.theme_use(theme)
                break
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

        self._log_queue: queue.Queue = queue.Queue()
        self._worker: threading.Thread | None = None
        self._funds: list[FundEntry] = []
        self._check_vars: dict[str, tk.BooleanVar] = {}
        self._checkbuttons: dict[str, ttk.Checkbutton] = {}
        self._download_root = get_download_root()
        self._downloading = False
        self._loading_funds = False
        self._new_slugs: set[str] = set()
        self._filter_to_new = False

        self._build_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._drain_log_queue)
        self._load_fund_list(force_refresh=False)

    # ── UI construction ──────────────────────────────────────────────

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        # Menu wording matches the buttons exactly, so the same action never
        # goes by two different names.
        file_menu.add_command(label="Change folder...", command=self._choose_folder)
        file_menu.add_command(label="Open folder", command=self._open_downloads_folder)
        if can_create_shortcut():
            file_menu.add_separator()
            file_menu.add_command(label="Add to Start Menu", command=self._add_to_start_menu)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="How to use", command=self._show_help)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def _show_help(self) -> None:
        win = tk.Toplevel(self.root)
        win.title("How to Use")
        win.geometry("640x560")
        win.transient(self.root)
        if _ICON_PATH.exists():
            try:
                win.iconbitmap(str(_ICON_PATH))
            except tk.TclError:
                pass

        box = scrolledtext.ScrolledText(win, wrap="word", font=("Segoe UI", 10), padx=12, pady=10)
        box.pack(fill="both", expand=True)
        box.insert("1.0", HELP_TEXT)
        box.config(state="disabled")

        ttk.Button(win, text="Close", command=win.destroy).pack(pady=8)

    def _add_to_start_menu(self) -> None:
        try:
            link_path = create_start_menu_shortcut()
        except Exception as exc:
            messagebox.showerror(WINDOW_TITLE, f"Could not add the shortcut.\n\n{exc}")
            return

        # Start Menu search can take a while to index a new shortcut, so point
        # at the actual folder rather than telling them to search for it.
        if messagebox.askyesno(
            WINDOW_TITLE,
            f'Added a shortcut called "{site_config.APP_NAME}" here:\n\n'
            f"{link_path.parent}\n\n"
            "To pin it, right click that shortcut and choose Pin to taskbar or "
            "Pin to Start. On Windows 11 click \"Show more options\" first.\n\n"
            "Open that folder now?",
        ):
            os.startfile(link_path.parent)

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About",
            f"{WINDOW_TITLE}\nVersion {APP_VERSION}\n\n"
            f"Downloads documents from {site_config.SITE_NAME}, one folder per "
            f"{site_config.ITEM_WORD}.\n\n"
            "The list comes from the website itself, so anything added later "
            "shows up on its own.",
        )

    def _build_widgets(self) -> None:
        self._build_menu()

        # Header band, coloured to give the window an identity rather than
        # looking like a bare dialog.
        header = tk.Frame(self.root, bg=_BRAND, padx=14, pady=10)
        header.pack(fill="x")
        self._header = header

        # The frog lives in the header and hops while a download runs.
        self._frog_frames = {
            name: build_frame(2, name, background=_BRAND) for name in ("idle", "hop", "happy")
        }
        self._frog_label = tk.Label(header, image=self._frog_frames["idle"], bg=_BRAND, bd=0)
        self._frog_label.pack(side="left", anchor="w", padx=(0, 10))
        self._frog_job: str | None = None
        self._frog_flip = False

        tk.Label(
            header, text=site_config.APP_NAME, bg=_BRAND, fg="white", font=("Segoe UI", 15, "bold")
        ).pack(side="left", anchor="w")
        tk.Label(
            header, text=f"Everything posted on {site_config.SITE_NAME}, "
                                 f"filed by {site_config.ITEM_WORD}",
            bg=_BRAND, fg="#cfe6da", font=("Segoe UI", 9),
        ).pack(side="left", anchor="s", padx=(10, 0), pady=(0, 3))
        tk.Button(
            header, text="How to use", command=self._show_help,
            bg=_BRAND_LIGHT, fg=_BRAND, relief="flat", font=("Segoe UI", 9, "bold"),
            padx=10, cursor="hand2", activebackground="white",
        ).pack(side="right")

        # Sits hidden until a launch finds items that weren't there last time.
        self._banner = tk.Frame(self.root, bg="#e7f5ec")
        self._banner_label = tk.Label(
            self._banner, text="", bg="#e7f5ec", fg=_BRAND, font=("Segoe UI", 9, "bold"),
            anchor="w", padx=14, pady=7,
        )
        self._banner_label.pack(side="left", fill="x", expand=True)
        tk.Button(
            self._banner, text="Show only these", command=self._show_only_new,
            bg="#e7f5ec", fg=_BRAND, relief="flat", font=("Segoe UI", 9, "underline"),
            cursor="hand2", activebackground="#e7f5ec",
        ).pack(side="right", padx=(0, 6))
        tk.Button(
            self._banner, text="Dismiss", command=self._banner.pack_forget,
            bg="#e7f5ec", fg="#666", relief="flat", font=("Segoe UI", 9),
            cursor="hand2", activebackground="#e7f5ec",
        ).pack(side="right", padx=(0, 10))

        body = ttk.Frame(self.root, padding=(14, 10, 14, 0))
        body.pack(fill="both", expand=True)
        self._body = body

        # Where files go
        folder_row = ttk.Frame(body)
        folder_row.pack(fill="x")
        ttk.Label(folder_row, text="Saving to", font=("Segoe UI", 9, "bold")).pack(side="left")
        self.folder_label = ttk.Label(folder_row, text=_shorten_path(self._download_root))
        self.folder_label.pack(side="left", padx=6)
        ttk.Button(folder_row, text="Change folder", command=self._choose_folder).pack(side="right")

        ttk.Separator(body).pack(fill="x", pady=10)

        # Search
        search_row = ttk.Frame(body)
        search_row.pack(fill="x")
        ttk.Label(search_row, text=f"Find a {site_config.ITEM_WORD}", font=("Segoe UI", 9, "bold")).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._apply_filter())
        search_entry = ttk.Entry(search_row, textvariable=self.search_var, font=("Segoe UI", 10))
        search_entry.pack(side="left", fill="x", expand=True, padx=8)
        search_entry.focus_set()
        # Typing a search means they're done looking at just the new items.
        search_entry.bind("<Key>", lambda e: setattr(self, "_filter_to_new", False))
        self.root.bind("<Escape>", lambda e: self.search_var.set(""))
        self.root.bind("<Return>", lambda e: self._start_download())
        ttk.Label(search_row, text="name", foreground="#777").pack(side="left")

        button_bar = ttk.Frame(body)
        button_bar.pack(fill="x", pady=(8, 6))
        ttk.Button(button_bar, text="Select all", command=self._select_all).pack(side="left")
        ttk.Button(button_bar, text="Clear", command=self._clear_all).pack(side="left", padx=4)
        self.refresh_button = ttk.Button(button_bar, text=f"Check for new {site_config.ITEM_WORD_PL}", command=self._refresh_fund_list)
        self.refresh_button.pack(side="right")
        self.selected_label = ttk.Label(button_bar, text="Nothing selected yet", foreground="#555")
        self.selected_label.pack(side="left", padx=10)

        # Scrollable fund list
        list_frame = ttk.Frame(body)
        list_frame.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(
            list_frame, borderwidth=1, relief="solid", highlightthickness=0, bg="white"
        )
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self._canvas.yview)
        self._checks_frame = tk.Frame(self._canvas, bg="white")

        self._checks_frame.bind(
            "<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        )
        self._canvas_window = self._canvas.create_window((0, 0), window=self._checks_frame, anchor="nw")
        self._canvas.bind(
            "<Configure>", lambda e: self._canvas.itemconfig(self._canvas_window, width=e.width)
        )
        self._canvas.configure(yscrollcommand=scrollbar.set)

        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._canvas.bind_all("<MouseWheel>", lambda e: self._canvas.yview_scroll(int(-e.delta / 120), "units"))

        self._loading_label = tk.Label(
            self._checks_frame,
            text=f"Getting the list from {site_config.SITE_NAME}, one moment...",
            bg="white", fg="#555", anchor="w",
        )
        self._loading_label.pack(fill="x", padx=8, pady=8)

        # Shown in place of the list when a search matches nothing, so a blank
        # list never reads as "the app is broken".
        self._no_match_label = tk.Label(self._checks_frame, text="", bg="white", fg="#555", anchor="w")

        self.progress = ttk.Progressbar(body, mode="determinate")
        self.progress.pack(fill="x", pady=(10, 0))

        # Primary action. A plain tk.Button is used so the accent colour
        # actually applies; ttk themes ignore background on Windows.
        action_bar = ttk.Frame(body)
        action_bar.pack(fill="x", pady=10)

        self.download_button = tk.Button(
            action_bar, text="Download selected", command=self._start_download,
            bg=_BRAND, fg="white", activebackground=_BRAND, activeforeground="white",
            relief="flat", font=("Segoe UI", 10, "bold"), padx=18, pady=7,
            cursor="hand2", state="disabled", disabledforeground="#e8e8e8",
        )
        self.download_button.pack(side="left")

        ttk.Button(action_bar, text="Open folder", command=self._open_downloads_folder).pack(
            side="left", padx=8
        )

        self.status_label = ttk.Label(action_bar, text="Starting up...", anchor="e", foreground="#555")
        self.status_label.pack(side="right", fill="x", expand=True)

        # Progress detail
        log_frame = ttk.Frame(self.root, padding=(14, 0, 14, 12))
        log_frame.pack(fill="both", expand=False)
        ttk.Label(log_frame, text="Progress", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 3))
        self.log_box = scrolledtext.ScrolledText(
            log_frame, height=9, state="disabled", font=("Consolas", 9),
            bg="#fbfbfb", relief="solid", borderwidth=1,
        )
        self.log_box.pack(fill="both", expand=True)

    # ── The frog ───────────────────────────────────────────────────────


    def _set_frog(self, frame: str) -> None:
        self._frog_label.config(image=self._frog_frames[frame])

    def _start_frog_hopping(self) -> None:
        self._stop_frog_hopping()
        self._hop_once()

    def _hop_once(self) -> None:
        self._frog_flip = not self._frog_flip
        self._set_frog("hop" if self._frog_flip else "idle")
        self._frog_job = self.root.after(320, self._hop_once)

    def _stop_frog_hopping(self, final: str = "idle") -> None:
        if self._frog_job is not None:
            self.root.after_cancel(self._frog_job)
            self._frog_job = None
        self._set_frog(final)

    # ── Download folder ────────────────────────────────────────────────

    def _choose_folder(self) -> None:
        chosen = filedialog.askdirectory(
            title="Choose where downloaded documents should be saved",
            initialdir=str(self._download_root),
        )
        if not chosen:
            return
        self._download_root = Path(chosen)
        set_download_root(self._download_root)
        self.folder_label.config(text=_shorten_path(self._download_root))

    # ── Fund list loading ──────────────────────────────────────────────

    def _load_fund_list(self, force_refresh: bool) -> None:
        if self._loading_funds:
            return
        self._loading_funds = True
        self.refresh_button.config(state="disabled")
        self.status_label.config(text="Getting the list...")
        threading.Thread(target=self._load_fund_list_worker, args=(force_refresh,), daemon=True).start()

    def _load_fund_list_worker(self, force_refresh: bool) -> None:
        try:
            if force_refresh:
                funds, new = refresh_and_find_new(log=self._log_queue.put)
            else:
                funds = get_fund_index(log=self._log_queue.put)
                new = []
            self._log_queue.put(("__FUNDS_LOADED__", funds, new))
        except Exception as exc:
            self._log_queue.put(f"Could not get the list: {exc}")
            self._log_queue.put(("__FUNDS_LOADED__", [], []))

    def _auto_check_for_new_funds(self) -> None:
        """Quietly re-read the site after the cached list is already on screen.

        A new fund would otherwise stay invisible until someone thought to press
        a refresh button, which is not something to rely on.
        """
        if self._loading_funds or self._downloading:
            return
        threading.Thread(target=self._auto_check_worker, daemon=True).start()

    def _auto_check_worker(self) -> None:
        try:
            funds, new = refresh_and_find_new(log=lambda _msg: None)
            if new:
                self._log_queue.put(("__FUNDS_LOADED__", funds, new))
        except Exception:
            pass  # the cached list is already usable; a failed check changes nothing

    def _refresh_fund_list(self) -> None:
        if self._loading_funds:
            return
        self._clear_fund_widgets()
        self.download_button.config(state="disabled")
        self._loading_label.config(
            text=f"Checking {site_config.SITE_NAME} for new {site_config.ITEM_WORD_PL}..."
        )
        self._loading_label.pack(fill="x", padx=8, pady=8)
        self._load_fund_list(force_refresh=True)

    def _clear_fund_widgets(self) -> None:
        for cb in self._checkbuttons.values():
            cb.destroy()
        self._checkbuttons.clear()
        self._check_vars.clear()
        self._funds = []
        self._no_match_label.pack_forget()

    def _populate_fund_list(self, funds: list[FundEntry], new: list[FundEntry] | None = None) -> None:
        previously_selected = {slug for slug, var in self._check_vars.items() if var.get()}
        if self._checkbuttons:
            self._clear_fund_widgets()

        self._funds = funds
        self._loading_funds = False
        self._loading_label.pack_forget()
        self.refresh_button.config(state="normal")

        if new:
            self._new_slugs = {e["slug"] for e in new}

        for entry in funds:
            var = tk.BooleanVar(value=entry["slug"] in previously_selected)
            var.trace_add("write", lambda *_: self._update_selected_count())
            self._check_vars[entry["slug"]] = var
            self._checkbuttons[entry["slug"]] = self._make_fund_row(entry, var)

        self._apply_filter()
        self._update_selected_count()

        if not funds:
            self._loading_label.config(
                text=f"Could not reach {site_config.SITE_NAME}. "
                     "Check your internet, then try again."
            )
            self._loading_label.pack(fill="x", padx=8, pady=8)
            self.status_label.config(text="Nothing loaded.")
            return

        # Never re-enable the button underneath a running download.
        if not self._downloading:
            self.download_button.config(state="normal")
        self.status_label.config(text=f"Ready. {len(funds)} {site_config.ITEM_WORD_PL}.")

        if new:
            plural = site_config.ITEM_WORD if len(new) == 1 else site_config.ITEM_WORD_PL
            names = ", ".join(e["name"] for e in new[:3])
            if len(new) > 3:
                names += f", and {len(new) - 3} more"
            self._banner_label.config(text=f"{len(new)} new {plural} since last time: {names}")
            self._banner.pack(fill="x", after=self._header, before=self._body)
        else:
            # First run has nothing to compare against, so check again once the
            # list is on screen and the saved copy exists.
            self.root.after(1200, self._auto_check_for_new_funds)

    def _make_fund_row(self, entry: FundEntry, var: tk.BooleanVar) -> tk.Frame:
        """One row: checkbox, name and any codes, plus New / Saved markers."""
        row = tk.Frame(self._checks_frame, bg="white")

        label = entry["name"]
        if entry["tickers"]:
            label += f"   {', '.join(entry['tickers'])}"
        tk.Checkbutton(
            row, text=label, variable=var, bg="white", activebackground="white",
            anchor="w", font=("Segoe UI", 9), cursor="hand2",
        ).pack(side="left")

        if entry["slug"] in self._new_slugs:
            tk.Label(
                row, text="NEW", bg=_NEW_BADGE, fg="white", font=("Segoe UI", 7, "bold"), padx=4,
            ).pack(side="left", padx=4)

        if self._already_downloaded(entry["name"]):
            tk.Label(
                row, text="saved", bg="white", fg="#8a8a8a", font=("Segoe UI", 8),
            ).pack(side="left", padx=4)

        return row

    def _already_downloaded(self, fund_name: str) -> bool:
        """True when this item already has a folder, so the user sees what they have."""
        try:
            return (self._download_root / safe_name(fund_name, "item")).is_dir()
        except OSError:
            return False

    def _show_only_new(self) -> None:
        self._clear_all()
        for slug in self._new_slugs:
            if slug in self._check_vars:
                self._check_vars[slug].set(True)
        self.search_var.set("")
        self._filter_to_new = True
        self._apply_filter()

    def _matches(self, entry: FundEntry, query: str) -> bool:
        if self._filter_to_new and entry["slug"] not in self._new_slugs:
            return False
        if not query:
            return True
        return query in (entry["name"].lower() + " " + " ".join(entry["tickers"]).lower())

    def _apply_filter(self) -> None:
        query = self.search_var.get().strip().lower()
        shown = 0
        for entry in self._funds:
            row = self._checkbuttons[entry["slug"]]
            if self._matches(entry, query):
                row.pack(fill="x", anchor="w")
                shown += 1
            else:
                row.pack_forget()

        if self._funds and shown == 0:
            self._no_match_label.config(text=f'Nothing matches "{self.search_var.get().strip()}".')
            self._no_match_label.pack(fill="x", padx=8, pady=8)
        else:
            self._no_match_label.pack_forget()

    # ── Actions ──────────────────────────────────────────────────────

    def _update_selected_count(self) -> None:
        count = sum(1 for var in self._check_vars.values() if var.get())
        if count == 0:
            self.selected_label.config(text="Nothing selected yet")
        elif count == 1:
            self.selected_label.config(text=f"1 {site_config.ITEM_WORD} selected")
        else:
            self.selected_label.config(
                text=f"{count} {site_config.ITEM_WORD_PL} selected"
            )

    def _select_all(self) -> None:
        """Selects everything currently matching the search filter."""
        query = self.search_var.get().strip().lower()
        for entry in self._funds:
            if self._matches(entry, query):
                self._check_vars[entry["slug"]].set(True)

    def _clear_all(self) -> None:
        for var in self._check_vars.values():
            var.set(False)

    def _open_downloads_folder(self) -> None:
        self._download_root.mkdir(parents=True, exist_ok=True)
        os.startfile(self._download_root)

    def _on_close(self) -> None:
        if self._downloading:
            if not messagebox.askyesno(
                WINDOW_TITLE, "A download is still running. Stop it and close?"
            ):
                return
        self.root.destroy()

    def _start_download(self) -> None:
        if self._downloading or not self._funds:
            return

        selected = [
            (entry["name"], entry["slug"]) for entry in self._funds if self._check_vars[entry["slug"]].get()
        ]
        if not selected:
            messagebox.showinfo(
                WINDOW_TITLE, f"Tick at least one {site_config.ITEM_WORD} first."
            )
            return

        self._set_log("")
        self._downloading = True
        self._start_frog_hopping()
        self.download_button.config(state="disabled", text="Downloading...")
        self.progress.config(value=0, maximum=len(selected))
        self.status_label.config(
            text=f"Downloading {len(selected)} "
                 f"{site_config.ITEM_WORD if len(selected) == 1 else site_config.ITEM_WORD_PL}..."
        )

        self._worker = threading.Thread(target=self._run_worker, args=(selected,), daemon=True)
        self._worker.start()

    def _run_worker(self, selected: list[tuple[str, str]]) -> None:
        """Runs on a background thread, so it only ever posts to the queue."""
        try:
            result = run_download(
                selected,
                self._download_root,
                log=self._log_queue.put,
                on_fund_done=lambda done, total: self._log_queue.put(("__PROGRESS__", done, total)),
            )

            self._log_queue.put(
                f"\nFinished. {result.downloaded} new file(s), "
                f"{result.skipped} already had, {len(result.failed)} problem(s)."
            )
            if result.failed:
                self._log_queue.put("\nWhat did not work:")
                for fund_name, reason in result.failed:
                    self._log_queue.put(f"  {fund_name}: {reason}")
            self._log_queue.put(f"\nSaved in: {self._download_root}")

            if result.looks_like_site_changed:
                self._log_queue.put(
                    f"\nHeads up: none of the {site_config.ITEM_WORD_PL} you picked "
                    "listed any documents. "
                    "That is unusual and may mean the website changed how it "
                    "publishes them. Try again later, and if it keeps happening "
                    "the documents will need to be downloaded from the site by hand."
                )
            self._log_queue.put(("__DONE__", result))
        except Exception as exc:
            self._log_queue.put(f"\nSomething went wrong and the download stopped: {exc}")
            self._log_queue.put(("__DONE__", None))

    def _on_download_finished(self, result) -> None:
        """Re-enable the UI and tell the user plainly how it went."""
        self._downloading = False
        self.download_button.config(state="normal", text="Download selected")

        if result is None:
            self._stop_frog_hopping("idle")
            self.status_label.config(text="Stopped early. See Progress below.")
            messagebox.showerror(
                WINDOW_TITLE,
                "The download stopped before it finished. The Progress box at the "
                "bottom has the details.\n\nAnything already downloaded has been kept.",
            )
            return

        self._stop_frog_hopping("happy" if not result.failed else "idle")

        # Rebuild rows first so the "saved" markers reflect what just landed,
        # then set the status, since rebuilding resets the status text.
        self._populate_fund_list(self._funds)
        self.status_label.config(
            text=f"Done. {result.downloaded} new, {result.skipped} already had, "
                 f"{len(result.failed)} problem(s)."
        )

        summary = (
            f"{result.downloaded} new file(s) downloaded.\n"
            f"{result.skipped} file(s) you already had were left alone.\n"
        )
        if result.failed:
            summary += f"{len(result.failed)} did not work. See Progress at the bottom.\n"
        summary += f"\nSaved in:\n{self._download_root}\n\nOpen that folder now?"

        if messagebox.askyesno(WINDOW_TITLE, summary):
            self._open_downloads_folder()

    # ── Log queue draining (runs on the main/UI thread) ───────────────

    def _set_log(self, text: str) -> None:
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", tk.END)
        self.log_box.insert(tk.END, text)
        self.log_box.config(state="disabled")

    def _append_log(self, line: str) -> None:
        self.log_box.config(state="normal")
        self.log_box.insert(tk.END, line + "\n")
        self.log_box.see(tk.END)
        self.log_box.config(state="disabled")

    def _drain_log_queue(self) -> None:
        try:
            while True:
                item = self._log_queue.get_nowait()
                if isinstance(item, tuple) and item[0] == "__DONE__":
                    self._on_download_finished(item[1])
                elif isinstance(item, tuple) and item[0] == "__FUNDS_LOADED__":
                    self._populate_fund_list(item[1], item[2] if len(item) > 2 else None)
                elif isinstance(item, tuple) and item[0] == "__PROGRESS__":
                    _, done, total = item
                    self.progress.config(value=done, maximum=total)
                else:
                    self._append_log(item)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._drain_log_queue)


def main() -> None:
    root = tk.Tk()
    ScraperApp(root)

    # A windowed .exe has no console, so an unhandled exception would otherwise
    # make the app vanish with no explanation. Show it instead with no
    # maintainer to call, the user at least gets something to act on or forward.
    def report_callback_exception(exc_type, exc_value, exc_tb):
        messagebox.showerror(
            WINDOW_TITLE,
            f"Something went wrong:\n\n{exc_type.__name__}: {exc_value}\n\n"
            f'Your downloaded files are unaffected. Try "Check for new '
            f'{site_config.ITEM_WORD_PL}", '
            "or reopen the app.",
        )

    root.report_callback_exception = report_callback_exception
    root.mainloop()


if __name__ == "__main__":
    main()
