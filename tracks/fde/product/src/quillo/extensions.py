"""Extension của khách: `QUILLO_EXTENSIONS="acme.report,acme.audit"` nạp các module đó từ thư mục
`QUILLO_EXTENSIONS_PATH` (chỉ từ thư mục này) và gọi `register(app, ctx)` của từng module lúc API khởi động.

Một extension lỗi (không import được, thiếu `register`, `register` ném lỗi) làm API không lên, log nêu tên module:
thà không chạy còn hơn chạy thiếu tính năng mà không ai biết."""

import importlib
import importlib.machinery
import importlib.util
import logging
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import ChoiceLoader, Environment, FileSystemLoader, select_autoescape

from quillo.auth import User
from quillo.config import Settings

log = logging.getLogger("quillo.extensions")
TEMPLATES = Path(__file__).resolve().parent / "templates"
RESERVED = {"quillo", *sys.stdlib_module_names}
_loaded: set[str] = set()


class ExtensionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExtensionContext:
    """Những gì một extension được dùng.

    - `ask(question, top_k, user)`: hỏi đáp như `/api/ask`, áp ACL của `user`.
    - `db_query(sql, params)`: SELECT trong transaction chỉ đọc; trả list dict. Không áp ACL: extension tự chịu trách
      nhiệm không lộ tài liệu cho người không được xem.
    - `templates`: Jinja tìm trong `<thư mục module>/templates` trước, rồi tới template của quillo.
    - `require_user`: dependency FastAPI trả `User` (401 khi chưa đăng nhập), dùng như `Depends(ctx.require_user)`.
    """

    settings: Settings
    ask: Callable[[str, int, User], dict]
    db_query: Callable[[str, Sequence], list[dict]]
    templates: Jinja2Templates
    require_user: Callable


def _import(name: str, root: Path):
    top = name.split(".")[0]
    if top in RESERVED:
        raise ImportError(f"tên {top!r} trùng module của Python hoặc quillo")
    spec = importlib.machinery.PathFinder.find_spec(top, [str(root)])
    if spec is None:
        raise ModuleNotFoundError(f"không có {top!r} trong {root}")
    current = sys.modules.get(top)
    if current is not None and getattr(current.__spec__, "origin", None) != spec.origin:
        if top not in _loaded:
            raise ImportError(f"tên {top!r} trùng một module đã nạp từ {current.__spec__.origin}")
        for key in [key for key in sys.modules if key == top or key.startswith(top + ".")]:
            del sys.modules[key]
    if top not in sys.modules:
        module = importlib.util.module_from_spec(spec)
        sys.modules[top] = module
        _loaded.add(top)
        try:
            spec.loader.exec_module(module)
        except BaseException:
            del sys.modules[top]
            raise
    return importlib.import_module(name)


def _templates(module) -> Jinja2Templates:
    folder = Path(module.__file__).resolve().parent / "templates"
    env = Environment(loader=ChoiceLoader([FileSystemLoader(folder), FileSystemLoader(TEMPLATES)]),
                      autoescape=select_autoescape(default=True))
    return Jinja2Templates(env=env)


def load(app, settings: Settings, context: Callable[[Jinja2Templates], ExtensionContext]) -> list[str]:
    """Nạp mọi extension trong `settings.extensions`; `context(templates)` dựng ExtensionContext cho từng module."""
    if settings.extensions and not settings.extensions_path:
        raise ExtensionError("QUILLO_EXTENSIONS được đặt nhưng thiếu QUILLO_EXTENSIONS_PATH")
    root = Path(settings.extensions_path).resolve()
    for name in settings.extensions:
        try:
            module = _import(name, root)
            register = getattr(module, "register", None)
            if not callable(register):
                raise TypeError(f"module {name} không có hàm register(app, ctx)")
            register(app, context(_templates(module)))
        except Exception as error:
            log.error(f"không nạp được extension {name}", extra={"fields": {"extension": name, "error": repr(error)}})
            raise ExtensionError(f"Không nạp được extension {name}: {error!r}") from error
        log.info(f"đã nạp extension {name}", extra={"fields": {"extension": name}})
    return list(settings.extensions)
