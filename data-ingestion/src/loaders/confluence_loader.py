import os
import re
from html import unescape
from html.parser import HTMLParser

import requests

from src.utils.logger import get_logger

logger = get_logger(__name__)


class _HTMLTextExtractor(HTMLParser):
    """Convert HTML content into plain text."""

    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, data):
        if data and data.strip():
            self._parts.append(data.strip())

    def get_text(self) -> str:
        return " ".join(self._parts)


def _html_to_text(html_content: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(unescape(html_content or ""))
    raw_text = parser.get_text()
    return re.sub(r"\s+", " ", raw_text).strip()


def read_confluence_page(page_id: str) -> dict:
    """
    Fetch a Confluence page by page ID and return text/title/url.
    """
    base_url = os.getenv("CONFLUENCE_BASE_URL", "").rstrip("/")
    email = os.getenv("CONFLUENCE_EMAIL")
    api_token = os.getenv("CONFLUENCE_API_TOKEN")

    if not base_url:
        raise ValueError("CONFLUENCE_BASE_URL must be set")
    if not email or not api_token:
        raise ValueError("CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN must be set")

    endpoint = f"{base_url}/wiki/rest/api/content/{page_id}"
    params = {"expand": "body.storage,title,_links"}

    logger.info(f"Fetching Confluence page {page_id} from {base_url}")
    response = requests.get(
        endpoint,
        params=params,
        auth=(email, api_token),
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()
    storage_html = payload.get("body", {}).get("storage", {}).get("value", "")
    title = payload.get("title", "")
    relative_link = payload.get("_links", {}).get("webui", "")

    page_url = f"{base_url}{relative_link}" if relative_link else ""
    text = _html_to_text(storage_html)

    if not text:
        raise ValueError(f"Confluence page {page_id} returned empty content")

    return {
        "text": text,
        "title": title,
        "url": page_url,
    }
