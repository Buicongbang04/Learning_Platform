import mlflow
from mlflow import MlflowClient


class ModelService:
    def __init__(self, tracking_uri: str, model_name: str) -> None:
        self.tracking_uri = tracking_uri
        self.model_name = model_name
        self.client = MlflowClient(tracking_uri)
        self.version = None
        self.model = None
        self._load(self._pick())

    def _pick(self) -> int:
        versions = self.client.search_model_versions(f"name = '{self.model_name}'")
        if not versions:
            raise LookupError(f"{self.model_name} chưa có version nào")
        return max(int(v.version) for v in versions)

    def _load(self, version: int) -> None:
        mlflow.set_tracking_uri(self.tracking_uri)
        self.model = mlflow.pyfunc.load_model(f"models:/{self.model_name}/{version}")
        self.version = version
        print(f"loaded {self.model_name} v{version}")

    def refresh(self) -> bool:
        target = self._pick()
        if target == self.version:
            return False
        self._load(target)
        return True

    def predict(self, rows) -> dict:
        return {"model_version": self.version, "predictions": [float(x) for x in self.model.predict(rows)]}
