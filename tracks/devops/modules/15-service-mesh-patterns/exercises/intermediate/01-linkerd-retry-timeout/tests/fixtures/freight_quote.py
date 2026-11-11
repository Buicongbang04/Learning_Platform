import json
import os
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

rng = random.Random(int(os.environ.get("SEED", "15")))
FAIL_RATE = float(os.environ.get("FAIL_RATE", "0.2"))
SLOW_RATE = float(os.environ.get("SLOW_RATE", "0.1"))
SLOW_SECONDS = float(os.environ.get("SLOW_SECONDS", "2.5"))
lock = threading.Lock()
counts = {"GET /quote": 0, "POST /reserve": 0}


def draw() -> float:
    with lock:
        return rng.random()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    disable_nagle_algorithm = True

    def reply(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def handle_one(self, key: str) -> None:
        with lock:
            counts[key] += 1
        roll = draw()
        if roll < FAIL_RATE:
            self.reply(503, {"error": "quote engine overloaded"})
        elif roll < FAIL_RATE + SLOW_RATE:
            time.sleep(SLOW_SECONDS)
            self.reply(200, {"price": 19.9, "slow": True})
        else:
            self.reply(200, {"price": 19.9})

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/healthz":
            self.reply(200, {"status": "ok"})
        elif path == "/stats":
            with lock:
                self.reply(200, dict(counts))
        elif path == "/quote":
            self.handle_one("GET /quote")
        else:
            self.reply(404, {"error": "not found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        if urlparse(self.path).path == "/reserve":
            self.handle_one("POST /reserve")
        else:
            self.reply(404, {"error": "not found"})

    def log_message(self, *args) -> None:
        pass


ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
