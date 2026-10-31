import json

import pytest

from testkit import Exercise

ex = Exercise(__file__)
GIB = 1024**3

# config.json thật tải từ Hugging Face (chỉ tệp cấu hình, không có trọng số).
NAMES = ["qwen2.5-0.5b-instruct", "qwen2.5-3b-instruct", "qwen2.5-7b-instruct", "phi-3-mini-4k-instruct",
         "mistral-7b-instruct-v0.3"]
# Số tham số thật: tổng numel của checkpoint (0.5B) hoặc general.parameter_count trong GGUF của Ollama (3B, 7B),
# số công bố trên model card (Phi-3 mini 3.8B, Mistral 7B v0.3).
PARAMS = {
    "qwen2.5-0.5b-instruct": 494_032_768,
    "qwen2.5-3b-instruct": 3_085_938_688,
    "qwen2.5-7b-instruct": 7_615_616_512,
    "phi-3-mini-4k-instruct": 3_821_079_552,
    "mistral-7b-instruct-v0.3": 7_248_023_552,
}


@pytest.fixture(scope="module")
def sz():
    return ex.module("sizing.py")


@pytest.fixture(scope="module")
def cfg():
    return {n: json.loads((ex.fixtures / f"{n}.json").read_text()) for n in NAMES}


# Cấu hình tí hon tính tay: head_dim khai báo riêng (6 != 8 // 2), attention_bias True dù model_type khác qwen2,
# thiếu num_key_value_heads (= số head), thiếu tie_word_embeddings (= False).
TINY = {"model_type": "llama", "vocab_size": 10, "hidden_size": 8, "num_hidden_layers": 2,
        "num_attention_heads": 2, "head_dim": 6, "intermediate_size": 16, "attention_bias": True,
        "max_position_embeddings": 64}


def test_head_dim(sz, cfg):
    assert sz.head_dim(cfg["qwen2.5-0.5b-instruct"]) == 64
    assert sz.head_dim(cfg["phi-3-mini-4k-instruct"]) == 96
    assert sz.head_dim(TINY) == 6
    assert sz.head_dim({**TINY, "head_dim": None}) == 4


@pytest.mark.parametrize("name", NAMES)
def test_count_params_matches_real_models(sz, cfg, name):
    assert sz.count_params(cfg[name]) == PARAMS[name]


def test_count_params_tiny_by_hand(sz):
    # q 8*12+12, k và v 2*(8*12+12), o 12*8, MLP 3*8*16, 2 norm 2*8 => 820 mỗi tầng
    # 2 tầng 1640, embedding + lm_head 2*10*8 = 160, norm cuối 8
    assert sz.count_params(TINY) == 1808
    assert sz.count_params({**TINY, "attention_bias": False}) == 1808 - 2 * (12 + 2 * 12)
    assert sz.count_params({**TINY, "tie_word_embeddings": True}) == 1808 - 80
    assert sz.count_params({**TINY, "num_key_value_heads": 1}) == 1808 - 2 * 2 * (8 * 6 + 6)


def test_qwen2_bias_only_when_flag_missing(sz, cfg):
    c = dict(cfg["qwen2.5-0.5b-instruct"])
    assert "attention_bias" not in c
    no_bias = sz.count_params({**c, "attention_bias": False})
    assert PARAMS["qwen2.5-0.5b-instruct"] - no_bias == 24 * (14 * 64 + 2 * 2 * 64)


def test_weight_bytes_matches_checkpoint(sz, cfg):
    # model.safetensors bf16 của Qwen2.5-0.5B-Instruct: 988 097 824 byte (gồm vài chục KB header JSON)
    w = sz.weight_bytes(cfg["qwen2.5-0.5b-instruct"], "bf16")
    assert w == 2 * PARAMS["qwen2.5-0.5b-instruct"]
    assert 0 < 988_097_824 - w < 100_000
    assert sz.weight_bytes(cfg["qwen2.5-7b-instruct"], "int4") == PARAMS["qwen2.5-7b-instruct"] / 2


def test_kv_cache_bytes(sz, cfg):
    assert sz.kv_cache_bytes(cfg["qwen2.5-0.5b-instruct"], 32768) == 384 * 1024**2
    assert sz.kv_cache_bytes(cfg["phi-3-mini-4k-instruct"], 4096) == 1.5 * GIB, "Phi-3 mini dùng MHA: 32 KV head"
    assert sz.kv_cache_bytes(cfg["mistral-7b-instruct-v0.3"], 32768) == 4 * GIB
    q3 = cfg["qwen2.5-3b-instruct"]
    assert sz.kv_cache_bytes(q3, 1000, batch=4) == 4 * sz.kv_cache_bytes(q3, 1000)
    assert sz.kv_cache_bytes(q3, 1000, kv_dtype="q8_0") == pytest.approx(sz.kv_cache_bytes(q3, 1000) * 8.5 / 16)
    assert sz.kv_cache_bytes(TINY, 10) == 2 * 2 * 2 * 6 * 10 * 2


def test_estimate_memory(sz, cfg):
    c = cfg["qwen2.5-3b-instruct"]
    m = sz.estimate_memory(c, "q4_k_m", 4096)
    assert set(m) == {"weights", "kv_cache", "overhead", "total"}
    assert m["weights"] == pytest.approx(PARAMS["qwen2.5-3b-instruct"] * 5 / 8)
    assert m["kv_cache"] == 2 * 36 * 2 * 128 * 4096 * 2
    assert m["overhead"] == pytest.approx(0.2 * (m["weights"] + m["kv_cache"]))
    assert m["total"] == pytest.approx(m["weights"] + m["kv_cache"] + m["overhead"])
    m0 = sz.estimate_memory(c, "fp16", 8192, batch=2, kv_dtype="fp32", overhead=0.0)
    assert m0["overhead"] == 0 and m0["kv_cache"] == 2 * 36 * 2 * 128 * 8192 * 2 * 4


@pytest.mark.parametrize("name, dtype, budget", [
    ("qwen2.5-3b-instruct", "q4_k_m", 3 * GIB),
    ("qwen2.5-0.5b-instruct", "bf16", 1.4 * GIB),
    ("phi-3-mini-4k-instruct", "q4_k_m", 3.5 * GIB),
])
def test_max_context_is_largest_fitting(sz, cfg, name, dtype, budget):
    c = cfg[name]
    n = sz.max_context(c, dtype, budget)
    assert type(n) is int and 0 < n < c["max_position_embeddings"]
    assert sz.estimate_memory(c, dtype, n)["total"] <= budget
    assert sz.estimate_memory(c, dtype, n + 1)["total"] > budget


def test_max_context_bounds(sz, cfg):
    assert sz.max_context(cfg["qwen2.5-7b-instruct"], "q4_k_m", 4 * GIB) == 0, "7B Q4 không vừa GPU 4 GB"
    assert sz.max_context(cfg["qwen2.5-3b-instruct"], "q4_k_m", 12 * GIB) == 32768, "không vượt context của model"
    big = sz.max_context(cfg["qwen2.5-3b-instruct"], "q4_k_m", 3 * GIB, batch=4)
    assert big < sz.max_context(cfg["qwen2.5-3b-instruct"], "q4_k_m", 3 * GIB) / 3
