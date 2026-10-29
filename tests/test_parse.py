import pytest

from listing_tracker.config import Pagination, Selectors, SiteConfig
from listing_tracker.parse import derive_id, parse_items, parse_price


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("£51.77", 51.77),
        ("$1,234.50", 1234.5),
        ("1.234,50 €", 1234.5),
        ("1,234", 1234.0),
        ("20,5", 20.5),
        ("1.234.567", 1234567.0),
        ("not a price", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_price(raw, expected):
    assert parse_price(raw) == expected


def test_derive_id_uses_regex_capture():
    url = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    assert derive_id(url, r"_([0-9]+)/index\.html$") == "1000"


def test_derive_id_falls_back_to_path():
    assert derive_id("https://example.com/deals/widget-42/", None) == "/deals/widget-42"


HTML = """
<html><body>
<article class="product">
  <h3><a href="widget-1.html" title="Widget One">Widget One</a></h3>
  <p class="price">£10.00</p>
</article>
<article class="product">
  <h3><a href="widget-2.html" title="Widget Two">Widget Two</a></h3>
  <p class="price">£12.50</p>
</article>
</body></html>
"""

CONFIG = SiteConfig(
    name="demo",
    base_url="https://example.com/list/",
    pagination=Pagination(url_template="https://example.com/list/page-{page}.html"),
    selectors=Selectors(
        item="article.product",
        title="h3 a",
        title_attr="title",
        price="p.price",
        url="h3 a",
    ),
)


def test_parse_items_extracts_fields():
    items, skipped = parse_items(HTML, CONFIG, "https://example.com/list/page-1.html")
    assert skipped == 0
    assert [item["id"] for item in items] == ["/list/widget-1.html", "/list/widget-2.html"]
    assert items[0]["title"] == "Widget One"
    assert items[0]["url"] == "https://example.com/list/widget-1.html"
    assert items[1]["price"] == 12.5


def test_parse_items_skips_malformed_nodes():
    broken_html = """
    <html><body>
    <article class="product"><p class="price">£1.00</p></article>
    <article class="product">
      <h3><a href="ok.html" title="Fine">Fine</a></h3>
      <p class="price">£2.00</p>
    </article>
    </body></html>
    """
    items, skipped = parse_items(broken_html, CONFIG, "https://example.com/list/page-1.html")
    assert len(items) == 1
    assert skipped == 1
