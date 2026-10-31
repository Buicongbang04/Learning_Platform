"""Ước lượng bộ nhớ chạy một LLM decoder-only từ `config.json` của Hugging Face.

`config` là dict đọc từ config.json (Qwen2, Llama, Mistral, Phi-3 cùng khung kiến trúc):

- `vocab_size` (V), `hidden_size` (d), `num_hidden_layers` (L), `num_attention_heads` (h),
  `num_key_value_heads` (h_kv, thiếu thì bằng h), `intermediate_size` (d_ff),
  `head_dim` (thiếu hoặc null thì d // h), `tie_word_embeddings` (thiếu thì False),
  `max_position_embeddings`.
- Bias của q, k, v: có khi `config["attention_bias"]` là True; thiếu khoá này (hoặc null) thì có bias khi
  `model_type == "qwen2"` (Qwen2 luôn có bias ở q, k, v, không có ở o). Các Linear khác không có bias.

Mỗi tầng decoder gồm: q_proj (d → h·hd), k_proj và v_proj (d → h_kv·hd), o_proj (h·hd → d), MLP kiểu SwiGLU
3 ma trận d×d_ff (gate, up, down), 2 RMSNorm (mỗi cái d trọng số). Ngoài các tầng: embedding V×d, RMSNorm cuối
(d), lm_head d×V (dùng chung với embedding khi tie_word_embeddings).

Chỉ dùng thư viện chuẩn.
"""

from __future__ import annotations

import math

GIB = 1024**3

# Số byte mỗi tham số. q8_0 và q4_k_m là trung bình đo trên GGUF thật (scale mỗi block, tensor nhạy giữ độ chính
# xác cao hơn): qwen2.5:3b Q4_K_M 1 929 912 432 byte cho 3 085 938 688 tham số, khoảng 5.0 bit mỗi tham số.
BYTES_PER_PARAM = {
    "fp32": 4.0,
    "fp16": 2.0,
    "bf16": 2.0,
    "int8": 1.0,
    "q8_0": 8.5 / 8,
    "q4_k_m": 5.0 / 8,
    "int4": 0.5,
}


def head_dim(config: dict) -> int:
    """`head_dim` nếu có (khác null), không thì hidden_size // num_attention_heads."""
    hd = config.get("head_dim")
    return int(hd) if hd else config["hidden_size"] // config["num_attention_heads"]


def count_params(config: dict) -> int:
    """Tổng số tham số theo kiến trúc mô tả ở đầu tệp."""
    V, d, L = config["vocab_size"], config["hidden_size"], config["num_hidden_layers"]
    h = config["num_attention_heads"]
    h_kv = config.get("num_key_value_heads") or h
    hd, d_ff = head_dim(config), config["intermediate_size"]
    bias = config.get("attention_bias")
    if bias is None:
        bias = config.get("model_type") == "qwen2"
    q = d * h * hd + (h * hd if bias else 0)
    kv = 2 * (d * h_kv * hd + (h_kv * hd if bias else 0))
    o = h * hd * d
    mlp = 3 * d * d_ff
    per_layer = q + kv + o + mlp + 2 * d
    embed = V * d * (1 if config.get("tie_word_embeddings", False) else 2)
    return embed + L * per_layer + d


def weight_bytes(config: dict, dtype: str) -> float:
    """Byte cho trọng số: count_params × BYTES_PER_PARAM[dtype]."""
    return count_params(config) * BYTES_PER_PARAM[dtype]


def kv_cache_bytes(config: dict, seq_len: int, batch: int = 1, kv_dtype: str = "fp16") -> float:
    """Byte của KV cache: K và V, cho mỗi tầng, mỗi KV head, mỗi vị trí, mỗi chuỗi trong batch."""
    h_kv = config.get("num_key_value_heads") or config["num_attention_heads"]
    return 2 * config["num_hidden_layers"] * h_kv * head_dim(config) * seq_len * batch * BYTES_PER_PARAM[kv_dtype]


def estimate_memory(config: dict, dtype: str, seq_len: int, batch: int = 1, kv_dtype: str = "fp16",
                    overhead: float = 0.2) -> dict[str, float]:
    """{"weights", "kv_cache", "overhead", "total"} tính bằng byte.

    overhead (activation, buffer, CUDA context...) = overhead × (weights + kv_cache); total là tổng ba phần.
    """
    w = weight_bytes(config, dtype)
    kv = kv_cache_bytes(config, seq_len, batch, kv_dtype)
    extra = overhead * (w + kv)
    return {"weights": w, "kv_cache": kv, "overhead": extra, "total": w + kv + extra}


def max_context(config: dict, dtype: str, budget_bytes: float, batch: int = 1, kv_dtype: str = "fp16",
                overhead: float = 0.2) -> int:
    """seq_len lớn nhất (int) để estimate_memory(...)["total"] <= budget_bytes.

    Không vượt max_position_embeddings của model. Trọng số (kèm overhead) đã vượt ngân sách thì trả 0.
    """
    w = weight_bytes(config, dtype) * (1 + overhead)
    if w > budget_bytes:
        return 0
    per_token = kv_cache_bytes(config, 1, batch, kv_dtype) * (1 + overhead)
    n = math.floor((budget_bytes - w) / per_token)
    return int(min(n, config["max_position_embeddings"]))
