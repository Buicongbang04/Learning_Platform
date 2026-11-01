"""Backend giả của Olist Shop cho bài tập Nginx: cùng route với API thật, trả lại header proxy đã gửi tới."""

import json
import os
import re
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

INSTANCE = os.environ.get("INSTANCE", "api")
PORT = int(os.environ.get("PORT", "8000"))
ORDER = re.compile(r"^/orders/[^/]+$")
served: dict[str, int] = {}
lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "olist-shop-stub"

    def setup(self):
        super().setup()
        self.on_connection = 0

    def route(self, method: str, path: str) -> tuple[int, dict]:
        if method == "GET" and path == "/healthz":
            return 200, {"status": "ok", "version": INSTANCE}
        if method == "GET" and path == "/readyz":
            return 200, {"db": "ok", "redis": "ok"}
        if method == "GET" and ORDER.match(path):
            return 200, {"order_id": path.rsplit("/", 1)[1], "total": 129.9}
        if method == "GET" and path == "/stats/revenue-by-state":
            return 200, {"rows": [{"state": "SP", "revenue": 5202.5}, {"state": "RJ", "revenue": 1800.0}]}
        if method == "POST" and path == "/jobs/recompute":
            return 202, {"job_id": uuid.uuid4().hex}
        if method == "GET" and path == "/slow":
            return 200, {"slept": True}
        return 404, {"detail": "Not Found"}

    def respond(self, method: str) -> None:
        self.on_connection += 1
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        url = urlsplit(self.path)
        if url.path == "/slow":
            time.sleep(float(parse_qs(url.query).get("seconds", ["0"])[0]))
        status, body = self.route(method, url.path)
        with lock:
            served[url.path] = served.get(url.path, 0) + 1
            count = served[url.path]
        rid = self.headers.get("X-Request-ID") or uuid.uuid4().hex
        body.update(
            instance=INSTANCE,
            method=method,
            path=self.path,
            served=count,
            connection_requests=self.on_connection,
            host=self.headers.get("Host"),
            x_forwarded_for=self.headers.get("X-Forwarded-For"),
            x_forwarded_proto=self.headers.get("X-Forwarded-Proto"),
            x_real_ip=self.headers.get("X-Real-IP"),
            x_request_id=self.headers.get("X-Request-ID"),
            connection=self.headers.get("Connection"),
            http_version=self.request_version,
        )
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Request-ID", rid)
        self.send_header("X-Instance", INSTANCE)
        self.end_headers()
        if method != "HEAD":
            self.wfile.write(data)

    def do_GET(self):
        self.respond("GET")

    def do_HEAD(self):
        self.respond("HEAD")

    def do_POST(self):
        self.respond("POST")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.daemon_threads = True
    print(f"olist-shop-stub {INSTANCE} ready on {PORT}", flush=True)
    server.serve_forever()
