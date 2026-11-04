import httpx


class ModelServer:
    """Client của một server nói API kiểu OpenAI (llama.cpp `llama-server`): chat, embeddings và `/health`."""

    def __init__(self, base_url: str, timeout: float = 300.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(base_url=self.base_url, timeout=timeout)

    def close(self) -> None:
        self._http.close()

    def healthy(self, timeout: float = 3.0) -> bool:
        try:
            return self._http.get("/health", timeout=timeout).status_code == 200
        except httpx.HTTPError:
            return False

    def chat(self, messages: list[dict], max_tokens: int = 400) -> tuple[str, str]:
        response = self._http.post("/v1/chat/completions",
                                   json={"messages": messages, "max_tokens": max_tokens, "temperature": 0})
        response.raise_for_status()
        body = response.json()
        return body["choices"][0]["message"]["content"].strip(), body.get("model", "")

    def embed(self, texts: list[str], batch: int = 16) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), batch):
            response = self._http.post("/v1/embeddings", json={"input": texts[start:start + batch]})
            response.raise_for_status()
            data = sorted(response.json()["data"], key=lambda item: item["index"])
            vectors.extend(item["embedding"] for item in data)
        return vectors
