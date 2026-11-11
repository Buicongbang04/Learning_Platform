import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

WORKERS = int(os.environ.get("WORKERS", "2"))
SERVICE_MS = float(os.environ.get("SERVICE_MS", "40"))
SLOTS = threading.Semaphore(WORKERS)


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
            self.reply(200, {"status": "ok"})
            return
        SLOTS.acquire()
        try:
            time.sleep(SERVICE_MS / 1000)
        finally:
            SLOTS.release()
        self.reply(200, {"order_id": self.path.rsplit("/", 1)[-1], "status": "delivered"})

    def log_message(self, *args) -> None:
        pass


server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
server.daemon_threads = True
print(f"listening workers={WORKERS} service_ms={SERVICE_MS}", flush=True)
server.serve_forever()
