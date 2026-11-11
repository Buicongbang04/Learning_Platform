import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

LOCK = threading.Lock()
STATE = {"delay": 0.4, "limit": 8, "fail": [], "calls": {}, "in_flight": 0, "max_in_flight": 0, "rejected": 0}


def freight(order_id: str) -> int:
    return 900 + sum(order_id.encode()) % 2000


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/stats":
            with LOCK:
                return self.reply(200, {k: STATE[k] for k in ("calls", "max_in_flight", "rejected", "in_flight")})
        if url.path != "/quote":
            return self.reply(404, {"error": "not found"})
        order_id = parse_qs(url.query).get("order_id", [""])[0]
        with LOCK:
            if STATE["in_flight"] >= STATE["limit"]:
                STATE["rejected"] += 1
                return self.reply(429, {"error": "too many concurrent requests"})
            STATE["in_flight"] += 1
            STATE["max_in_flight"] = max(STATE["max_in_flight"], STATE["in_flight"])
            STATE["calls"][order_id] = STATE["calls"].get(order_id, 0) + 1
            delay, failing = STATE["delay"], order_id in STATE["fail"]
        try:
            time.sleep(delay)
            if failing:
                return self.reply(500, {"error": "carrier unavailable"})
            return self.reply(200, {"order_id": order_id, "freight_cents": freight(order_id)})
        finally:
            with LOCK:
                STATE["in_flight"] -= 1

    def do_POST(self):
        if self.path != "/reset":
            return self.reply(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        with LOCK:
            STATE.update({"delay": float(body.get("delay", 0.4)), "limit": int(body.get("limit", 8)),
                          "fail": list(body.get("fail", [])), "calls": {}, "max_in_flight": 0, "rejected": 0})
        return self.reply(200, {"ok": True})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    server.daemon_threads = True
    print("quote service ready", flush=True)
    server.serve_forever()
