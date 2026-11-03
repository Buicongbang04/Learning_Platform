import io
import json
import os
import signal
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import joblib
import numpy as np

MODEL_PATH = os.environ.get("MODEL_PATH", "/models/eta-v1.joblib")
PORT = int(os.environ.get("PORT", "8080"))
FETCH_SECONDS = float(os.environ.get("MODEL_FETCH_SECONDS", "0"))
signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))


def fetch(path: str) -> dict:
    started = time.monotonic()
    print(f"loading model from {path}", flush=True)
    time.sleep(FETCH_SECONDS)
    bundle = joblib.load(io.BytesIO(Path(path).read_bytes()))
    reference = bundle.pop("reference")
    bundle["baseline"] = {"mean": reference.mean(axis=0).round(4).tolist(), "rows": int(len(reference))}
    print(f"model {bundle['version']} ready in {time.monotonic() - started:.1f}s", flush=True)
    return bundle


BUNDLE = fetch(MODEL_PATH)
NAME = os.environ.get("MODEL_NAME", "eta")


class Handler(BaseHTTPRequestHandler):
    def reply(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/healthz", "/readyz", f"/v1/models/{NAME}"):
            self.reply(200, {"name": NAME, "ready": True, "model_version": BUNDLE["version"]})
        else:
            self.reply(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path not in ("/predict", f"/v1/models/{NAME}:predict"):
            self.reply(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length))
            rows = body.get("rows", body.get("instances"))
            predictions = [round(float(v), 4) for v in BUNDLE["model"].predict(np.asarray(rows, dtype=float))]
        except Exception as error:
            self.reply(400, {"error": str(error)})
            return
        self.reply(200, {"predictions": predictions, "model_version": BUNDLE["version"], "pod": os.environ.get("HOSTNAME", "")})

    def log_message(self, format: str, *args) -> None:
        pass


if __name__ == "__main__":
    print(f"serving {BUNDLE['version']} on :{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
