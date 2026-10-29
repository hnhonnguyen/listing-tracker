from __future__ import annotations

from datetime import datetime, timezone

from .config import SiteConfig
from .fetch import Fetcher, FetchError
from .parse import parse_items
from .store import Store


def crawl(config: SiteConfig, store: Store, pages: int | None = None) -> dict:
    """Walk the paginated listing for one config and record every item.

    A failed middle page is skipped; a failed first page aborts this config
    because it usually means the URL or layout is wrong.
    """
    pages = pages or config.pagination.max_pages
    fetcher = Fetcher(config.user_agent, timeout=config.timeout_seconds)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = {"new": 0, "price": 0, "seen": 0, "errors": 0}
    first_page = config.pagination.start_page
    previous_ids: set[str] = set()

    for page in range(first_page, first_page + pages):
        url = config.pagination.url_template.format(page=page)
        try:
            html = fetcher.get(url, delay=config.delay_seconds)
        except FetchError as exc:
            summary["errors"] += 1
            print(f"  [{config.name}] page {page}: {exc}")
            if page == first_page:
                break
            continue

        items, skipped = parse_items(html, config, url)
        if not items:
            summary["errors"] += 1
            print(f"  [{config.name}] page {page}: no items parsed — wrong URL or layout changed")
            break

        ids = {item["id"] for item in items}
        page_new = page_price = 0
        for item in items:
            summary["seen"] += 1
            result = store.record(config.name, config.currency, item, now)
            page_new += result == "new"
            page_price += result == "price"
        summary["new"] += page_new
        summary["price"] += page_price
        print(
            f"  [{config.name}] page {page}: {len(items)} items, "
            f"+{page_new} new, ~{page_price} price changes"
            + (f", {skipped} skipped" if skipped else "")
        )

        if page > first_page and ids == previous_ids:
            print(f"  [{config.name}] page {page} repeats the previous page — end of pagination")
            break
        previous_ids = ids

    store.commit()
    return summary
