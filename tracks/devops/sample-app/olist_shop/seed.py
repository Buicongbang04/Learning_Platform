import argparse
import csv
import logging
from itertools import islice
from pathlib import Path

from sqlalchemy import Engine, delete, insert

from olist_shop import db, log
from olist_shop.settings import Settings

logger = logging.getLogger("olist_shop.seed")

ORDERS_CSV = "olist_orders_dataset.csv"
ITEMS_CSV = "olist_order_items_dataset.csv"
CUSTOMERS_CSV = "olist_customers_dataset.csv"


def _rows(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


def load(engine: Engine, olist_dir: Path, limit_orders: int = 5000) -> dict[str, int]:
    olist_dir = Path(olist_dir)
    orders = [
        {"order_id": r["order_id"], "customer_id": r["customer_id"], "order_status": r["order_status"],
         "order_purchase_timestamp": r["order_purchase_timestamp"]}
        for r in islice(_rows(olist_dir / ORDERS_CSV), limit_orders)
    ]
    order_ids = {o["order_id"] for o in orders}
    customer_ids = {o["customer_id"] for o in orders}
    items = [
        {"order_id": r["order_id"], "order_item_id": int(r["order_item_id"]), "product_id": r["product_id"],
         "seller_id": r["seller_id"], "price": float(r["price"]), "freight_value": float(r["freight_value"])}
        for r in _rows(olist_dir / ITEMS_CSV) if r["order_id"] in order_ids
    ]
    customers = [
        {"customer_id": r["customer_id"], "customer_unique_id": r["customer_unique_id"],
         "customer_city": r["customer_city"], "customer_state": r["customer_state"]}
        for r in _rows(olist_dir / CUSTOMERS_CSV) if r["customer_id"] in customer_ids
    ]
    db.init(engine)
    with engine.begin() as conn:
        for table in (db.revenue_by_state, db.order_items, db.orders, db.customers):
            conn.execute(delete(table))
        for table, rows in ((db.customers, customers), (db.orders, orders), (db.order_items, items)):
            if rows:
                conn.execute(insert(table), rows)
    counts = {"orders": len(orders), "order_items": len(items), "customers": len(customers)}
    logger.info("seed xong", extra=counts)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Nạp dữ liệu Olist vào database của Olist Shop.")
    parser.add_argument("olist_dir", type=Path, help="thư mục chứa CSV Olist (data/raw/olist hoặc thư mục sinh)")
    parser.add_argument("--limit-orders", type=int, default=5000, help="số đơn tối đa (mặc định 5000)")
    args = parser.parse_args()
    settings = Settings()
    log.configure(settings.log_level)
    counts = load(db.make_engine(settings.database_url), args.olist_dir, args.limit_orders)
    print(f"Đã nạp {counts['orders']} đơn, {counts['order_items']} dòng hàng, {counts['customers']} khách.")


if __name__ == "__main__":
    main()
