"""Sinh dữ liệu giả cùng schema với Brazilian E-Commerce Public Dataset by Olist.

Tạo 9 tệp CSV trùng tên và trùng cột với bộ thật trên Kaggle, nên code viết cho dữ liệu giả
chạy được nguyên với dữ liệu thật (xem data/download_olist.py).

    uv run python data/generate_olist.py                       # 50 000 đơn, ghi vào data/raw/
    uv run python data/generate_olist.py --orders 2000 --out /tmp/olist
    uv run python data/generate_olist.py --orders 500000 --out data/raw_big --seed 7

Dữ liệu có chủ đích chứa các ca biên giống bộ thật:
- đơn `canceled` / `unavailable` (không có ngày giao, đơn `unavailable` không có item),
- đơn giao trễ (order_delivered_customer_date > order_estimated_delivery_date),
- đơn `delivered` nhưng thiếu order_delivered_customer_date,
- đơn không có review, review không có tiêu đề / nội dung,
- sản phẩm thiếu category hoặc thiếu kích thước, category không có trong bảng dịch,
- khách hàng mua nhiều lần (customer_unique_id lặp, customer_id luôn mới mỗi đơn),
- đơn trả bằng nhiều phương thức (payment_sequential > 1), voucher, trả góp.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

DEFAULT_OUT = Path(__file__).resolve().parent / "raw"

FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "translation": "product_category_name_translation.csv",
}

# (category pt, category en, trọng số, khoảng giá BRL)
CATEGORIES = [
    ("cama_mesa_banho", "bed_bath_table", 11, (20, 250)),
    ("beleza_saude", "health_beauty", 9, (10, 300)),
    ("esporte_lazer", "sports_leisure", 8, (15, 400)),
    ("moveis_decoracao", "furniture_decor", 7, (30, 600)),
    ("informatica_acessorios", "computers_accessories", 7, (20, 900)),
    ("utilidades_domesticas", "housewares", 6, (10, 300)),
    ("relogios_presentes", "watches_gifts", 5, (50, 1200)),
    ("telefonia", "telephony", 4, (15, 1500)),
    ("ferramentas_jardim", "garden_tools", 4, (20, 350)),
    ("automotivo", "auto", 4, (20, 500)),
    ("brinquedos", "toys", 4, (15, 300)),
    ("cool_stuff", "cool_stuff", 3, (30, 500)),
    ("perfumaria", "perfumery", 3, (20, 400)),
    ("bebes", "baby", 3, (15, 400)),
    ("eletronicos", "electronics", 2, (15, 800)),
    ("papelaria", "stationery", 2, (5, 150)),
    ("fashion_bolsas_e_acessorios", "fashion_bags_accessories", 2, (15, 250)),
    ("pet_shop", "pet_shop", 2, (10, 250)),
    ("moveis_escritorio", "office_furniture", 1, (80, 900)),
    ("consoles_games", "consoles_games", 1, (30, 1500)),
    ("malas_acessorios", "luggage_accessories", 1, (40, 600)),
    ("construcao_ferramentas_construcao", "construction_tools_construction", 1, (20, 500)),
    ("eletrodomesticos", "home_appliances", 1, (40, 1200)),
    ("instrumentos_musicais", "musical_instruments", 1, (30, 2000)),
    ("livros_interesse_geral", "books_general_interest", 1, (10, 120)),
    ("alimentos", "food", 1, (5, 100)),
    ("bebidas", "drinks", 1, (5, 150)),
    ("audio", "audio", 1, (30, 700)),
    ("climatizacao", "air_conditioning", 1, (60, 1500)),
    ("market_place", "market_place", 1, (20, 300)),
    # Hai category có trong products nhưng KHÔNG có trong bảng dịch (giống bộ thật).
    ("pc_gamer", None, 0.3, (500, 4000)),
    ("portateis_cozinha_e_preparadores_de_alimentos", None, 0.3, (50, 600)),
]

# Phân bố bang gần đúng bộ thật (SP chiếm ~42% khách hàng).
STATES = {
    "SP": 42, "RJ": 13, "MG": 12, "RS": 5.5, "PR": 5, "SC": 3.7, "BA": 3.4, "DF": 2.2,
    "ES": 2, "GO": 2, "PE": 1.7, "CE": 1.3, "PA": 1, "MT": 0.9, "MA": 0.8, "MS": 0.7,
    "PB": 0.5, "PI": 0.5, "RN": 0.5, "AL": 0.4, "SE": 0.3, "TO": 0.3, "RO": 0.25,
    "AM": 0.15, "AC": 0.08, "AP": 0.07, "RR": 0.05,
}
# Tâm gần đúng (lat, lng) và tiền tố CEP (2 chữ số đầu) của từng bang.
STATE_GEO = {
    "SP": (-23.0, -47.5, (1, 19)), "RJ": (-22.5, -43.2, (20, 28)), "ES": (-19.8, -40.5, (29, 29)),
    "MG": (-19.5, -44.5, (30, 39)), "BA": (-12.9, -40.0, (40, 48)), "SE": (-10.9, -37.3, (49, 49)),
    "PE": (-8.3, -36.0, (50, 56)), "AL": (-9.6, -36.4, (57, 57)), "PB": (-7.2, -36.3, (58, 58)),
    "RN": (-5.8, -36.5, (59, 59)), "CE": (-4.5, -39.3, (60, 63)), "PI": (-7.0, -42.5, (64, 64)),
    "MA": (-4.5, -44.8, (65, 65)), "PA": (-3.5, -51.0, (66, 68)), "AP": (0.5, -51.5, (68, 68)),
    "AM": (-3.4, -62.0, (69, 69)), "RR": (2.5, -61.0, (69, 69)), "AC": (-9.5, -69.0, (69, 69)),
    "DF": (-15.8, -47.9, (70, 73)), "GO": (-16.3, -49.5, (72, 76)), "TO": (-10.2, -48.3, (77, 77)),
    "MT": (-13.0, -56.0, (78, 78)), "RO": (-10.9, -62.8, (76, 76)), "MS": (-20.5, -54.6, (79, 79)),
    "PR": (-24.8, -51.5, (80, 87)), "SC": (-27.2, -50.4, (88, 89)), "RS": (-29.7, -53.0, (90, 99)),
}

ORDER_STATUS = {
    "delivered": 96.5, "shipped": 1.1, "canceled": 0.65, "unavailable": 0.6,
    "invoiced": 0.32, "processing": 0.3, "created": 0.05, "approved": 0.03,
}
PAYMENT_TYPES = {"credit_card": 74, "boleto": 19, "voucher": 5.5, "debit_card": 1.5}

REVIEW_TITLES = ["Recomendo", "Ótimo", "Muito bom", "Bom", "Excelente", "Super recomendo",
                 "Não recebi", "Produto com defeito", "Atrasou", "Ruim", "Gostei", "Perfeito"]
POSITIVE = ["Produto chegou antes do prazo, muito bom.", "Recomendo o vendedor, tudo certo.",
            "Ótima qualidade, chegou bem embalado.", "Entrega rápida e produto conforme anúncio.",
            "Gostei muito, comprarei novamente."]
NEGATIVE = ["Ainda não recebi o produto.", "Produto veio com defeito, quero devolver.",
            "Entrega atrasou muito e ninguém responde.", "Veio diferente do anunciado.",
            "Recebi apenas um dos itens que comprei."]

START = datetime(2016, 9, 4)
END = datetime(2018, 10, 17)


class Gen:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        Faker.seed(seed)
        self.fake = Faker("pt_BR")
        self.fake.seed_instance(seed)

    def hex_id(self) -> str:
        return f"{self.rng.getrandbits(128):032x}"

    def pick(self, weights: dict):
        return self.rng.choices(list(weights), weights=list(weights.values()))[0]


def fmt(ts: datetime | None) -> str:
    return ts.strftime("%Y-%m-%d %H:%M:%S") if ts else ""


def write_csv(path: Path, header: list[str], rows) -> int:
    n = 0
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row in rows:
            w.writerow(["" if v is None else v for v in row])
            n += 1
    return n


def build_locations(g: Gen, n_zips: int) -> list[tuple[str, str, str, float, float]]:
    """Mỗi phần tử: (zip_prefix, city, state, lat, lng)."""
    locs, used = [], set()
    while len(locs) < n_zips:
        state = g.pick(STATES)
        lat0, lng0, (lo, hi) = STATE_GEO[state]
        prefix = f"{g.rng.randint(lo, hi):02d}{g.rng.randint(0, 999):03d}"
        if prefix in used:
            continue
        used.add(prefix)
        city = g.fake.city().lower()
        locs.append((prefix, city, state, lat0 + g.rng.uniform(-2, 2), lng0 + g.rng.uniform(-2, 2)))
    return locs


def generate(n_orders: int, out: Path, seed: int) -> dict[str, int]:
    g = Gen(seed)
    rng = g.rng
    out.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}

    # --- geolocation: nhiều dòng (toạ độ hơi lệch) cho mỗi zip prefix, như bộ thật ---
    locations = build_locations(g, max(50, n_orders // 12))
    geo_rows = []
    for prefix, city, state, lat, lng in locations:
        for _ in range(rng.randint(1, 4)):
            geo_rows.append((prefix, round(lat + rng.gauss(0, 0.02), 14),
                             round(lng + rng.gauss(0, 0.02), 14), city, state))
    counts["geolocation"] = write_csv(out / FILES["geolocation"], [
        "geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng",
        "geolocation_city", "geolocation_state"], geo_rows)

    def location():
        # ~0.3% zip không có trong geolocation (giống bộ thật).
        if rng.random() < 0.003:
            state = g.pick(STATES)
            lo, hi = STATE_GEO[state][2]
            return f"{rng.randint(lo, hi):02d}{rng.randint(0, 999):03d}", g.fake.city().lower(), state
        loc = rng.choice(locations)
        return loc[0], loc[1], loc[2]

    # --- translation ---
    counts["translation"] = write_csv(
        out / FILES["translation"], ["product_category_name", "product_category_name_english"],
        [(pt, en) for pt, en, _, _ in CATEGORIES if en is not None])

    # --- sellers ---
    n_sellers = max(20, n_orders // 32)
    sellers = []
    for _ in range(n_sellers):
        z, c, s = location()
        sellers.append((g.hex_id(), z, c, s))
    counts["sellers"] = write_csv(out / FILES["sellers"], [
        "seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"], sellers)
    seller_ids = [s[0] for s in sellers]
    # Một số seller bán rất nhiều (phân phối lệch).
    seller_weights = list(itertools.accumulate(rng.paretovariate(1.2) for _ in seller_ids))

    # --- products ---
    n_products = max(50, int(n_orders * 0.33))
    cat_weights = [c[2] for c in CATEGORIES]
    products, product_price = [], {}
    for _ in range(n_products):
        pid = g.hex_id()
        pt, _en, _w, (lo, hi) = rng.choices(CATEGORIES, weights=cat_weights)[0]
        missing_cat = rng.random() < 0.0185
        missing_dim = rng.random() < 0.001
        products.append((
            pid,
            None if missing_cat else pt,
            None if missing_cat else rng.randint(5, 76),
            None if missing_cat else rng.randint(4, 3992),
            None if missing_cat else rng.choice([1, 1, 1, 1, 2, 2, 3, 4, 5, 6]),
            None if missing_dim else rng.choice([rng.randint(50, 2000), rng.randint(2000, 30000)]),
            None if missing_dim else rng.randint(7, 105),
            None if missing_dim else rng.randint(2, 105),
            None if missing_dim else rng.randint(6, 118),
        ))
        product_price[pid] = round(min(hi, max(lo * 0.5, rng.lognormvariate(0, 0.6) * (lo + hi) / 4)), 2)
    counts["products"] = write_csv(out / FILES["products"], [
        "product_id", "product_category_name", "product_name_lenght", "product_description_lenght",
        "product_photos_qty", "product_weight_g", "product_length_cm", "product_height_cm",
        "product_width_cm"], products)
    product_ids = [p[0] for p in products]
    product_weights = list(itertools.accumulate(rng.paretovariate(1.5) for _ in product_ids))

    # --- customers + orders + items + payments + reviews ---
    customers, orders, items, payments, reviews = [], [], [], [], []
    unique_pool: list[tuple[str, tuple]] = []  # (customer_unique_id, location) để mua lại
    span = (END - START).total_seconds()

    for _ in range(n_orders):
        # Khách quay lại ~3%: customer_unique_id lặp nhưng customer_id luôn mới.
        if unique_pool and rng.random() < 0.03:
            unique_id, loc = rng.choice(unique_pool)
        else:
            unique_id, loc = g.hex_id(), location()
            unique_pool.append((unique_id, loc))
        customer_id = g.hex_id()
        customers.append((customer_id, unique_id, *loc))

        order_id = g.hex_id()
        # Đơn tăng dần theo thời gian (sqrt để lệch về cuối giai đoạn).
        purchase = START + timedelta(seconds=span * (rng.random() ** 0.6))
        status = g.pick(ORDER_STATUS)
        estimated = (purchase + timedelta(days=rng.randint(10, 45))).replace(hour=0, minute=0, second=0)
        approved = carrier = delivered = None

        if status not in ("created",):
            if not (status == "canceled" and rng.random() < 0.15):
                approved = purchase + timedelta(minutes=rng.choice([rng.randint(5, 60), rng.randint(60, 4320)]))
        if status in ("shipped", "delivered") and approved:
            carrier = approved + timedelta(hours=rng.randint(12, 24 * 7))
        if status == "delivered" and carrier:
            late = rng.random() < 0.08
            if late:
                delivered = estimated + timedelta(days=rng.randint(1, 30), hours=rng.randint(0, 23))
            else:
                delivered = carrier + timedelta(hours=rng.randint(24, 24 * 20))
                if delivered > estimated:
                    delivered = estimated - timedelta(hours=rng.randint(1, 72))
                    delivered = max(delivered, carrier + timedelta(hours=6))
            # ~0.2% đơn delivered thiếu ngày giao (hoặc thiếu ngày duyệt), như bộ thật.
            r = rng.random()
            if r < 0.002:
                delivered = None
            elif r < 0.004:
                approved = None
        if status == "canceled" and approved and rng.random() < 0.1:
            carrier = approved + timedelta(days=rng.randint(1, 5))  # huỷ sau khi đã giao cho hãng vận chuyển

        orders.append((order_id, customer_id, status, fmt(purchase), fmt(approved),
                       fmt(carrier), fmt(delivered), fmt(estimated)))

        # Items: đơn unavailable / created không có item.
        total = 0.0
        if status not in ("unavailable", "created") or rng.random() < 0.05:
            n_items = rng.choices([1, 2, 3, 4, 5, 6], weights=[88, 8, 2, 1, 0.6, 0.4])[0]
            seller = rng.choices(seller_ids, cum_weights=seller_weights)[0]
            product = rng.choices(product_ids, cum_weights=product_weights)[0]
            shipping_limit = (approved or purchase) + timedelta(days=rng.randint(2, 7))
            for i in range(1, n_items + 1):
                # Phần lớn đơn nhiều item là cùng sản phẩm (mua số lượng > 1).
                if i > 1 and rng.random() < 0.3:
                    product = rng.choices(product_ids, cum_weights=product_weights)[0]
                    if rng.random() < 0.3:
                        seller = rng.choices(seller_ids, cum_weights=seller_weights)[0]
                price = product_price[product]
                freight = round(max(0.0, rng.gauss(20, 12)) if rng.random() > 0.003 else 0.0, 2)
                items.append((order_id, i, product, seller, fmt(shipping_limit), f"{price:.2f}", f"{freight:.2f}"))
                total += price + freight

        # Payments: tổng payment_value = tổng price + freight.
        if total == 0:
            total = round(rng.uniform(20, 200), 2)  # đơn không item vẫn có payment (giống bộ thật)
        ptype = g.pick(PAYMENT_TYPES)
        seq = 1
        if ptype == "voucher" or rng.random() < 0.03:
            n_vouchers = rng.choice([1, 1, 2, 3])
            remaining = total
            for _v in range(n_vouchers):
                part = round(remaining * rng.uniform(0.1, 0.6), 2)
                payments.append((order_id, seq, "voucher", 1, f"{part:.2f}"))
                remaining -= part
                seq += 1
            ptype = "credit_card" if rng.random() < 0.7 else "boleto"
            total = remaining
        installments = rng.choices([1, 2, 3, 4, 5, 6, 8, 10], weights=[50, 12, 10, 7, 5, 5, 4, 7])[0] \
            if ptype == "credit_card" else 1
        if ptype == "credit_card" and rng.random() < 0.0005:
            installments = 0  # giá trị lạ có trong bộ thật
        payments.append((order_id, seq, ptype, installments, f"{total:.2f}"))

        # Reviews: ~1% đơn không có review; ~59% review không có nội dung.
        if rng.random() > 0.01:
            late = delivered is not None and delivered > estimated
            bad = status in ("canceled", "unavailable") or late or (status == "delivered" and delivered is None)
            score = rng.choices([1, 2, 3, 4, 5], weights=[45, 12, 15, 13, 15] if bad else [7, 2, 7, 20, 64])[0]
            base = delivered or (estimated if status not in ("canceled", "unavailable") else purchase + timedelta(days=rng.randint(5, 30)))
            created = base.replace(hour=0, minute=0, second=0) + timedelta(days=1)
            answered = created + timedelta(hours=rng.randint(2, 24 * 5), minutes=rng.randint(0, 59))
            title = rng.choice(REVIEW_TITLES) if rng.random() < 0.12 else None
            message = None
            if rng.random() < 0.41:
                message = rng.choice(NEGATIVE if score <= 2 else POSITIVE)
                if rng.random() < 0.3:
                    message += " " + g.fake.sentence(nb_words=8)
            reviews.append((g.hex_id(), order_id, score, title, message, fmt(created), fmt(answered)))

    counts["customers"] = write_csv(out / FILES["customers"], [
        "customer_id", "customer_unique_id", "customer_zip_code_prefix", "customer_city",
        "customer_state"], customers)
    counts["orders"] = write_csv(out / FILES["orders"], [
        "order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date"], orders)
    counts["order_items"] = write_csv(out / FILES["order_items"], [
        "order_id", "order_item_id", "product_id", "seller_id", "shipping_limit_date", "price",
        "freight_value"], items)
    counts["order_payments"] = write_csv(out / FILES["order_payments"], [
        "order_id", "payment_sequential", "payment_type", "payment_installments",
        "payment_value"], payments)
    counts["order_reviews"] = write_csv(out / FILES["order_reviews"], [
        "review_id", "order_id", "review_score", "review_comment_title", "review_comment_message",
        "review_creation_date", "review_answer_timestamp"], reviews)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Sinh dữ liệu giả cùng schema bộ Olist.")
    parser.add_argument("--orders", type=int, default=50_000, help="số đơn hàng (mặc định 50000)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="thư mục ghi CSV (mặc định data/raw)")
    parser.add_argument("--seed", type=int, default=42, help="seed cố định để dữ liệu lặp lại được")
    args = parser.parse_args()

    t0 = time.perf_counter()
    counts = generate(args.orders, args.out, args.seed)
    print(f"Đã ghi vào {args.out.resolve()} ({time.perf_counter() - t0:.1f}s):")
    for key, name in FILES.items():
        print(f"  {name:<45} {counts[key]:>9,} dòng")


if __name__ == "__main__":
    main()
