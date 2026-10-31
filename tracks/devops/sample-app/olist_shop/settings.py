import os
from dataclasses import dataclass, field


def _env(name: str, default: str):
    return field(default_factory=lambda: os.environ.get(name, default))


@dataclass(frozen=True)
class Settings:
    database_url: str = _env("DATABASE_URL", "sqlite:///./olist_shop.db")
    redis_url: str = _env("REDIS_URL", "redis://localhost:26379/0")
    log_level: str = _env("LOG_LEVEL", "INFO")
    app_version: str = _env("APP_VERSION", "dev")
    worker_metrics_port: int = field(
        default_factory=lambda: int(os.environ.get("WORKER_METRICS_PORT", "9101")))
