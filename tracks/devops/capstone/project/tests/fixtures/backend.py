"""API giả của Olist Shop cho M02: cùng route với API thật, ghi một dòng JSON mỗi request (có request_id) và trả lại
header proxy đã nhận.

Khác API thật một chỗ có chủ đích: khi không nhận được X-Request-ID, API thật tự sinh 32 ký tự hex, còn bản giả trả
`stub-...`. Nhờ vậy test phân biệt được id do Nginx sinh với id do backend tự sinh.
"""

import json
import os
import re
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

PORT = int(os.environ.get("PORT", "8000"))
ORDER = re.compile(r"^/orders/[^/]+$")
lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "olist-shop-stub"

    def route(self, method: str, path: str) -> tuple[int, dict]:
        if method == "GET" and path == "/healthz":
            return 200, {"status": "ok", "version": "stub"}
        if method == "GET" and path == "/readyz":
            return 200, {"db": "ok", "redis": "ok"}
        if method == "GET" and ORDER.match(path):
            return 200, {"order_id": path.rsplit("/", 1)[1], "total": 129.9}
        if method == "POST" and path == "/jobs/recompute":
            return 202, {"job_id": uuid.uuid4().hex}
        return 404, {"detail": "Not Found"}

    def respond(self, method: str) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        url = urlsplit(self.path)
        status, body = self.route(method, url.path)
        received = self.headers.get("X-Request-ID")
        rid = received or f"stub-{uuid.uuid4().hex[:12]}"
        body.update(
            method=method,
            path=self.path,
            host=self.headers.get("Host"),
            x_forwarded_for=self.headers.get("X-Forwarded-For"),
            x_forwarded_proto=self.headers.get("X-Forwarded-Proto"),
            x_real_ip=self.headers.get("X-Real-IP"),
            x_request_id=received,
        )
        with lock:
            print(json.dumps({"msg": "request", "request_id": rid, "method": method, "path": url.path,
                              "status": status}), flush=True)
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Request-ID", rid)
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
    print(f"olist-shop-stub ready on {PORT}", flush=True)
    server.serve_forever()
