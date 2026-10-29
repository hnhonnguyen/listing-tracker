from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .config import SiteConfig

NUMBER_RE = re.compile(r"\d[\d.,\s]*\d|\d")


def parse_price(raw: str | None) -> float | None:
    """Parse a human-formatted number from a price string.

    Handles the common formats seen on listing pages: "£51.77" -> 51.77,
    "$1,234.50" -> 1234.5, "1.234,50 €" -> 1234.5, "20,5" -> 20.5 (decimal
    comma), "1,234" -> 1234 (thousands group). Returns None instead of
    guessing when the format is genuinely ambiguous.
    """
    if not raw:
        return None
    match = NUMBER_RE.search(str(raw))
    if not match:
        return None
    s = re.sub(r"\s", "", match.group(0))
    if not re.fullmatch(r"\d+(?:[.,]\d+)*", s):
        return None
    separators = re.findall(r"[.,]", s)
    groups = re.split(r"[.,]", s)
    if not separators:
        return float(s)
    if len(set(separators)) == 1:
        if len(separators) == 1:
            # "1,234" reads as a thousands group; "20,5" reads as a decimal comma.
            if separators[0] == "," and len(groups[-1]) == 3 and len(groups[0]) <= 3:
                return float("".join(groups))
            return float(".".join(groups))
        if all(len(g) == 3 for g in groups[1:]):
            return float("".join(groups))
        return None
    # Mixed separators: the last one is the decimal separator.
    if len(groups[-1]) <= 2:
        return float("".join(groups[:-1]) + "." + groups[-1])
    return None


def derive_id(url: str, id_regex: str | None) -> str:
    """Stable item ID: first capture group of id_regex, else the URL path."""
    if id_regex:
        match = re.search(id_regex, url)
        if match and match.groups():
            return match.group(1)
    path = urlsplit(url).path.rstrip("/")
    return path or url


def parse_items(html: str, config: SiteConfig, page_url: str) -> tuple[list[dict], int]:
    """Extract items from one listing page. Returns (items, skipped_count).

    One malformed item never kills the page: it is skipped and counted.
    """
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict] = []
    skipped = 0
    for node in soup.select(config.selectors.item):
        try:
            title_node = node.select_one(config.selectors.title)
            url_node = node.select_one(config.selectors.url)
            price_node = node.select_one(config.selectors.price)
            if not title_node or not url_node:
                skipped += 1
                continue
            href = url_node.get(config.selectors.url_attr)
            if not href:
                skipped += 1
                continue
            url = urljoin(page_url, href)
            title = (
                title_node.get(config.selectors.title_attr)
                if config.selectors.title_attr
                else None
            ) or title_node.get_text(" ", strip=True)
            price_text = None
            if price_node:
                price_text = (
                    price_node.get(config.selectors.price_attr)
                    if config.selectors.price_attr
                    else None
                ) or price_node.get_text(" ", strip=True)
            items.append(
                {
                    "id": derive_id(url, config.id_regex),
                    "url": url,
                    "title": title.strip(),
                    "price": parse_price(price_text),
                }
            )
        except Exception:
            skipped += 1
    return items, skipped
