import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from quillo import __version__

PRODUCT_DIR = Path(__file__).resolve().parents[2]
MIN_TOKEN_LENGTH = 16


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    database_url: str
    llm_url: str
    embed_url: str
    admin_token: str
    version: str = __version__
    migrations_dir: Path = PRODUCT_DIR / "migrations"
    max_upload_mb: int = 20
    http_timeout_s: float = 300.0

    @classmethod
    def from_env(cls, env=os.environ) -> "Settings":
        missing = [name for name in ("QUILLO_DATABASE_URL", "QUILLO_ADMIN_TOKEN") if not env.get(name)]
        if missing:
            raise ConfigError(f"Thiếu biến môi trường: {', '.join(missing)}")
        token = env["QUILLO_ADMIN_TOKEN"]
        if len(token) < MIN_TOKEN_LENGTH:
            raise ConfigError(f"QUILLO_ADMIN_TOKEN phải dài ít nhất {MIN_TOKEN_LENGTH} ký tự")
        return cls(
            database_url=env["QUILLO_DATABASE_URL"],
            llm_url=env.get("QUILLO_LLM_URL", "http://llm:8080"),
            embed_url=env.get("QUILLO_EMBED_URL", "http://embed:8080"),
            admin_token=token,
            version=env.get("QUILLO_VERSION", __version__),
            migrations_dir=Path(env.get("QUILLO_MIGRATIONS_DIR", PRODUCT_DIR / "migrations")),
            max_upload_mb=int(env.get("QUILLO_MAX_UPLOAD_MB", "20")),
            http_timeout_s=float(env.get("QUILLO_HTTP_TIMEOUT_S", "300")),
        )


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {"ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"), "level": record.levelname,
                 "logger": record.name, "msg": record.getMessage()}
        entry.update(getattr(record, "fields", {}))
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def setup_logging(level: str | None = None) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level or os.environ.get("QUILLO_LOG_LEVEL", "INFO"))
    logging.getLogger("httpx").setLevel(logging.WARNING)
