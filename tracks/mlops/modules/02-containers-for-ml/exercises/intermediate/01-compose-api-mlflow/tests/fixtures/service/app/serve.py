import json
import os
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import joblib

MODEL_PATH = os.environ.get("MODEL_PATH", "/models/model.joblib")
PORT = int(os.environ.get("PORT", "8000"))
MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "")

BUNDLE = joblib.load(MODEL_PATH)
MODEL = BUNDLE["model"]
FEATURES = BUNDLE["features"]
STATE = {"run_id": None, "calls": 0}


def mlflow_post(path: str, body: dict) -> dict:
    request = urllib.request.Request(
        f"{MLFLOW_URI}/api/2.0/mlflow/{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.load(response)


def ensure_run() -> str:
    if STATE["run_id"] is None:
        try:
            with urllib.request.urlopen(f"{MLFLOW_URI}/api/2.0/mlflow/experiments/get-by-name?experiment_name=eta-serving", timeout=5) as response:
                experiment = json.load(response)["experiment"]["experiment_id"]
        except Exception:
            experiment = mlflow_post("experiments/create", {"name": "eta-serving"})["experiment_id"]
        STATE["run_id"] = mlflow_post("runs/create", {"experiment_id": experiment, "run_name": "api"})["run"]["info"]["run_id"]
    return STATE["run_id"]


def record_call(count: int) -> None:
    STATE["calls"] += count
    run_id = ensure_run()
    mlflow_post("runs/log-metric", {"run_id": run_id, "key": "predictions", "value": STATE["calls"], "timestamp": 0, "step": STATE["calls"]})


class Handler(BaseHTTPRequestHandler):
    def reply(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self.reply(200, {"status": "ok", "features": FEATURES})
        else:
            self.reply(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/predict":
            self.reply(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            rows = json.loads(self.rfile.read(length))["rows"]
            predictions = [float(value) for value in MODEL.predict(rows)]
        except Exception as error:
            self.reply(400, {"error": str(error)})
            return
        payload = {"predictions": predictions}
        if MLFLOW_URI:
            try:
                record_call(len(rows))
                payload["run_id"] = STATE["run_id"]
            except Exception as error:
                self.reply(503, {"error": f"mlflow: {error}"})
                return
        self.reply(200, payload)

    def log_message(self, format: str, *args) -> None:
        sys.stderr.write("%s\n" % (format % args))


if __name__ == "__main__":
    print(f"serving {MODEL_PATH} on :{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
