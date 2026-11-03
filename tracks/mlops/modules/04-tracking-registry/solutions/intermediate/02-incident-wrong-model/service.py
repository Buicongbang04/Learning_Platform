import mlflow
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException

SERVING_ALIAS = "champion"


class ModelService:
    def __init__(self, tracking_uri: str, model_name: str) -> None:
        self.tracking_uri = tracking_uri
        self.model_name = model_name
        self.client = MlflowClient(tracking_uri)
        self.version = None
        self.model = None
        self._load(self._pick())

    def _pick(self) -> int:
        try:
            return int(self.client.get_model_version_by_alias(self.model_name, SERVING_ALIAS).version)
        except MlflowException as error:
            raise LookupError(f"{self.model_name} chưa có version nào mang alias '{SERVING_ALIAS}'") from error

    def _load(self, version: int) -> None:
        mlflow.set_tracking_uri(self.tracking_uri)
        self.model = mlflow.pyfunc.load_model(f"models:/{self.model_name}/{version}")
        self.version = version
        print(f"loaded {self.model_name} v{version} (alias {SERVING_ALIAS})")

    def refresh(self) -> bool:
        target = self._pick()
        if target == self.version:
            return False
        self._load(target)
        return True

    def predict(self, rows) -> dict:
        return {"model_version": self.version, "predictions": [float(x) for x in self.model.predict(rows)]}
