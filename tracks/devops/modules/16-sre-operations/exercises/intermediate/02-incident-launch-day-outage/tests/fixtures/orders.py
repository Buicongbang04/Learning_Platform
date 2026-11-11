import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RELEASES = {"2.3.0": (4, True), "2.4.0": (2, False), "2.4.1": (2, True)}
VERSION = os.environ.get("RELEASE", "2.3.0")
SLOTS_COUNT, WAITS = RELEASES[VERSION]
SLOTS = threading.Semaphore(SLOTS_COUNT)
SERVICE_SECONDS = 0.04


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def reply(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self.reply(200, {"status": "ok", "release": VERSION})
            return
        if not SLOTS.acquire(blocking=WAITS):
            self.reply(503, {"error": "service unavailable"})
            return
        try:
            time.sleep(SERVICE_SECONDS)
        finally:
            SLOTS.release()
        self.reply(200, {"order_id": self.path.rsplit("/", 1)[-1], "status": "delivered", "release": VERSION})

    def log_message(self, *args) -> None:
        pass


server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
server.daemon_threads = True
print(f"orders release {VERSION} listening", flush=True)
server.serve_forever()
