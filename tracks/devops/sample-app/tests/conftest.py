import csv
from pathlib import Path

import fakeredis
import pytest
from fastapi.testclient import TestClient

from olist_shop import db, seed
from olist_shop.main import create_app

CUSTOMERS = [
    ("c1", "u1", "01001", "sao paulo", "SP"),
    ("c2", "u2", "20010", "rio de janeiro", "RJ"),
]
ORDERS = [
    ("o1", "c1", "delivered", "2018-01-02 10:00:00", "", "", "", "2018-01-20 00:00:00"),
    ("o2", "c2", "delivered", "2018-01-03 11:00:00", "", "", "", "2018-01-21 00:00:00"),
    ("o3", "c2", "shipped", "2018-01-04 12:00:00", "", "", "", "2018-01-22 00:00:00"),
]
ITEMS = [
    ("o1", 1, "p1", "s1", "2018-01-05 00:00:00", "20.00", "3.00"),
    ("o1", 2, "p2", "s1", "2018-01-05 00:00:00", "10.00", "2.50"),
    ("o2", 1, "p1", "s2", "2018-01-06 00:00:00", "8.00", "2.00"),
    ("o3", 1, "p3", "s2", "2018-01-07 00:00:00", "5.00", "1.00"),
]


def _write(path: Path, header: list[str], rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


@pytest.fixture
def olist_dir(tmp_path):
    d = tmp_path / "olist"
    d.mkdir()
    _write(d / "olist_customers_dataset.csv", [
        "customer_id", "customer_unique_id", "customer_zip_code_prefix", "customer_city",
        "customer_state"], CUSTOMERS)
    _write(d / "olist_orders_dataset.csv", [
        "order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date"], ORDERS)
    _write(d / "olist_order_items_dataset.csv", [
        "order_id", "order_item_id", "product_id", "seller_id", "shipping_limit_date", "price",
        "freight_value"], ITEMS)
    return d


@pytest.fixture
def engine(tmp_path):
    e = db.make_engine(f"sqlite:///{tmp_path / 'shop.db'}")
    db.init(e)
    yield e
    e.dispose()


@pytest.fixture
def broken_engine(tmp_path):
    e = db.make_engine(f"sqlite:///{tmp_path / 'missing' / 'dir' / 'shop.db'}")
    yield e
    e.dispose()


@pytest.fixture
def fake_redis():
    return fakeredis.FakeRedis()


@pytest.fixture
def broken_redis():
    server = fakeredis.FakeServer()
    server.connected = False
    return fakeredis.FakeRedis(server=server)


@pytest.fixture
def client(engine, fake_redis):
    return TestClient(create_app(engine=engine, redis_client=fake_redis))


@pytest.fixture
def client_without_db(broken_engine, broken_redis):
    return TestClient(create_app(engine=broken_engine, redis_client=broken_redis))


@pytest.fixture
def client_seeded(client, engine, olist_dir):
    seed.load(engine, olist_dir)
    return client
