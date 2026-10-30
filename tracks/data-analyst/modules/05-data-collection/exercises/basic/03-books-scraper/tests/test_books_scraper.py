"""Fixture `page-1.html`, `page-50.html`: trang danh mục đầu và cuối của https://books.toscrape.com, lưu nguyên
bytes ngày 30/10/2026. books.toscrape.com là website sandbox do Zyte (Scrapinghub) dựng **để luyện scraping**: sách,
giá, đánh giá đều là dữ liệu giả, được phép crawl. Test không gọi mạng."""
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
BASE = "https://books.toscrape.com/catalogue/"
PAGE1 = (ex.fixtures / "page-1.html").read_bytes()
PAGE50 = (ex.fixtures / "page-50.html").read_bytes()
COLUMNS = ["title", "price", "rating", "in_stock", "url"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("books_scraper.ipynb")


def test_parse_price(nb):
    assert nb.parse_price("£51.77") == 51.77
    # requests đoán ISO-8859-1 khi server không gửi charset: "£" thành "Â£"
    assert nb.parse_price("Â£51.77") == 51.77
    assert nb.parse_price(" £1,051.00 ") == 1051.0
    with pytest.raises(ValueError):
        nb.parse_price("Hết hàng")


def test_parse_listing_first_page(nb):
    books = nb.parse_listing(PAGE1, BASE + "page-1.html")
    assert len(books) == 20
    assert books[0] == {"title": "A Light in the Attic", "price": 51.77, "rating": 3, "in_stock": True,
                        "url": BASE + "a-light-in-the-attic_1000/index.html"}
    # tiêu đề đầy đủ nằm trong thuộc tính title, chữ hiển thị bị cắt "..."
    long_title = "Our Band Could Be Your Life: Scenes from the American Indie Underground, 1981-1991"
    assert long_title in [b["title"] for b in books]
    assert [b["rating"] for b in books].count(1) == 6
    assert sum(b["price"] for b in books) == pytest.approx(760.97)


def test_parse_listing_accepts_text(nb):
    books = nb.parse_listing(PAGE1.decode("utf-8"), BASE + "page-1.html")
    assert books[1]["title"] == "Tipping the Velvet" and books[1]["price"] == 53.74


def test_next_page(nb):
    assert nb.next_page(PAGE1, BASE + "page-1.html") == BASE + "page-2.html"
    assert nb.next_page(PAGE50, BASE + "page-50.html") is None


def test_robots_allows(nb):
    assert nb.robots_allows(None, "https://example.com/anything") is True
    rules = "User-agent: *\nDisallow: /private/\n\nUser-agent: badbot\nDisallow: /\n"
    assert nb.robots_allows(rules, "https://example.com/catalogue/page-1.html") is True
    assert nb.robots_allows(rules, "https://example.com/private/report.html") is False
    assert nb.robots_allows(rules, "https://example.com/catalogue/page-1.html", agent="badbot") is False


class FakeSite:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        return self.pages[url]


def test_crawl_follows_next_and_sleeps_between_requests(nb):
    # trang 2 giả lập bằng nội dung trang cuối (không có nút next)
    site = FakeSite({BASE + "page-1.html": PAGE1, BASE + "page-2.html": PAGE50})
    sleeps = []
    df = nb.crawl(site, BASE + "page-1.html", delay=1.5, sleep=sleeps.append)
    assert site.calls == [BASE + "page-1.html", BASE + "page-2.html"]
    assert sleeps == [1.5]
    assert list(df.columns) == COLUMNS
    assert len(df) == 40
    assert df["price"].sum() == pytest.approx(760.97 + 743.99)


def test_crawl_respects_max_pages(nb):
    site = FakeSite({BASE + "page-1.html": PAGE1, BASE + "page-2.html": PAGE50})
    sleeps = []
    df = nb.crawl(site, BASE + "page-1.html", max_pages=1, sleep=sleeps.append)
    assert site.calls == [BASE + "page-1.html"]
    assert sleeps == []
    assert len(df) == 20


def test_crawl_stops_on_loop_and_dedupes(nb):
    # trang 2 trả lại nội dung trang 1: link next của nó lại trỏ về page-2.html -> phải dừng, không lặp vô hạn
    site = FakeSite({BASE + "page-1.html": PAGE1, BASE + "page-2.html": PAGE1})
    df = nb.crawl(site, BASE + "page-1.html", sleep=lambda s: None)
    assert site.calls == [BASE + "page-1.html", BASE + "page-2.html"]
    assert len(df) == 20
    assert df["url"].is_unique
    assert isinstance(df, pd.DataFrame)
