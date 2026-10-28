"""Sinh order/shipment events dạng JSON để luyện streaming (module 07, capstone M07).

Mỗi đơn đi qua vòng đời:
    order_created -> order_approved -> payment_confirmed -> shipped -> delivered
hoặc dừng giữa chừng bằng `canceled`. Nhiều đơn chạy xen kẽ nhau.

Có chủ đích chèn:
- **event trùng** (`--dup-rate`): cùng `event_id`, gửi lại lần nữa (mô phỏng producer retry,
  at-least-once). Consumer phải dedup theo `event_id`.
- **event đến trễ** (`--late-rate`): `event_time` cũ hơn nhiều so với `ingest_time`, và đến sau
  các event mới hơn của cùng đơn (out-of-order). Dùng để luyện watermark / xử lý late data.

Ví dụ:
    uv run python data/simulate_events.py --count 20 --stdout
    uv run python data/simulate_events.py --count 5000 --out data/raw/events.jsonl
    uv run python data/simulate_events.py --kafka --rate 20               # chạy tới khi Ctrl+C
    uv run python data/simulate_events.py --kafka --count 1000 --topic olist.order-events \\
        --bootstrap localhost:9094 --dup-rate 0.05 --late-rate 0.05
    # Dùng order_id/customer_id có thật từ dữ liệu đã sinh:
    uv run python data/simulate_events.py --count 100 --stdout --orders-csv data/raw

Schema một event:
    {
      "event_id": "uuid",                 # khoá dedup
      "event_type": "shipped",
      "order_id": "32 hex", "customer_id": "32 hex", "seller_id": "32 hex",
      "event_time": "2026-10-28T08:15:02.123Z",   # lúc sự việc xảy ra (event time)
      "ingest_time": "2026-10-28T08:15:02.456Z",  # lúc gửi đi (processing time)
      "payload": {...}                    # tuỳ event_type
    }
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

LIFECYCLE = ["order_created", "order_approved", "payment_confirmed", "shipped", "delivered"]
CARRIERS = ["correios", "jadlog", "total_express", "loggi", "azul_cargo"]
PAYMENT_TYPES = ["credit_card", "credit_card", "credit_card", "boleto", "voucher", "debit_card"]
STATES = ["SP", "SP", "SP", "RJ", "MG", "RS", "PR", "SC", "BA", "DF", "GO", "PE"]
CANCEL_REASONS = ["customer_request", "payment_refused", "out_of_stock", "fraud_suspected"]


def iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def load_ids(raw_dir: Path) -> list[tuple[str, str, str]]:
    """Đọc (order_id, customer_id, seller_id) từ CSV do generate_olist.py sinh ra."""
    sellers: dict[str, str] = {}
    with (raw_dir / "olist_order_items_dataset.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sellers.setdefault(row["order_id"], row["seller_id"])
    ids = []
    with (raw_dir / "olist_orders_dataset.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["order_id"] in sellers:
                ids.append((row["order_id"], row["customer_id"], sellers[row["order_id"]]))
    return ids


class Simulator:
    def __init__(self, seed: int, dup_rate: float, late_rate: float, cancel_rate: float,
                 start: datetime, ids: list[tuple[str, str, str]] | None = None,
                 max_active: int = 50):
        self.rng = random.Random(seed)
        self.dup_rate = dup_rate
        self.late_rate = late_rate
        self.cancel_rate = cancel_rate
        self.clock = start
        self.ids = list(ids) if ids else None
        if self.ids:
            self.rng.shuffle(self.ids)
        self.id_pos = 0
        self.max_active = max_active
        self.active: list[dict] = []
        self.delayed: list[tuple[int, dict]] = []  # (bước sẽ phát, event)
        self.step = 0
        self.sellers = [self._hex() for _ in range(30)]

    def _hex(self) -> str:
        return f"{self.rng.getrandbits(128):032x}"

    def _new_order(self) -> dict:
        if self.ids:
            # Lấy lần lượt theo thứ tự đã xáo, hết thì vòng lại: mỗi order_id chỉ chạy một lần mỗi vòng.
            order_id, customer_id, seller_id = self.ids[self.id_pos % len(self.ids)]
            self.id_pos += 1
        else:
            order_id, customer_id, seller_id = self._hex(), self._hex(), self.rng.choice(self.sellers)
        n_items = self.rng.choices([1, 2, 3], weights=[88, 9, 3])[0]
        amount = round(sum(self.rng.uniform(15, 400) for _ in range(n_items)) + self.rng.uniform(5, 40), 2)
        return {"order_id": order_id, "customer_id": customer_id, "seller_id": seller_id,
                "stage": 0, "amount": amount, "n_items": n_items,
                "state": self.rng.choice(STATES), "will_cancel": self.rng.random() < self.cancel_rate}

    def _event(self, order: dict, event_type: str) -> dict:
        payload: dict = {}
        if event_type == "order_created":
            payload = {"order_status": "created", "items": order["n_items"],
                       "total_amount": order["amount"], "currency": "BRL",
                       "customer_state": order["state"]}
        elif event_type == "order_approved":
            payload = {"order_status": "approved"}
        elif event_type == "payment_confirmed":
            ptype = self.rng.choice(PAYMENT_TYPES)
            payload = {"payment_type": ptype, "payment_value": order["amount"],
                       "installments": self.rng.choice([1, 1, 2, 3, 6, 10]) if ptype == "credit_card" else 1}
        elif event_type == "shipped":
            payload = {"order_status": "shipped", "carrier": self.rng.choice(CARRIERS),
                       "tracking_code": f"BR{self.rng.randint(10**8, 10**9 - 1)}",
                       "estimated_delivery_date": (self.clock + timedelta(days=self.rng.randint(5, 25))).date().isoformat()}
        elif event_type == "delivered":
            payload = {"order_status": "delivered", "on_time": self.rng.random() > 0.08}
        elif event_type == "canceled":
            payload = {"order_status": "canceled", "reason": self.rng.choice(CANCEL_REASONS)}
        return {"event_id": str(uuid.UUID(int=self.rng.getrandbits(128), version=4)),
                "event_type": event_type, "order_id": order["order_id"],
                "customer_id": order["customer_id"], "seller_id": order["seller_id"],
                "event_time": iso(self.clock), "ingest_time": None, "payload": payload}

    def _next_raw(self) -> dict:
        """Chọn một đơn: tạo đơn mới hoặc đẩy một đơn đang chạy sang bước kế."""
        if not self.active or (len(self.active) < self.max_active and self.rng.random() < 0.35):
            order = self._new_order()
            self.active.append(order)
            return self._event(order, "order_created")
        order = self.rng.choice(self.active)
        order["stage"] += 1
        if order["will_cancel"] and order["stage"] >= self.rng.randint(1, 3):
            self.active.remove(order)
            return self._event(order, "canceled")
        event_type = LIFECYCLE[order["stage"]]
        if event_type == "delivered":
            self.active.remove(order)
        return self._event(order, event_type)

    def events(self, realtime_rate: float | None = None) -> Iterator[dict]:
        while True:
            self.step += 1
            if realtime_rate:
                self.clock = datetime.now(timezone.utc)
            else:
                self.clock += timedelta(seconds=self.rng.expovariate(2.0))

            # Phát event trễ đã tới hạn trước (event_time cũ, ingest_time mới).
            due = [e for s, e in self.delayed if s <= self.step]
            self.delayed = [(s, e) for s, e in self.delayed if s > self.step]
            for event in due:
                yield {**event, "ingest_time": iso(self.clock)}

            event = self._next_raw()
            if event["event_type"] != "order_created" and self.rng.random() < self.late_rate:
                # Lùi event_time 2–15 phút và giữ lại 5–30 bước rồi mới phát.
                event["event_time"] = iso(self.clock - timedelta(minutes=self.rng.uniform(2, 15)))
                self.delayed.append((self.step + self.rng.randint(5, 30), event))
                continue
            out = {**event, "ingest_time": iso(self.clock)}
            yield out
            if self.rng.random() < self.dup_rate:
                # Bản trùng: giống hệt (cùng event_id), chỉ khác ingest_time.
                dup_at = self.clock + timedelta(milliseconds=self.rng.randint(50, 3000))
                yield {**event, "ingest_time": iso(dup_at)}


def main() -> None:
    p = argparse.ArgumentParser(description="Sinh order/shipment events JSON (stdout, JSONL, Kafka).")
    dest = p.add_mutually_exclusive_group()
    dest.add_argument("--stdout", action="store_true", help="in mỗi event một dòng ra stdout (mặc định)")
    dest.add_argument("--out", type=Path, help="ghi ra tệp JSONL")
    dest.add_argument("--kafka", action="store_true", help="gửi vào Kafka")
    p.add_argument("--count", type=int, help="số event (gồm cả bản trùng). Bỏ trống với --kafka = chạy mãi")
    p.add_argument("--bootstrap", default="localhost:9094", help="Kafka bootstrap server")
    p.add_argument("--topic", default="olist.order-events")
    p.add_argument("--rate", type=float, help="event/giây theo thời gian thực (mặc định 10 với --kafka; "
                   "stdout/tệp: không đặt thì sinh ngay với đồng hồ giả lập)")
    p.add_argument("--dup-rate", type=float, default=0.03, help="tỉ lệ event bị gửi trùng (mặc định 0.03)")
    p.add_argument("--late-rate", type=float, default=0.03, help="tỉ lệ event đến trễ (mặc định 0.03)")
    p.add_argument("--cancel-rate", type=float, default=0.05, help="tỉ lệ đơn bị huỷ (mặc định 0.05)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--start", help="thời điểm bắt đầu của đồng hồ giả lập, ISO (mặc định: bây giờ)")
    p.add_argument("--orders-csv", type=Path, help="thư mục CSV Olist để lấy order_id/customer_id thật")
    args = p.parse_args()

    if args.count is None and not args.kafka:
        args.count = 100
    rate = args.rate if args.rate else (10.0 if args.kafka else None)
    start = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc) if args.start \
        else datetime.now(timezone.utc)
    ids = load_ids(args.orders_csv) if args.orders_csv else None
    sim = Simulator(args.seed, args.dup_rate, args.late_rate, args.cancel_rate, start, ids)

    producer = None
    sink = None
    if args.kafka:
        try:
            from kafka import KafkaProducer
        except ImportError:
            sys.exit("Thiếu thư viện kafka-python-ng. Chạy: uv sync")
        try:
            producer = KafkaProducer(
                bootstrap_servers=args.bootstrap,
                key_serializer=lambda k: k.encode(),
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode(),
                acks="all", linger_ms=20,
            )
        except Exception as exc:  # NoBrokersAvailable, ...
            sys.exit(f"Không kết nối được Kafka ở {args.bootstrap}: {exc}\n"
                     "Bật Kafka: docker compose -f setup/docker-compose.yml up -d kafka")
    elif args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        sink = args.out.open("w", encoding="utf-8")
    else:
        sink = sys.stdout

    sent = 0
    try:
        for event in sim.events(realtime_rate=rate):
            if producer:
                producer.send(args.topic, key=event["order_id"], value=event)
            else:
                sink.write(json.dumps(event, ensure_ascii=False) + "\n")
            sent += 1
            if args.count and sent >= args.count:
                break
            if rate:
                time.sleep(1.0 / rate)
            if producer and sent % 100 == 0:
                print(f"Đã gửi {sent} event vào {args.topic}", file=sys.stderr)
    except KeyboardInterrupt:
        pass
    finally:
        if producer:
            producer.flush()
            producer.close()
        if sink and sink is not sys.stdout:
            sink.close()
    dest_name = args.topic if producer else (args.out or "stdout")
    print(f"Xong: {sent} event -> {dest_name}", file=sys.stderr)


if __name__ == "__main__":
    main()
