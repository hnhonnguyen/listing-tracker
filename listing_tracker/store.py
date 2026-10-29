from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id TEXT NOT NULL,
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    currency TEXT,
    price REAL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    price_seen_at TEXT,
    PRIMARY KEY (id, source)
);
CREATE TABLE IF NOT EXISTS price_changes (
    id TEXT NOT NULL,
    source TEXT NOT NULL,
    seen_at TEXT NOT NULL,
    old_price REAL,
    new_price REAL,
    currency TEXT,
    PRIMARY KEY (id, source, seen_at)
);
"""

FIELDS = [
    "id",
    "source",
    "url",
    "title",
    "currency",
    "price",
    "first_seen",
    "last_seen",
    "price_seen_at",
]

ITEM_COLUMNS = ", ".join(FIELDS)

NEW_ITEMS_SQL = (
    "SELECT source, title, price, currency, url, first_seen FROM items "
    "WHERE first_seen >= ? ORDER BY source, price"
)

CHANGES_SQL = (
    "SELECT c.source, l.title, c.old_price, c.new_price, l.currency, l.url "
    "FROM price_changes c JOIN items l ON l.id = c.id AND l.source = c.source "
    "WHERE c.seen_at >= ? ORDER BY (c.new_price - c.old_price)"
)


class Store:
    def __init__(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(path)
        self.con.executescript(SCHEMA)

    def close(self) -> None:
        self.con.close()

    def commit(self) -> None:
        self.con.commit()

    def record(self, source: str, currency: str, item: dict, now: str) -> str | None:
        """Store one item. Returns "new", "price", or None when unchanged."""
        row = self.con.execute(
            "SELECT price FROM items WHERE id = ? AND source = ?", (item["id"], source)
        ).fetchone()
        if row is None:
            self.con.execute(
                f"INSERT INTO items ({ITEM_COLUMNS}) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    item["id"],
                    source,
                    item["url"],
                    item["title"],
                    currency,
                    item["price"],
                    now,
                    now,
                    now if item["price"] is not None else None,
                ),
            )
            return "new"
        old_price = row[0]
        price = item["price"]
        self.con.execute(
            "UPDATE items SET url = ?, title = COALESCE(?, title), "
            "price = COALESCE(?, price), last_seen = ?, "
            "price_seen_at = CASE WHEN ? IS NOT NULL THEN ? ELSE price_seen_at END "
            "WHERE id = ? AND source = ?",
            (
                item["url"],
                item["title"],
                price,
                now,
                price,
                now,
                item["id"],
                source,
            ),
        )
        if price is not None and old_price is not None and price != old_price:
            self.con.execute(
                "INSERT OR IGNORE INTO price_changes "
                "(id, source, seen_at, old_price, new_price, currency) VALUES (?,?,?,?,?,?)",
                (item["id"], source, now, old_price, price, currency),
            )
            return "price"
        return None

    def stats(self) -> dict:
        total, with_price, sources = self.con.execute(
            "SELECT COUNT(*), SUM(price IS NOT NULL), COUNT(DISTINCT source) FROM items"
        ).fetchone()
        changes = self.con.execute("SELECT COUNT(*) FROM price_changes").fetchone()[0]
        return {
            "total": total,
            "with_price": with_price or 0,
            "sources": sources or 0,
            "changes": changes,
        }

    def source_breakdown(self) -> list[tuple]:
        return self.con.execute(
            "SELECT source, COUNT(*), SUM(price IS NOT NULL) FROM items "
            "GROUP BY source ORDER BY source"
        ).fetchall()

    def new_items(self, since: str) -> list[tuple]:
        return self.con.execute(NEW_ITEMS_SQL, (since,)).fetchall()

    def price_changes_since(self, since: str) -> list[tuple]:
        return self.con.execute(CHANGES_SQL, (since,)).fetchall()

    def export(self, out_path: str | Path) -> int:
        rows = self.con.execute(
            f"SELECT {ITEM_COLUMNS} FROM items ORDER BY source, id"
        ).fetchall()
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", newline="", encoding="utf-8") as fh:
            if out_path.suffix == ".jsonl":
                for row in rows:
                    fh.write(json.dumps(dict(zip(FIELDS, row)), ensure_ascii=False) + "\n")
            else:
                writer = csv.writer(fh)
                writer.writerow(FIELDS)
                writer.writerows(rows)
        return len(rows)
