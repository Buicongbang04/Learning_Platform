"""Test cho llmkit: HTTP giả bằng httpx.MockTransport, không cần mạng/GPU/LLM thật."""

import json

import httpx
import numpy as np
import pytest

import llmkit
from llmkit import FakeLLM, LLMError, OllamaClient, OpenAICompatClient

MSG = [{"role": "user", "content": "chào"}]


def _transport(handler):
    return httpx.MockTransport(handler)


def test_import_does_not_connect(monkeypatch):
    def boom(self, *a, **k):
        raise AssertionError("không được kết nối khi import")

    monkeypatch.setattr(httpx.Client, "send", boom)
    assert llmkit.get_client() is not None  # tạo client lazily, chưa gửi request


def test_ollama_chat_payload_and_reply():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": "xin chào"}})

    client = OllamaClient(host="http://x:11434", transport=_transport(handler))
    assert client.chat(MSG) == "xin chào"
    assert seen["path"] == "/api/chat"
    assert seen["body"]["model"] == "qwen2.5:3b"
    assert seen["body"]["stream"] is False
    assert seen["body"]["options"]["temperature"] == 0.0
    assert seen["body"]["messages"] == MSG
    assert "format" not in seen["body"]


def test_ollama_json_schema_sent_as_format():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": "{}"}})

    schema = {"type": "object", "properties": {"a": {"type": "string"}}}
    OllamaClient(transport=_transport(handler)).chat(MSG, json_schema=schema)
    assert seen["body"]["format"] == schema


def test_ollama_embed_shape():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"embeddings": [[1, 2, 3], [4, 5, 6]]})

    out = OllamaClient(transport=_transport(handler)).embed(["a", "b"])
    assert seen["path"] == "/api/embed"
    assert seen["body"] == {"model": "bge-m3", "input": ["a", "b"]}
    assert out.dtype == np.float32 and out.shape == (2, 3)


def test_openai_compat_bearer_and_parse():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["Authorization"]
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        if request.url.path.endswith("/embeddings"):
            return httpx.Response(200, json={"data": [{"embedding": [1, 2]}, {"embedding": [3, 4]}]})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    client = OpenAICompatClient(base_url="http://h/v1", api_key="k", transport=_transport(handler))
    assert client.chat(MSG) == "ok"
    assert seen["auth"] == "Bearer k"
    assert seen["path"] == "/v1/chat/completions"
    assert "response_format" not in seen["body"]
    schema = {"type": "object"}
    client.chat(MSG, json_schema=schema)
    assert seen["body"]["response_format"]["type"] == "json_schema"
    assert seen["body"]["response_format"]["json_schema"]["schema"] == schema
    emb = client.embed(["a", "b"])
    assert seen["path"] == "/v1/embeddings"
    assert emb.dtype == np.float32 and emb.shape == (2, 2)


def test_connection_refused_message():
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(LLMError) as err:
        OllamaClient(transport=_transport(handler)).chat(MSG)
    assert "ollama serve" in str(err.value)


def test_model_not_found_message():
    def handler(request):
        return httpx.Response(404, json={"error": 'model "x" not found, try pulling it first'})

    with pytest.raises(LLMError) as err:
        OllamaClient(transport=_transport(handler)).chat(MSG, model="x")
    assert "ollama pull x" in str(err.value)


def test_fake_llm_scripted_and_records_calls():
    fake = FakeLLM(["một", "hai"])
    assert fake.chat(MSG) == "một"
    assert fake.chat(MSG) == "hai"
    with pytest.raises(AssertionError):
        fake.chat(MSG)
    assert fake.calls == [MSG, MSG, MSG]
    assert FakeLLM(lambda m: m[-1]["content"].upper()).chat(MSG) == "CHÀO"


def _cos(a, b):
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def test_fake_embed_deterministic_and_similar():
    a, b, c = FakeLLM().embed(["luật đất đai", "đất đai luật", "bóng đá"])
    again = FakeLLM().embed(["luật đất đai"])[0]
    assert a.dtype == np.float32 and a.shape == (64,)
    assert np.array_equal(a, again)
    assert _cos(a, b) > _cos(a, c)


def test_use_swaps_global_client():
    fake = FakeLLM(["giả"])
    before = llmkit.get_client()
    with llmkit.use(fake):
        assert llmkit.get_client() is fake
        assert llmkit.chat(MSG) == "giả"
        assert llmkit.embed(["a"]).shape == (1, 64)
    assert llmkit.get_client() is before


def test_openai_compat_no_auth_header_when_key_empty():
    seen = []

    def handler(request):
        seen.append(request.headers.get("Authorization"))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    OpenAICompatClient(base_url="http://h/v1", api_key="", transport=_transport(handler)).chat(MSG)
    OpenAICompatClient(base_url="http://h/v1", api_key="k", transport=_transport(handler)).chat(MSG)
    assert seen == [None, "Bearer k"]


def test_ollama_embed_batch_500_retries_item_by_item():
    calls = []

    def handler(request):
        inputs = json.loads(request.content)["input"]
        calls.append(inputs)
        if "nan" in inputs:
            return httpx.Response(500, json={"error": "failed to encode response: json: unsupported value: NaN"})
        return httpx.Response(200, json={"embeddings": [[float(len(t)), 1.0] for t in inputs]})

    client = OllamaClient(transport=_transport(handler))
    out = client.embed(["a", "bb", "ccc"])
    assert out.shape == (3, 2) and out.dtype == np.float32
    assert len(calls) == 1  # lô tốt: một request

    calls.clear()
    with pytest.raises(LLMError, match="thứ 1"):
        client.embed(["a", "nan", "ccc"])
    assert calls == [["a", "nan", "ccc"], ["a"], ["nan"]]


def test_ollama_embed_batch_500_recovers_when_items_succeed():
    calls = []

    def handler(request):
        inputs = json.loads(request.content)["input"]
        calls.append(inputs)
        if len(inputs) > 1:
            return httpx.Response(500, json={"error": "NaN"})
        return httpx.Response(200, json={"embeddings": [[float(len(inputs[0])), 0.0]]})

    out = OllamaClient(transport=_transport(handler)).embed(["a", "bb"])
    np.testing.assert_allclose(out, [[1.0, 0.0], [2.0, 0.0]])
    assert len(calls) == 3


def test_ollama_embed_4xx_not_retried():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(404, json={"error": 'model "bge-m3" not found, try pulling it first'})

    with pytest.raises(LLMError, match="ollama pull bge-m3"):
        OllamaClient(transport=_transport(handler)).embed(["a", "b"])
    assert len(calls) == 1
