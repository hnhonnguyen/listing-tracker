from listing_tracker.store import Store


def test_record_lifecycle(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    try:
        item = {"id": "1", "url": "https://example.com/1", "title": "Thing", "price": 10.0}
        now = "2026-10-29T00:00:00+00:00"

        assert store.record("demo", "USD", item, now) == "new"
        assert store.record("demo", "USD", item, now) is None

        cheap = dict(item, price=8.0)
        assert store.record("demo", "USD", cheap, now) == "price"

        stats = store.stats()
        assert stats == {"total": 1, "with_price": 1, "sources": 1, "changes": 1}

        changes = store.price_changes_since("2026-10-28")
        assert changes[0][2:4] == (10.0, 8.0)
    finally:
        store.close()


def test_missing_price_keeps_last_known_price(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    try:
        item = {"id": "1", "url": "https://example.com/1", "title": "Thing", "price": 10.0}
        store.record("demo", "USD", item, "2026-10-29T00:00:00+00:00")

        without_price = dict(item, price=None)
        assert store.record("demo", "USD", without_price, "2026-10-30T00:00:00+00:00") is None

        price = store.con.execute("SELECT price FROM items WHERE id = '1'").fetchone()[0]
        assert price == 10.0
    finally:
        store.close()
