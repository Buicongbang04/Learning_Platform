import json

import pytest

from testkit import Exercise

ex = Exercise(__file__)
GiB = 1024**3
# Số tham số = total_size (byte, bf16) trong model.safetensors.index.json trên Hugging Face / 2 (kiểm 2026-10-30)
PARAMS = {"qwen2.5-3b-instruct": 6_171_877_376 / 2, "qwen2.5-7b-instruct": 15_231_233_024 / 2,
          "qwen2.5-72b-instruct": 145_412_407_296 / 2}


@pytest.fixture(scope="module")
def m():
    return ex.module("memory.py")


def config(name):
    return json.loads((ex.fixtures / f"{name}.json").read_text())


def shape(m, name):
    return m.shape_from_hf_config(config(name), PARAMS[name])


def test_shape_from_qwen_config(m):
    s = shape(m, "qwen2.5-7b-instruct")
    assert (s.n_layers, s.n_kv_heads, s.head_dim) == (28, 4, 128)
    assert s.n_params == PARAMS["qwen2.5-7b-instruct"]


def test_shape_uses_explicit_head_dim(m):
    # Mistral-Nemo: hidden 5120 / 32 head = 160, nhưng head_dim thật trong config là 128
    s = m.shape_from_hf_config(config("mistral-nemo-instruct-2407"), 12.2e9)
    assert (s.n_layers, s.n_kv_heads, s.head_dim) == (40, 8, 128)


def test_shape_without_kv_heads_is_mha(m):
    # config giả kiểu Llama-2-7B: không có num_key_value_heads nghĩa là multi-head attention đầy đủ
    cfg = {"hidden_size": 4096, "num_attention_heads": 32, "num_hidden_layers": 32}
    s = m.shape_from_hf_config(cfg, 6.7e9)
    assert (s.n_kv_heads, s.head_dim) == (32, 128)
    assert m.kv_bytes_per_token(s) == 524_288  # 512 KiB mỗi token


def test_weight_bytes(m):
    # bf16: đúng bằng total_size của safetensors
    assert m.weight_bytes(PARAMS["qwen2.5-7b-instruct"], 16) == pytest.approx(15_231_233_024)
    assert m.weight_bytes(PARAMS["qwen2.5-7b-instruct"], 4.5) == pytest.approx(4_283_784_288)
    with pytest.raises(ValueError):
        m.weight_bytes(1e9, 0)


def test_kv_bytes_per_token_gqa(m):
    # 2 (K, V) * layer * kv_head * head_dim * 2 byte
    assert m.kv_bytes_per_token(shape(m, "qwen2.5-3b-instruct")) == 36_864  # 2*36*2*128*2
    assert m.kv_bytes_per_token(shape(m, "qwen2.5-7b-instruct")) == 57_344  # 2*28*4*128*2
    assert m.kv_bytes_per_token(shape(m, "qwen2.5-72b-instruct")) == 327_680  # 2*80*8*128*2
    nemo = m.shape_from_hf_config(config("mistral-nemo-instruct-2407"), 12.2e9)
    assert m.kv_bytes_per_token(nemo) == 163_840
    # KV cache int8: một nửa
    assert m.kv_bytes_per_token(shape(m, "qwen2.5-7b-instruct"), kv_bits=8) == 28_672


def test_kv_cache_bytes(m):
    s = shape(m, "qwen2.5-7b-instruct")
    assert m.kv_cache_bytes(s, 32_768) == 1_879_048_192  # đúng 1.75 GiB cho một chuỗi 32k
    assert m.kv_cache_bytes(s, 8192, batch=16) == 16 * 8192 * 57_344


def test_max_concurrent_sequences_rtx3060(m):
    s = shape(m, "qwen2.5-7b-instruct")
    # 12 GiB, trọng số 4.5 bit, chừa 1.5 GiB: còn 6 990 504 864 byte cho KV; mỗi chuỗi 8k cần 469 762 048
    assert m.max_concurrent_sequences(12 * GiB, s, 4.5, 8192, reserve_bytes=1.5 * GiB) == 14
    assert m.max_concurrent_sequences(12 * GiB, s, 4.5, 8192, kv_bits=8, reserve_bytes=1.5 * GiB) == 29
    # bf16 không vừa 12 GiB: 0 chứ không âm
    assert m.max_concurrent_sequences(12 * GiB, s, 16, 8192) == 0
    assert isinstance(m.max_concurrent_sequences(12 * GiB, s, 4.5, 8192), int)


def test_max_context_tokens(m):
    s = shape(m, "qwen2.5-7b-instruct")
    assert m.max_context_tokens(12 * GiB, s, 4.5, reserve_bytes=1.5 * GiB) == 121_904
    assert m.max_context_tokens(12 * GiB, s, 4.5, batch=4, reserve_bytes=1.5 * GiB) == 30_476
    assert m.max_context_tokens(12 * GiB, s, 16) == 0
    s3 = shape(m, "qwen2.5-3b-instruct")
    assert m.max_context_tokens(4 * GiB, s3, 5.0, reserve_bytes=0.8 * GiB) == 40_887


def test_72b_needs_big_iron(m):
    s = shape(m, "qwen2.5-72b-instruct")
    # 2 GPU 80 GiB, bf16, chừa 8 GiB: trọng số 135.4 GiB, chỉ còn chỗ cho 1 chuỗi 32k
    assert m.max_concurrent_sequences(160 * GiB, s, 16, 32_768, reserve_bytes=8 * GiB) == 1


def test_rejects_bad_input(m):
    s = shape(m, "qwen2.5-7b-instruct")
    with pytest.raises(ValueError):
        m.max_concurrent_sequences(12 * GiB, s, 4.5, 0)
    with pytest.raises(ValueError):
        m.max_context_tokens(12 * GiB, s, 4.5, batch=0)
    with pytest.raises(ValueError):
        m.kv_cache_bytes(s, -1)
