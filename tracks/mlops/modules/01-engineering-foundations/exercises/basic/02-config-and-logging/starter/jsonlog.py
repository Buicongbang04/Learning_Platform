import io
import logging


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # TODO: một dòng JSON với khoá ts (ISO 8601 UTC), level, logger, msg, cộng mọi trường truyền qua `extra=`.
        # Trường có tên chứa password, token, secret hoặc key (không phân biệt hoa thường) đổi thành "***".
        # Có exc_info thì thêm khoá exc là traceback dạng chuỗi.
        raise NotImplementedError


def configure_logging(level: str = "INFO", stream: io.TextIOBase | None = None, name: str = "eta") -> logging.Logger:
    # TODO: trả logger `name` với đúng một handler JsonFormatter ghi vào stream (mặc định stderr).
    # Gọi lại nhiều lần không được nhân đôi handler. Không đẩy log lên root logger (propagate=False).
    raise NotImplementedError
