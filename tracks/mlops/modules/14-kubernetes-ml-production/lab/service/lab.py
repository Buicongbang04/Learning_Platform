"""Service lab của module 14, chỉ dùng thư viện chuẩn. Vai trò chọn bằng biến `ROLE`.

- `predictor`: model ETA giả theo giao thức KServe v1 (`GET /v1/models/eta`, `POST /v1/models/eta:predict`). Mỗi
  request tốn `SERVICE_MS` mili giây và mỗi pod xử lý tối đa `CONCURRENCY` request cùng lúc, như một model server một
  worker: thông lượng của một pod có trần, muốn hơn thì thêm replica.
- `queue`: hàng đợi job suy luận batch trong bộ nhớ. `POST /enqueue {"n", "seconds"}`, `POST /take`, `POST /done`;
  `GET /pending` trả `{"pending": số job chưa xong}` (metric để autoscale), `GET /stats` trả số đếm và cold start.
- `worker`: lấy job từ `QUEUE_URL`, "suy luận" `seconds` giây mỗi job, báo xong. Nhận SIGTERM thì làm nốt job đang dở.

`MODEL_LOAD_SECONDS` giả thời gian nạp model lúc khởi động (predictor và worker).
"""

import json
import os
import signal
import sys
import threading
import time
import urllib.request
from collections import Counter, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROLE = os.environ.get("ROLE", "predictor")
PORT = int(os.environ.get("PORT", "8080"))
NAME = os.environ.get("MODEL_NAME", "eta")
POD = os.environ.get("HOSTNAME", "local")
LOAD_SECONDS = float(os.environ.get("MODEL_LOAD_SECONDS", "2"))
SERVICE_SECONDS = float(os.environ.get("SERVICE_MS", "25")) / 1000
SLOTS = threading.Semaphore(int(os.environ.get("CONCURRENCY", "1")))
LEASE_EXTRA = float(os.environ.get("LEASE_EXTRA_SECONDS", "10"))
MAX_ENQUEUE = 10_000
MAX_BODY = 1 << 20
COEF = (4.0, 2.1, 0.35, 0.8)


def predict(rows: list[list[float]]) -> list[float]:
    return [round(COEF[0] + COEF[1] * r[0] + COEF[2] * r[1] + COEF[3] * r[2], 4) for r in rows]


class BodyTooLarge(Exception):
    pass


class Queue:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.queued: deque = deque()
        self.inflight: dict[int, tuple[dict, float]] = {}
        self.next_id = 0
        self.done = 0
        self.pods: Counter = Counter()
        self.batch_started: float | None = None
        self.first_take: float | None = None

    def _expire(self, now: float) -> None:
        for job_id, (job, deadline) in list(self.inflight.items()):
            if now > deadline:
                del self.inflight[job_id]
                self.queued.appendleft(job)

    def pending(self) -> int:
        with self.lock:
            self._expire(time.monotonic())
            return len(self.queued) + len(self.inflight)

    def enqueue(self, n: int, seconds: float) -> int:
        with self.lock:
            now = time.monotonic()
            self._expire(now)
            if not self.queued and not self.inflight:
                self.batch_started, self.first_take = now, None
            for _ in range(n):
                self.queued.append({"id": self.next_id, "seconds": seconds})
                self.next_id += 1
            return len(self.queued) + len(self.inflight)

    def take(self) -> dict | None:
        with self.lock:
            now = time.monotonic()
            self._expire(now)
            if not self.queued:
                return None
            job = self.queued.popleft()
            self.inflight[job["id"]] = (job, now + 2 * job["seconds"] + LEASE_EXTRA)
            if self.first_take is None:
                self.first_take = now
            return job

    def finish(self, job_id: int, pod: str) -> None:
        with self.lock:
            if self.inflight.pop(job_id, None) is not None:
                self.done += 1
                self.pods[pod] += 1

    def stats(self) -> dict:
        with self.lock:
            cold = None
            if self.batch_started is not None and self.first_take is not None:
                cold = round(self.first_take - self.batch_started, 2)
            return {"queued": len(self.queued), "inflight": len(self.inflight), "done": self.done,
                    "pods": dict(self.pods), "cold_start_s": cold}


QUEUE = Queue()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def reply(self, status: int, payload: dict | None) -> None:
        body = json.dumps(payload).encode() if payload is not None else b""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 <= length <= MAX_BODY:
            raise BodyTooLarge(length)
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self.reply(200, {"role": ROLE, "pod": POD})
        elif ROLE == "predictor" and self.path == f"/v1/models/{NAME}":
            self.reply(200, {"name": NAME, "ready": True})
        elif ROLE == "queue" and self.path == "/pending":
            self.reply(200, {"pending": QUEUE.pending()})
        elif ROLE == "queue" and self.path == "/stats":
            self.reply(200, QUEUE.stats())
        else:
            self.reply(404, {"error": "not found"})

    def do_POST(self) -> None:
        try:
            payload = self.body()
        except BodyTooLarge:
            self.close_connection = True
            self.reply(413, {"error": f"body phải từ 0 đến {MAX_BODY} byte"})
            return
        except ValueError as error:
            self.reply(400, {"error": str(error)})
            return
        if not isinstance(payload, dict):
            self.reply(400, {"error": "body phải là object JSON"})
            return
        if ROLE == "predictor" and self.path == f"/v1/models/{NAME}:predict":
            rows = payload.get("instances")
            if not isinstance(rows, list) or not all(isinstance(r, list) and len(r) == 3 for r in rows):
                self.reply(400, {"error": "instances phải là danh sách [distance_km, hour, passengers]"})
                return
            with SLOTS:
                time.sleep(SERVICE_SECONDS)
            self.reply(200, {"predictions": predict(rows), "pod": POD})
        elif ROLE == "queue" and self.path == "/enqueue":
            try:
                n, seconds = int(payload.get("n", 1)), float(payload.get("seconds", 0.5))
            except (TypeError, ValueError):
                n, seconds = -1, -1.0
            if not (1 <= n <= MAX_ENQUEUE and 0 <= seconds <= 60):
                self.reply(400, {"error": f"n phải từ 1 đến {MAX_ENQUEUE}, seconds từ 0 đến 60"})
                return
            self.reply(200, {"pending": QUEUE.enqueue(n, seconds)})
        elif ROLE == "queue" and self.path == "/take":
            job = QUEUE.take()
            self.reply(200, {"job": job})
        elif ROLE == "queue" and self.path == "/done":
            try:
                job_id = int(payload["id"])
            except (KeyError, TypeError, ValueError):
                self.reply(400, {"error": "thiếu id"})
                return
            QUEUE.finish(job_id, str(payload.get("pod", "")))
            self.reply(200, {"ok": True})
        else:
            self.reply(404, {"error": "not found"})

    def log_message(self, format: str, *args) -> None:
        pass


def call(url: str, payload: dict) -> dict:
    request = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.load(response)


def work() -> None:
    queue_url = os.environ["QUEUE_URL"].rstrip("/")
    stopping = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopping.set())
    print(f"worker {POD} loading model ({LOAD_SECONDS}s)", flush=True)
    time.sleep(LOAD_SECONDS)
    print(f"worker {POD} ready, queue {queue_url}", flush=True)
    while not stopping.is_set():
        try:
            job = call(f"{queue_url}/take", {"pod": POD}).get("job")
        except OSError as error:
            print(f"queue unreachable: {error}", flush=True)
            stopping.wait(1)
            continue
        if job is None:
            stopping.wait(0.5)
            continue
        time.sleep(job["seconds"])
        try:
            call(f"{queue_url}/done", {"id": job["id"], "pod": POD})
        except OSError as error:
            print(f"cannot report job {job['id']}: {error}", flush=True)
    print(f"worker {POD} stopped", flush=True)


def serve() -> None:
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    if ROLE == "predictor":
        print(f"predictor {POD} loading model ({LOAD_SECONDS}s)", flush=True)
        time.sleep(LOAD_SECONDS)
    print(f"{ROLE} {POD} serving on :{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    if ROLE == "worker":
        work()
    elif ROLE in ("predictor", "queue"):
        serve()
    else:
        sys.exit(f"ROLE không hợp lệ: {ROLE}")
