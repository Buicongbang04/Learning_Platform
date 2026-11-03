"""Server giả nói API kiểu OpenAI như llama.cpp server (`/health`, `/v1/chat/completions`, `/v1/embeddings`).

Chạy trong tiến trình test trên 127.0.0.1, cổng ngẫu nhiên. Embedding là "túi từ" băm vào 768 chiều, nên câu hỏi và
đoạn văn có chung từ thì gần nhau: đủ để kiểm truy hồi mà không cần model thật.
"""

import hashlib
import json
import math
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DIM = 768
WORD = re.compile(r"[a-z0-9]+")


def embed(text: str) -> list[float]:
    vector = [0.0] * DIM
    for word in WORD.findall(text.lower()):
        vector[int(hashlib.sha1(word.encode()).hexdigest(), 16) % DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


class FakeOpenAI:
    def __init__(self, answer: str = "The agreement is governed by the laws of the State of New York [1].",
                 model: str = "fake-llm") -> None:
        self.answer = answer
        self.model = model
        self.chats: list[dict] = []
        self.embedded: list[str] = []
        self._server: ThreadingHTTPServer | None = None

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def __enter__(self) -> "FakeOpenAI":
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:
                pass

            def _reply(self, status: int, body: dict) -> None:
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:
                if self.path == "/health":
                    self._reply(200, {"status": "ok"})
                else:
                    self._reply(404, {"error": "not found"})

            def do_POST(self) -> None:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                if self.path == "/v1/embeddings":
                    inputs = body["input"] if isinstance(body["input"], list) else [body["input"]]
                    fake.embedded.extend(inputs)
                    data = [{"object": "embedding", "index": i, "embedding": embed(t)} for i, t in enumerate(inputs)]
                    self._reply(200, {"object": "list", "data": data, "model": "fake-embed"})
                elif self.path == "/v1/chat/completions":
                    fake.chats.append(body)
                    message = {"role": "assistant", "content": fake.answer}
                    self._reply(200, {"object": "chat.completion", "model": fake.model,
                                      "choices": [{"index": 0, "message": message, "finish_reason": "stop"}]})
                else:
                    self._reply(404, {"error": "not found"})

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc) -> None:
        self._server.shutdown()
        self._server.server_close()
