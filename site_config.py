"""
Everything that ties this tool to one particular website.

Public interface:
    SITE_BASE     -- root URL, no trailing slash
    SITE_NAME     -- how the site is referred to in the interface
    APP_NAME      -- window title, .exe filename, shortcut name
    ITEM_WORD     -- singular noun for one item, used in the interface
    ITEM_WORD_PL  -- plural of the above
"""

SITE_BASE = "https://www.cftc.gov"
SITE_NAME = "cftc.gov"

APP_NAME = "COT Report Downloader"

ITEM_WORD = "report"
ITEM_WORD_PL = "reports"
