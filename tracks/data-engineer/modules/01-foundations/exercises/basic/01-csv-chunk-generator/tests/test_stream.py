import inspect
import itertools
from decimal import Decimal

import pytest

from testkit import Exercise

ex = Exercise(__file__)

CSV_TEXT = """order_id,order_item_id,product_id,seller_id,price,freight_value
o1,1,p1,s1,50.00,8.50
o1,2,p2,s2,30.00,8.50
o2,1,p1,s1,52.00,12.00
o3,1,p3,s3,199.90,20.10
o3,2,p3,s3,199.90,20.10
o4,1,p2,,29.00,15.00
o5,1,p4,s1,abc,18.30
o6,1,p4,s2,-5.00,1.00
o7,1,p1,s4,48.00,18.30
"""


@pytest.fixture()
def csv_path(tmp_path):
    path = tmp_path / "order_items.csv"
    path.write_text(CSV_TEXT, encoding="utf-8")
    return str(path)


@pytest.fixture(scope="module")
def stream():
    return ex.module("stream.py")


def test_read_rows_is_lazy_generator(stream, csv_path):
    rows = stream.read_rows(csv_path)
    assert inspect.isgenerator(rows), "read_rows phải là generator (dùng yield)"
    first = next(rows)
    assert first == {
        "order_id": "o1",
        "order_item_id": "1",
        "product_id": "p1",
        "seller_id": "s1",
        "price": "50.00",
        "freight_value": "8.50",
    }
    assert len(list(rows)) == 8


def test_batched_sizes(stream):
    assert list(stream.batched(range(7), 3)) == [[0, 1, 2], [3, 4, 5], [6]]
    assert list(stream.batched([], 3)) == []
    assert list(stream.batched("abcd", 2)) == [["a", "b"], ["c", "d"]]


def test_batched_works_on_infinite_iterator(stream):
    batches = stream.batched(itertools.count(), 4)
    assert inspect.isgenerator(batches)
    assert next(batches) == [0, 1, 2, 3]
    assert next(batches) == [4, 5, 6, 7]


def test_batched_rejects_bad_size(stream):
    with pytest.raises(ValueError):
        list(stream.batched([1, 2], 0))


def test_parse_item_ok(stream):
    seller, amount = stream.parse_item(
        {"seller_id": "s1", "price": "0.10", "freight_value": "0.20"}
    )
    assert seller == "s1"
    assert isinstance(amount, Decimal)
    assert amount == Decimal("0.30")


@pytest.mark.parametrize(
    "row",
    [
        {"seller_id": "", "price": "1", "freight_value": "1"},
        {"seller_id": "s1", "price": "abc", "freight_value": "1"},
        {"seller_id": "s1", "price": "1", "freight_value": ""},
        {"seller_id": "s1", "price": "-1", "freight_value": "1"},
        {"seller_id": "s1", "price": "1", "freight_value": "-0.01"},
    ],
)
def test_parse_item_rejects(stream, row):
    with pytest.raises(ValueError):
        stream.parse_item(row)


def test_revenue_by_seller(stream, csv_path):
    result = stream.revenue_by_seller(csv_path, batch_size=4)
    assert result["rows"] == 9
    assert result["bad_rows"] == 3
    assert result["batches"] == 3
    assert result["revenue"] == {
        "s1": Decimal("122.50"),
        "s2": Decimal("38.50"),
        "s3": Decimal("440.00"),
        "s4": Decimal("66.30"),
    }


def test_revenue_by_seller_batch_size_does_not_change_result(stream, csv_path):
    a = stream.revenue_by_seller(csv_path, batch_size=1)
    b = stream.revenue_by_seller(csv_path, batch_size=100)
    assert a["revenue"] == b["revenue"]
    assert (a["batches"], b["batches"]) == (9, 1)
