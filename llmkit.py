"""Lớp gọi LLM dùng chung cho track AI Engineer: một giao diện, nhiều nơi chạy model.

Mặc định chạy local bằng Ollama (không cần key, không tốn tiền). Cấu hình qua biến môi trường
hoặc `setup/.env` (biến môi trường thật được ưu tiên):

    # 1. Ollama local (mặc định)
    ollama serve; ollama pull qwen2.5:3b; ollama pull bge-m3

    # 2. Ollama trên PC khác trong mạng (máy này chỉ là client)
    OLLAMA_HOST=http://<ip-PC>:11434

    # 3. OmniRoute (hoặc bất kỳ server tương thích OpenAI)
    LLM_PROVIDER=openai_compat
    LLM_BASE_URL=http://localhost:20128/v1
    LLM_API_KEY=<key của bạn>
    LLM_MODEL=<tên model trên router>

    # 4. Gemini qua endpoint tương thích OpenAI
    LLM_PROVIDER=openai_compat
    LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
    LLM_API_KEY=<GEMINI_API_KEY>
    LLM_MODEL=gemini-2.5-flash
    EMBED_MODEL=gemini-embedding-001

Biến khác: `LLM_MODEL` (mặc định qwen2.5:3b), `EMBED_MODEL` (mặc định bge-m3), `LLM_TIMEOUT` (giây, mặc định 120).
Không bao giờ commit key vào git.

Trong code bài tập:

    import llmkit
    llmkit.chat([{"role": "user", "content": "Xin chào"}])
    vectors = llmkit.embed(["luật đất đai", "bóng đá"])    # np.float32, shape (2, dim), chưa chuẩn hoá

Trong test (không mạng, không GPU, không LLM thật):

    from llmkit import FakeLLM
    fake = FakeLLM(["câu trả lời 1", "câu trả lời 2"])      # hoặc FakeLLM(lambda messages: "...")
    with llmkit.use(fake):
        ...                                                  # code gọi llmkit.chat/embed dùng fake
    fake.calls                                               # mọi lời gọi chat, để assert prompt
"""

from __future__ import annotations

import hashlib
import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator, Protocol

import httpx
import numpy as np

from testkit import _load_env_file

Message = dict[str, str]

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:3b"
DEFAULT_EMBED_MODEL = "bge-m3"
DEFAULT_TIMEOUT = 120.0


class LLMError(RuntimeError):
    """Lỗi gọi LLM; thông điệp tiếng Việt kèm lệnh khắc phục."""


class LLMClient(Protocol):
    def chat(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 0.0,
        json_schema: dict | None = None,
    ) -> str: ...

    def embed(self, texts: list[str], *, model: str | None = None) -> np.ndarray: ...


def _timeout() -> float:
    return float(os.environ.get("LLM_TIMEOUT", DEFAULT_TIMEOUT))


class _HTTPClient:
    """Phần chung: POST JSON, đổi lỗi mạng/HTTP thành LLMError."""

    def __init__(self, base_url: str, headers: dict[str, str], timeout: float, transport):
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(headers=headers, timeout=timeout, transport=transport)

    def _hint_connect(self) -> str:
        return f"Không kết nối được tới {self.base_url}."

    def _hint_http(self, status: int, text: str, model: str | None) -> str:
        return f"{self.base_url} trả lỗi HTTP {status}: {text[:300]}"

    def _post(self, path: str, payload: dict, model: str | None) -> dict:
        try:
            response = self._http.post(self.base_url + path, json=payload)
        except httpx.TimeoutException as exc:
            raise LLMError(
                f"Quá thời gian chờ {self.base_url}{path}. Tăng LLM_TIMEOUT (giây) hoặc dùng model nhỏ hơn."
            ) from exc
        except httpx.TransportError as exc:
            raise LLMError(self._hint_connect()) from exc
        if response.status_code >= 400:
            raise LLMError(self._hint_http(response.status_code, response.text, model))
        return response.json()


class OllamaClient(_HTTPClient):
    def __init__(
        self,
        host: str | None = None,
        *,
        model: str | None = None,
        embed_model: str | None = None,
        timeout: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        super().__init__(
            host or os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST),
            {},
            _timeout() if timeout is None else timeout,
            transport,
        )
        self.model = model or os.environ.get("LLM_MODEL", DEFAULT_MODEL)
        self.embed_model = embed_model or os.environ.get("EMBED_MODEL", DEFAULT_EMBED_MODEL)

    def _hint_connect(self) -> str:
        return (
            f"Không kết nối được Ollama tại {self.base_url}. Bật server: `ollama serve` "
            "(hoặc đặt OLLAMA_HOST=http://<ip-PC>:11434 nếu Ollama chạy trên máy khác)."
        )

    def _hint_http(self, status: int, text: str, model: str | None) -> str:
        if status == 404 and "not found" in text:
            match = re.search(r'model "?([^"\s,]+)"? not found', text)
            name = match.group(1) if match else (model or self.model)
            return f"Ollama chưa có model `{name}`. Tải về: `ollama pull {name}`."
        return super()._hint_http(status, text, model)

    def chat(self, messages, *, model=None, temperature=0.0, json_schema=None) -> str:
        used = model or self.model
        payload = {
            "model": used,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_schema is not None:
            payload["format"] = json_schema
        return self._post("/api/chat", payload, used)["message"]["content"]

    def embed(self, texts, *, model=None) -> np.ndarray:
        used = model or self.embed_model
        data = self._post("/api/embed", {"model": used, "input": list(texts)}, used)
        return np.asarray(data["embeddings"], dtype=np.float32)


class OpenAICompatClient(_HTTPClient):
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        *,
        model: str | None = None,
        embed_model: str | None = None,
        timeout: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        url = base_url or os.environ.get("LLM_BASE_URL")
        if not url:
            raise LLMError("Thiếu LLM_BASE_URL. Đặt trong setup/.env, ví dụ: LLM_BASE_URL=http://localhost:20128/v1")
        key = api_key if api_key is not None else os.environ.get("LLM_API_KEY", "")
        super().__init__(
            url,
            {"Authorization": f"Bearer {key}"} if key else {},
            _timeout() if timeout is None else timeout,
            transport,
        )
        self.model = model or os.environ.get("LLM_MODEL", DEFAULT_MODEL)
        self.embed_model = embed_model or os.environ.get("EMBED_MODEL", DEFAULT_EMBED_MODEL)

    def _hint_connect(self) -> str:
        return f"Không kết nối được {self.base_url}. Kiểm tra server đang chạy và LLM_BASE_URL trong setup/.env."

    def _hint_http(self, status: int, text: str, model: str | None) -> str:
        if status in (401, 403):
            return f"{self.base_url} từ chối key (HTTP {status}). Kiểm tra LLM_API_KEY trong setup/.env."
        return super()._hint_http(status, text, model)

    def chat(self, messages, *, model=None, temperature=0.0, json_schema=None) -> str:
        used = model or self.model
        payload = {"model": used, "messages": messages, "temperature": temperature}
        if json_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": json_schema},
            }
        return self._post("/chat/completions", payload, used)["choices"][0]["message"]["content"]

    def embed(self, texts, *, model=None) -> np.ndarray:
        used = model or self.embed_model
        data = self._post("/embeddings", {"model": used, "input": list(texts)}, used)
        return np.asarray([item["embedding"] for item in data["data"]], dtype=np.float32)


_TOKEN = re.compile(r"\w+", re.UNICODE)


class FakeLLM:
    """LLM giả cho test: trả lời theo kịch bản, embed xác định, ghi lại mọi lời gọi chat."""

    def __init__(self, replies: Callable[[list[Message]], str] | list[str] | None = None, dim: int = 64):
        self._replies = replies
        self.dim = dim
        self.calls: list[list[Message]] = []
        self._next = 0

    def chat(self, messages, *, model=None, temperature=0.0, json_schema=None) -> str:
        self.calls.append(messages)
        if callable(self._replies):
            return self._replies(messages)
        replies = self._replies or []
        assert self._next < len(replies), f"FakeLLM hết câu trả lời kịch bản (đã gọi {self._next} lần)"
        reply = replies[self._next]
        self._next += 1
        return reply

    def embed(self, texts, *, model=None) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for token in _TOKEN.findall(text.lower()):
                digest = hashlib.md5(token.encode("utf-8")).digest()
                out[row, int.from_bytes(digest[:4], "big") % self.dim] += 1.0
        return out


_client: LLMClient | None = None


def _make_client() -> LLMClient:
    _load_env_file(Path(__file__).resolve().parent / "setup" / ".env")
    provider = os.environ.get("LLM_PROVIDER", "ollama")
    if provider == "ollama":
        return OllamaClient()
    if provider == "openai_compat":
        return OpenAICompatClient()
    raise LLMError(f"LLM_PROVIDER=`{provider}` không hợp lệ. Dùng `ollama` hoặc `openai_compat`.")


def get_client() -> LLMClient:
    """Client toàn cục, tạo theo env ở lần gọi đầu (không kết nối mạng khi tạo)."""
    global _client
    if _client is None:
        _client = _make_client()
    return _client


@contextmanager
def use(client: LLMClient) -> Iterator[LLMClient]:
    """Đổi client toàn cục tạm thời, ví dụ `with llmkit.use(FakeLLM([...])):`."""
    global _client
    previous = _client
    _client = client
    try:
        yield client
    finally:
        _client = previous


def chat(messages: list[Message], **kwargs) -> str:
    return get_client().chat(messages, **kwargs)


def embed(texts: list[str], **kwargs) -> np.ndarray:
    return get_client().embed(texts, **kwargs)
