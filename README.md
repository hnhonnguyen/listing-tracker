# listing-tracker

Config-driven web scraper and price tracker. Point it at any paginated listing
page with CSS selectors and it keeps a local SQLite history, detects price
changes, and prints a change report on every run.

Built for low-volume personal monitoring of marketplaces, e-commerce catalogs,
and classifieds — no browser automation, just HTTP and CSS selectors.

## Features

- **One YAML file per site** — no per-target scraping code
- **SQLite history** — first/last seen timestamps for every item
- **Price change detection** — every change is logged with old and new values
- **Change reports** — `watch` prints new items and price movements over the last N days
- **Polite by default** — per-request delays, retries with backoff, custom User-Agent
- **End-of-pagination detection** — stops early when a page repeats
- **CSV / JSONL export**
- **Runnable demo** — `configs/books_toscrape.yaml` targets
  [books.toscrape.com](https://books.toscrape.com), a site built for scraping practice

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# Crawl 3 pages of the demo site
.venv/bin/listing-tracker crawl configs/books_toscrape.yaml

# Show what changed in the last 7 days
.venv/bin/listing-tracker watch configs/books_toscrape.yaml --since-days 7

# Database summary
.venv/bin/listing-tracker stats

# Export everything
.venv/bin/listing-tracker export --out data/books.csv
```

First crawl:

```
$ listing-tracker crawl configs/books_toscrape.yaml
  [books-toscrape] page 1: 20 items, +20 new, ~0 price changes
  [books-toscrape] page 2: 20 items, +20 new, ~0 price changes
  [books-toscrape] page 3: 20 items, +20 new, ~0 price changes
done: +60 new, ~0 price changes, 60 items seen, 0 page errors
```

Watch report:

```
$ listing-tracker watch configs/books_toscrape.yaml --since-days 7
  [books-toscrape] page 1: 20 items, +0 new, ~0 price changes
  ...

# watch report (last 7d): +60 new, 0 price changes
  +      12.84 GBP  books-toscrape       In Her Wake
  +      13.99 GBP  books-toscrape       Starving Hearts (Triangular Trade Trilogy, #1)
  +      14.27 GBP  books-toscrape       Untitled Collection: Sabbath Poems 2014
```

When a price moves, the change is recorded and reported:

```
  ~ 99.99 GBP -> 51.77 GBP (-48.2%)  A Light in the Attic
    https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html
```

## Configuring a site

One YAML file per site:

```yaml
name: example-shop
base_url: https://example.com
currency: USD
delay_seconds: 1.5

pagination:
  url_template: "https://example.com/deals?page={page}"
  start_page: 1
  max_pages: 5

selectors:
  item: "div.product-card"   # one node per listing
  title: "h2"                # title text, or an attribute via title_attr
  price: "span.price"
  url: "a.detail"            # link to the item page
  url_attr: "href"
```

| Key | Required | Description |
| --- | --- | --- |
| `name` | yes | Source name stored with every item |
| `base_url` | yes | Used to resolve relative item URLs |
| `pagination.url_template` | yes | Listing URL with a `{page}` placeholder |
| `pagination.start_page` / `max_pages` | no | Defaults: `1` / `3` |
| `selectors.item` | yes | One node per listing |
| `selectors.title` / `price` / `url` | yes | CSS selectors inside an item node |
| `title_attr` / `price_attr` / `url_attr` | no | Read an attribute instead of text; `url_attr` defaults to `href` |
| `currency` | no | Stored with each item (default: `USD`) |
| `id_regex` | no | First capture group becomes the item ID; falls back to the URL path |
| `delay_seconds` | no | Delay between requests (default: `1.5`) |
| `timeout_seconds` | no | HTTP timeout (default: `30`) |
| `user_agent` | no | Override the default User-Agent |

## Commands

| Command | What it does |
| --- | --- |
| `crawl CONFIG [--pages N]` | Crawl one config once and record every item |
| `watch CONFIG... [--since-days N] [--top N]` | Crawl one or more configs, then report new items and price changes |
| `stats` | Totals plus a per-source breakdown |
| `export --out FILE.csv\|.jsonl` | Dump all items |

All commands accept `--db PATH` (default: `data/listing-tracker.sqlite`).

## How price changes are detected

An item is identified by `id` — the first capture group of `id_regex`, or the
URL path when no regex is configured. On every crawl the new price is compared
with the stored price; if both exist and differ, a row is written to
`price_changes` with the timestamp, old value, and new value. If a page stops
showing a price, the last known price is kept and `price_seen_at` is not
advanced.

Prices are parsed from text like `£51.77`, `$1,234.50`, `1.234,50 €`, and
`20,5`. Ambiguous formats are rejected rather than guessed.

One malformed item never kills a page: it is skipped and counted in the page
summary. A failed first page aborts that config (usually a wrong URL or a
layout change); a failed middle page is skipped.

## Project layout

```
listing-tracker/
├── listing_tracker/   # config, fetch, parse, store, crawl, cli
├── configs/           # one YAML per site
└── tests/             # pytest suite
```

## Development

```bash
.venv/bin/pytest
```

15 tests cover price parsing, item extraction, ID derivation, and the
store lifecycle (new / unchanged / price change / missing price).

## Responsible use

- Check the target site's terms of service and `robots.txt` before scraping.
- Keep delays generous; the defaults are intentionally conservative.
- This tool is for personal, low-volume monitoring — not for building a data
  resale product.
- Sites protected by Cloudflare or heavy JavaScript rendering need a
  browser-based approach; this tool deliberately stays simple.

## License

MIT
