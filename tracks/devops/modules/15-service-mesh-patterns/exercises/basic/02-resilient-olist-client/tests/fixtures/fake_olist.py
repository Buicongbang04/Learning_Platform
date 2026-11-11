import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeOlist:
    """Server HTTP giả của Olist Shop trên 127.0.0.1, trả lời theo kịch bản cho từng path.

    Mỗi path có một danh sách hành động, dùng lần lượt cho từng request; hết danh sách thì lặp lại hành động cuối.
    Hành động: số (mã HTTP), tuple (mã, {header}), "slow" (ngủ 0,6 giây rồi trả 200), "reset" (đóng kết nối không trả lời).
    """

    def __init__(self, script: dict):
        self.script = {path: list(actions) for path, actions in script.items()}
        self.requests = []
        self.lock = threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            disable_nagle_algorithm = True

            def handle_any(self, method):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length).decode() if length else ""
                with owner.lock:
                    owner.requests.append({"method": method, "path": self.path, "body": body,
                                           "idempotency_key": self.headers.get("Idempotency-Key")})
                    actions = owner.script.get(self.path, [404])
                    action = actions.pop(0) if len(actions) > 1 else actions[0]
                if action == "reset":
                    self.close_connection = True
                    self.connection.shutdown(2)
                    return
                if action == "slow":
                    time.sleep(0.6)
                    action = 200
                status, headers = action if isinstance(action, tuple) else (action, {})
                payload = json.dumps({"path": self.path, "status": status}).encode()
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):
                self.handle_any("GET")

            def do_POST(self):
                self.handle_any("POST")

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def count(self, path: str) -> int:
        with self.lock:
            return sum(1 for r in self.requests if r["path"] == path)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
