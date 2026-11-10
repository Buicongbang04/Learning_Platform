"""beacon: dịch vụ mẫu của bài. GET /healthz trả 503 khi đang kiểm model, 200 khi sẵn sàng."""

import hashlib
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HOME = Path(__file__).resolve().parent.parent
VERSION = (HOME / "app" / "VERSION").read_text().strip()
WEIGHTS = HOME / "models" / "weights.bin"
STATE = {"weights_sha256": None}


def digest() -> None:
    sha = hashlib.sha256()
    with open(WEIGHTS, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    STATE["weights_sha256"] = sha.hexdigest()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/healthz":
            self.send_error(404)
            return
        ready = STATE["weights_sha256"] is not None
        body = json.dumps({
            "status": "ok" if ready else "loading",
            "version": VERSION,
            "greeting": os.environ.get("BEACON_GREETING", ""),
            "weights_sha256": STATE["weights_sha256"],
        }).encode()
        self.send_response(200 if ready else 503)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:
        pass


def main() -> None:
    threading.Thread(target=digest, daemon=True).start()
    port = int(os.environ.get("BEACON_PORT", "8088"))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
