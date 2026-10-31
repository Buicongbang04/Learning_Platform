from sqlalchemy import (Column, Engine, Float, ForeignKey, Integer, MetaData, String, Table,
                        create_engine, text)

metadata = MetaData()

customers = Table(
    "customers", metadata,
    Column("customer_id", String, primary_key=True),
    Column("customer_unique_id", String),
    Column("customer_city", String),
    Column("customer_state", String(2), index=True),
)

orders = Table(
    "orders", metadata,
    Column("order_id", String, primary_key=True),
    Column("customer_id", String, ForeignKey("customers.customer_id"), index=True),
    Column("order_status", String),
    Column("order_purchase_timestamp", String),
)

order_items = Table(
    "order_items", metadata,
    Column("order_id", String, ForeignKey("orders.order_id"), primary_key=True),
    Column("order_item_id", Integer, primary_key=True),
    Column("product_id", String),
    Column("seller_id", String),
    Column("price", Float, nullable=False),
    Column("freight_value", Float, nullable=False),
)

revenue_by_state = Table(
    "revenue_by_state", metadata,
    Column("state", String(2), primary_key=True),
    Column("revenue", Float, nullable=False),
)


def make_engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True)


def init(engine: Engine) -> None:
    metadata.create_all(engine)


def ping(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
