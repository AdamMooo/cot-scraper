"""
Shared HTTP session with retries. This tool runs unattended with no one around
to patch it if the site has a transient blip, so every network call in
the app goes through get_session() rather than a bare requests.get.

Public interface:
    get_session() -> requests.Session
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_session: requests.Session | None = None


def get_session() -> requests.Session:
    global _session
    if _session is not None:
        return _session

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    retry = Retry(
        total=4,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    _session = session
    return session
