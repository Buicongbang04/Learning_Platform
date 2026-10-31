import json

import pytest

from testkit import Exercise

ex = Exercise(__file__)
MSGS = [{"role": "user", "content": "Xin chào"}]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("ollama_rest.ipynb")


# ---------- chat_payload ----------


def test_payload_minimal(nb):
    assert nb.chat_payload("qwen2.5:3b", MSGS) == {"model": "qwen2.5:3b", "messages": MSGS, "stream": True}
    assert nb.chat_payload("m", MSGS, stream=False)["stream"] is False


def test_payload_options_and_top_level(nb):
    schema = {"type": "object", "properties": {"label": {"type": "string"}}}
    p = nb.chat_payload("m", MSGS, temperature=0, top_p=0.9, top_k=40, num_ctx=8192, num_predict=64, seed=7,
                        keep_alive=0, format=schema)
    assert p["options"] == {"temperature": 0, "top_p": 0.9, "top_k": 40, "num_ctx": 8192, "num_predict": 64,
                            "seed": 7}, "temperature=0 vẫn phải gửi đi (khác None)"
    assert p["keep_alive"] == 0 and p["format"] == schema
    assert "keep_alive" not in p["options"] and "format" not in p["options"]
    q = nb.chat_payload("m", MSGS, num_ctx=2048)
    assert q["options"] == {"num_ctx": 2048} and "keep_alive" not in q and "format" not in q
    json.dumps(p)


# ---------- parse_stream ----------


def chunk(text, done=False, **extra):
    return json.dumps({"model": "m", "message": {"role": "assistant", "content": text}, "done": done, **extra},
                      ensure_ascii=False)


FINAL = {"done_reason": "stop", "total_duration": 4_941_787_756, "load_duration": 297_602_624,
         "prompt_eval_count": 38, "prompt_eval_duration": 529_157_015, "eval_count": 6,
         "eval_duration": 4_036_382_601}


def test_parse_stream_concatenates(nb):
    lines = [chunk("X"), chunk("in"), "", chunk(" chào"), chunk(" bạn!"), chunk("", done=True, **FINAL)]
    text, final = nb.parse_stream(lines)
    assert text == "Xin chào bạn!"
    assert final["done"] is True and final["eval_count"] == 6


def test_parse_stream_bytes_and_stops_at_done(nb):
    lines = [chunk("a").encode(), b"\n", chunk("b", done=True, eval_count=1).encode(), chunk("thừa").encode()]
    text, final = nb.parse_stream(iter(lines))
    assert text == "ab" and final["eval_count"] == 1


def test_parse_stream_errors(nb):
    with pytest.raises(RuntimeError, match="not found"):
        nb.parse_stream([chunk("a"), json.dumps({"error": 'model "x" not found, try pulling it first'})])
    with pytest.raises(RuntimeError):
        nb.parse_stream([chunk("a"), chunk("b")])


# ---------- speed_stats ----------


def test_speed_stats(nb):
    s = nb.speed_stats({"done": True, **FINAL})
    assert set(s) == {"load_s", "prompt_tokens", "prompt_tps", "gen_tokens", "gen_tps", "total_s"}
    assert s["load_s"] == pytest.approx(0.297602624)
    assert s["prompt_tokens"] == 38 and s["gen_tokens"] == 6
    assert s["prompt_tps"] == pytest.approx(38 / 0.529157015)
    assert s["gen_tps"] == pytest.approx(6 / 4.036382601)
    assert s["total_s"] == pytest.approx(4.941787756)


def test_speed_stats_missing_fields(nb):
    s = nb.speed_stats({"done": True, "eval_count": 10, "eval_duration": 500_000_000, "total_duration": 600_000_000})
    assert s["prompt_tokens"] == 0 and s["prompt_tps"] == 0.0 and s["load_s"] == 0.0
    assert s["gen_tps"] == pytest.approx(20.0)


# ---------- model_facts ----------


def show_json(arch, **info):
    return {"details": {"quantization_level": "Q4_K_M", "parameter_size": "3.1B"},
            "model_info": {"general.architecture": arch, **info}}


def test_model_facts(nb):
    show = show_json("qwen2", **{"general.parameter_count": 3_085_938_688, "qwen2.context_length": 32768,
                                 "general.license": "other", "llama.context_length": 1})
    assert nb.model_facts(show) == {"architecture": "qwen2", "parameter_count": 3_085_938_688,
                                    "context_length": 32768, "quantization": "Q4_K_M", "license": "other"}
    gemma = show_json("gemma3", **{"general.parameter_count": 1, "gemma3.context_length": 131072})
    facts = nb.model_facts(gemma)
    assert facts["context_length"] == 131072, "khoá context theo kiến trúc: <architecture>.context_length"
    assert facts["license"] is None


# ---------- render_modelfile ----------


def test_render_modelfile(nb):
    mf = nb.render_modelfile("qwen2.5:3b", "Bạn là trợ lý.", {"temperature": 0.2, "num_ctx": 4096,
                                                               "stop": ["<|im_end|>", "<|endoftext|>"]})
    assert mf == (
        "FROM qwen2.5:3b\n"
        "PARAMETER temperature 0.2\n"
        "PARAMETER num_ctx 4096\n"
        "PARAMETER stop <|im_end|>\n"
        "PARAMETER stop <|endoftext|>\n"
        'SYSTEM """Bạn là trợ lý."""\n'
    )
    assert nb.render_modelfile("llama3.2:1b") == "FROM llama3.2:1b\n"
