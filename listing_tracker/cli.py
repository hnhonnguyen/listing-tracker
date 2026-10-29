from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from .config import SiteConfig
from .crawl import crawl
from .store import Store

DEFAULT_DB = "data/listing-tracker.sqlite"


def fmt_price(price, currency: str) -> str:
    return f"{price:,.2f} {currency}" if price is not None else "n/a"


def cmd_crawl(args: argparse.Namespace) -> int:
    config = SiteConfig.load(args.config)
    store = Store(args.db)
    try:
        summary = crawl(config, store, args.pages)
    finally:
        store.close()
    print(
        f"done: +{summary['new']} new, ~{summary['price']} price changes, "
        f"{summary['seen']} items seen, {summary['errors']} page errors"
    )
    return 1 if summary["errors"] else 0


def cmd_watch(args: argparse.Namespace) -> int:
    store = Store(args.db)
    since = (datetime.now(timezone.utc) - timedelta(days=args.since_days)).isoformat(
        timespec="seconds"
    )
    totals = {"new": 0, "price": 0, "errors": 0}
    try:
        for config_path in args.configs:
            summary = crawl(SiteConfig.load(config_path), store)
            for key in totals:
                totals[key] += summary[key]
        new_items = store.new_items(since)
        changes = store.price_changes_since(since)
    finally:
        store.close()

    print(
        f"\n# watch report (last {args.since_days}d): "
        f"+{len(new_items)} new, {len(changes)} price changes"
    )
    if totals["errors"]:
        print(f"! {totals['errors']} page errors — this report may be incomplete")
    for source, title, price, currency, url, _first_seen in new_items[: args.top]:
        print(f"  + {fmt_price(price, currency):>14}  {source:<20} {str(title)[:56]}")
    for _source, title, old, new, currency, url in changes[: args.top]:
        pct = (new - old) / old * 100 if old else 0.0
        print(
            f"  ~ {fmt_price(old, currency)} -> {fmt_price(new, currency)} "
            f"({pct:+.1f}%)  {str(title)[:48]}\n    {url}"
        )
    return 1 if totals["errors"] else 0


def cmd_stats(args: argparse.Namespace) -> int:
    store = Store(args.db)
    try:
        stats = store.stats()
        breakdown = store.source_breakdown()
    finally:
        store.close()
    print(
        f"{stats['total']} items across {stats['sources']} source(s), "
        f"{stats['with_price']} with a price, {stats['changes']} price changes"
    )
    for source, total, with_price in breakdown:
        print(f"  {source:<24} {total:>6} items  {with_price or 0:>6} priced")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    store = Store(args.db)
    try:
        count = store.export(args.out)
    finally:
        store.close()
    print(f"exported {count} items -> {args.out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="listing-tracker", description="Config-driven web scraper and price tracker"
    )
    parser.add_argument("--db", default=DEFAULT_DB, help="SQLite database path (default: %(default)s)")
    sub = parser.add_subparsers(dest="command", required=True)

    crawl_parser = sub.add_parser("crawl", help="crawl one config once")
    crawl_parser.add_argument("config", help="path to a YAML site config")
    crawl_parser.add_argument("--pages", type=int, default=None, help="override max_pages")
    crawl_parser.set_defaults(func=cmd_crawl)

    watch_parser = sub.add_parser(
        "watch", help="crawl one or more configs and report new items and price changes"
    )
    watch_parser.add_argument("configs", nargs="+", help="one or more YAML site configs")
    watch_parser.add_argument("--since-days", type=int, default=1, help="report window (default: 1)")
    watch_parser.add_argument("--top", type=int, default=15, help="max rows per section")
    watch_parser.set_defaults(func=cmd_watch)

    stats_parser = sub.add_parser("stats", help="show a database summary")
    stats_parser.set_defaults(func=cmd_stats)

    export_parser = sub.add_parser("export", help="export items to CSV or JSONL")
    export_parser.add_argument("--out", default="data/items.csv", help="output file (.csv or .jsonl)")
    export_parser.set_defaults(func=cmd_export)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
