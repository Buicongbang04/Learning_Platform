import json
from collections import Counter

from dateutil import parser

BUILD_ID = "dev"

ORDERS = [
    ("e481f51cbdc54678b7cc49136f2d6af7", "2017-10-02 10:56:33", "SP"),
    ("53cdb2fc8bc7dce0b6741e2150273451", "2018-07-24 20:41:37", "BA"),
    ("47770eb9100c2d0c44946d9cf07ec65d", "2018-08-08 08:38:49", "GO"),
    ("949d5b44dbf5de918fe9c16f97b45f8a", "2017-11-18 19:28:06", "RN"),
    ("ad21c59c0840e6cb83a9ceb5573f8159", "2018-02-13 21:18:39", "SP"),
]


def orders_per_month() -> dict[str, int]:
    return dict(sorted(Counter(parser.parse(ts).strftime("%Y-%m") for _, ts, _ in ORDERS).items()))


if __name__ == "__main__":
    print(json.dumps({"build_id": BUILD_ID, "orders_per_month": orders_per_month()}))
