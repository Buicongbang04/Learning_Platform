import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from quillo import __version__

PRODUCT_DIR = Path(__file__).resolve().parents[2]
MIN_TOKEN_LENGTH = 16
MODULE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")
OIDC_REQUIRED = ("QUILLO_OIDC_ISSUER", "QUILLO_OIDC_CLIENT_ID", "QUILLO_OIDC_CLIENT_SECRET_FILE")


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    database_url: str
    llm_url: str
    embed_url: str
    admin_token: str = field(repr=False)
    version: str = __version__
    migrations_dir: Path = PRODUCT_DIR / "migrations"
    max_upload_mb: int = 20
    http_timeout_s: float = 300.0
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = field(default="", repr=False)
    oidc_groups_claim: str = "groups"
    oidc_ca_file: str = ""
    acl: str = ""
    extensions: tuple[str, ...] = ()
    extensions_path: str = ""

    @property
    def oidc_enabled(self) -> bool:
        return bool(self.oidc_issuer)

    @classmethod
    def from_env(cls, env=os.environ) -> "Settings":
        missing = [name for name in ("QUILLO_DATABASE_URL", "QUILLO_ADMIN_TOKEN") if not env.get(name)]
        if missing:
            raise ConfigError(f"Thiếu biến môi trường: {', '.join(missing)}")
        token = env["QUILLO_ADMIN_TOKEN"]
        if len(token) < MIN_TOKEN_LENGTH:
            raise ConfigError(f"QUILLO_ADMIN_TOKEN phải dài ít nhất {MIN_TOKEN_LENGTH} ký tự")
        extensions = tuple(name.strip() for name in env.get("QUILLO_EXTENSIONS", "").split(",") if name.strip())
        bad = [name for name in extensions if not MODULE_NAME.match(name)]
        if bad:
            raise ConfigError(f"QUILLO_EXTENSIONS chỉ nhận tên module Python dạng pkg.mod, không nhận: {', '.join(bad)}")
        return cls(
            **_oidc_from_env(env),
            acl=env.get("QUILLO_ACL", ""),
            extensions=extensions,
            extensions_path=env.get("QUILLO_EXTENSIONS_PATH", ""),
            database_url=env["QUILLO_DATABASE_URL"],
            llm_url=env.get("QUILLO_LLM_URL", "http://llm:8080"),
            embed_url=env.get("QUILLO_EMBED_URL", "http://embed:8080"),
            admin_token=token,
            version=env.get("QUILLO_VERSION", __version__),
            migrations_dir=Path(env.get("QUILLO_MIGRATIONS_DIR", PRODUCT_DIR / "migrations")),
            max_upload_mb=int(env.get("QUILLO_MAX_UPLOAD_MB", "20")),
            http_timeout_s=float(env.get("QUILLO_HTTP_TIMEOUT_S", "300")),
        )


def _oidc_from_env(env) -> dict:
    """OIDC bật khi đặt QUILLO_OIDC_ISSUER; client secret chỉ đọc từ tệp (QUILLO_OIDC_CLIENT_SECRET_FILE), không từ env."""
    if not any(env.get(name) for name in OIDC_REQUIRED):
        return {}
    missing = [name for name in OIDC_REQUIRED if not env.get(name)]
    if missing:
        raise ConfigError(f"Bật OIDC cần đủ {', '.join(OIDC_REQUIRED)}; thiếu: {', '.join(missing)}")
    path = env["QUILLO_OIDC_CLIENT_SECRET_FILE"]
    try:
        secret = Path(path).read_text().strip()
    except OSError as error:
        raise ConfigError(f"QUILLO_OIDC_CLIENT_SECRET_FILE: không đọc được {path} ({error.strerror})") from error
    if not secret:
        raise ConfigError(f"QUILLO_OIDC_CLIENT_SECRET_FILE: tệp {path} rỗng")
    ca_file = env.get("QUILLO_OIDC_CA_FILE", "")
    if ca_file and not Path(ca_file).is_file():
        raise ConfigError(f"QUILLO_OIDC_CA_FILE: không có tệp {ca_file}")
    return {"oidc_issuer": env["QUILLO_OIDC_ISSUER"].rstrip("/"), "oidc_client_id": env["QUILLO_OIDC_CLIENT_ID"],
            "oidc_client_secret": secret, "oidc_groups_claim": env.get("QUILLO_OIDC_GROUPS_CLAIM") or "groups",
            "oidc_ca_file": ca_file}


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
