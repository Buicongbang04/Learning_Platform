class ShadowRunner:
    def __init__(self, primary, shadow, log):
        self.primary = primary
        self.shadow = shadow
        self.log = log

    def predict(self, request_id: str, rows: list[list[float]]) -> dict:
        return self.shadow.predict(rows)

    def drain(self, timeout: float = 5.0) -> None:
        pass
