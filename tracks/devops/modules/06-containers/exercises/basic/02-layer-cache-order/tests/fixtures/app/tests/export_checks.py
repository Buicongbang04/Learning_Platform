from export_orders import orders_per_month


def check_counts_every_order():
    assert sum(orders_per_month().values()) == 5
