import copy
from concurrent.futures import ThreadPoolExecutor, wait


class ShadowRunner:
    def __init__(self, primary, shadow, log):
        self.primary = primary
        self.shadow = shadow
        self.log = log
        self.pool = ThreadPoolExecutor(max_workers=4)
        self.pending = set()

    def predict(self, request_id: str, rows: list[list[float]]) -> dict:
        shadow_rows = copy.deepcopy(rows)
        response = self.primary.predict(rows)
        future = self.pool.submit(self.run_shadow, request_id, shadow_rows, copy.deepcopy(response))
        self.pending.add(future)
        future.add_done_callback(self.pending.discard)
        return response

    def run_shadow(self, request_id: str, rows: list[list[float]], primary: dict) -> None:
        record = {
            "request_id": request_id,
            "primary_version": primary["model_version"],
            "primary": primary["predictions"],
            "shadow_version": None,
            "shadow": None,
            "max_abs_diff": None,
            "error": None,
        }
        try:
            result = self.shadow.predict(rows)
            record["shadow_version"] = result["model_version"]
            record["shadow"] = result["predictions"]
            record["max_abs_diff"] = max(abs(a - b) for a, b in zip(primary["predictions"], result["predictions"]))
        except Exception as error:
            record["error"] = f"{type(error).__name__}: {error}"
        try:
            self.log(record)
        except Exception:
            pass

    def drain(self, timeout: float = 5.0) -> None:
        wait(list(self.pending), timeout=timeout)
