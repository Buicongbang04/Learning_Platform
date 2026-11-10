import json
import os
import signal
import sys
import time
from datetime import datetime, timezone

stopping = False


def log(msg: str, **fields) -> None:
    print(json.dumps({"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), "msg": msg, **fields},
                     ensure_ascii=False), flush=True)


def request_stop(signum, _frame) -> None:
    global stopping
    stopping = True
    log("nhận tín hiệu, hoàn tất batch đang dở", signal=signal.Signals(signum).name)


def main() -> int:
    queue = os.environ.get("ORDER_SYNC_QUEUE")
    if not queue:
        log("thiếu ORDER_SYNC_QUEUE, dừng")
        return 2
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    log("order-sync sẵn sàng", queue=queue, pid=os.getpid())
    batch = 0
    while not stopping:
        batch += 1
        time.sleep(0.2)
    log("đã ack batch cuối, dừng sạch", queue=queue, batches=batch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
