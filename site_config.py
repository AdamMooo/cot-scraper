"""
Everything that ties this tool to one particular website.

This is the file to edit when pointing the tool at a different site. Nothing
else contains a hostname or a product name, so a fork normally means changing
the values here and, depending on the site, the three functions named in
README.md under "Pointing it at a different site".

Public interface:
    SITE_BASE     -- root URL, no trailing slash
    SITE_NAME     -- how the site is referred to in the interface
    ITEM_PATH     -- the URL section the pages live under
    APP_NAME      -- window title, .exe filename, shortcut name
    ITEM_WORD     -- singular noun for one page, used in the interface
    ITEM_WORD_PL  -- plural of the above
"""

SITE_BASE = "https://www.example.com"
SITE_NAME = "example.com"

# Pages are expected at SITE_BASE + ITEM_PATH + "<slug>", for example
# "/funds/some-fund-name". Keep the leading and trailing slashes.
ITEM_PATH = "/funds/"

APP_NAME = "Document Downloader"

ITEM_WORD = "fund"
ITEM_WORD_PL = "funds"
