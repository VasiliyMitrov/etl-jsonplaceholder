import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import API_BASE_URL, REQUEST_TIMEOUT

log = logging.getLogger(__name__)


def _make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch(endpoint: str) -> list[dict]:
    url = API_BASE_URL + endpoint
    log.info("Fetching %s", url)
    with _make_session() as session:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    data = response.json()
    log.info("Fetched %d records from %s", len(data), endpoint)
    return data
