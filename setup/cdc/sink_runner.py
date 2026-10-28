"""Consumer lab: DB commit trước, Kafka commit đúng partition sau."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
import time
from pathlib import Path

from kafka import KafkaConsumer, TopicPartition
from kafka.structs import OffsetAndMetadata

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "tracks/data-engineer/modules/07-streaming-kafka"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solution", action="store_true", help="Dùng lời giải; mặc định dùng starter đã làm")
    parser.add_argument("--db", type=Path, default=Path("/tmp/olist-cdc-lab.sqlite"))
    parser.add_argument("--bootstrap", default="localhost:19094")
    parser.add_argument("--group", default="olist-cdc-sink")
    parser.add_argument("--topic", default="olist_cdc.public.orders")
    parser.add_argument("--idle-seconds", type=float, default=15)
    parser.add_argument("--crash-after-db-commit", action="store_true")
    args = parser.parse_args()
    if args.idle_seconds <= 0:
        parser.error("--idle-seconds phải dương")
    target = (MODULE / "solutions/intermediate/04-cdc-sink/cdc_sink.py" if args.solution else
              MODULE / "exercises/intermediate/04-cdc-sink/starter/cdc_sink.py")
    spec = importlib.util.spec_from_file_location("lab_cdc_sink", target)
    sink = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sink)
    con = sqlite3.connect(args.db)
    consumer = None
    try:
        sink.initialize(con)
        consumer = KafkaConsumer(
            args.topic, bootstrap_servers=args.bootstrap, group_id=args.group,
            auto_offset_reset="earliest", enable_auto_commit=False,
            key_deserializer=lambda b: None if b is None else json.loads(b),
            value_deserializer=lambda b: None if b is None else json.loads(b),
        )
        deadline = time.monotonic() + args.idle_seconds
        while time.monotonic() < deadline:
            for records in consumer.poll(timeout_ms=500, max_records=100).values():
                for record in records:
                    applied = sink.apply_record(con, record.topic, record.partition,
                                                record.offset, record.key, record.value)
                    print(json.dumps({"topic": record.topic, "partition": record.partition,
                                      "offset": record.offset, "applied": applied}), flush=True)
                    if args.crash_after_db_commit and applied:
                        raise SystemExit("Crash mô phỏng sau DB commit, trước Kafka commit")
                    consumer.commit({TopicPartition(record.topic, record.partition):
                                     OffsetAndMetadata(record.offset + 1, "")})
                    deadline = time.monotonic() + args.idle_seconds
        print("orders:", con.execute("SELECT * FROM orders ORDER BY order_id").fetchall())
    finally:
        if consumer is not None:
            consumer.close(autocommit=False)
        con.close()


if __name__ == "__main__":
    main()
