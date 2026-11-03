import io
import json
import logging
import re
import sys
from datetime import datetime, timezone

STANDARD = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {"message", "asctime", "taskName"}
SECRET = re.compile(r"password|token|secret|key", re.IGNORECASE)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in vars(record).items():
            if key not in STANDARD:
                payload[key] = "***" if SECRET.search(key) else value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO", stream: io.TextIOBase | None = None, name: str = "eta") -> logging.Logger:
    logger = logging.getLogger(name)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(level.upper())
    logger.propagate = False
    return logger
