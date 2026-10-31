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
    # TODO
    raise NotImplementedError


def count_params(config: dict) -> int:
    """Tổng số tham số theo kiến trúc mô tả ở đầu tệp."""
    # TODO
    raise NotImplementedError


def weight_bytes(config: dict, dtype: str) -> float:
    """Byte cho trọng số: count_params × BYTES_PER_PARAM[dtype]."""
    # TODO
    raise NotImplementedError


def kv_cache_bytes(config: dict, seq_len: int, batch: int = 1, kv_dtype: str = "fp16") -> float:
    """Byte của KV cache: K và V, cho mỗi tầng, mỗi KV head, mỗi vị trí, mỗi chuỗi trong batch."""
    # TODO
    raise NotImplementedError


def estimate_memory(config: dict, dtype: str, seq_len: int, batch: int = 1, kv_dtype: str = "fp16",
                    overhead: float = 0.2) -> dict[str, float]:
    """{"weights", "kv_cache", "overhead", "total"} tính bằng byte.

    overhead (activation, buffer, CUDA context...) = overhead × (weights + kv_cache); total là tổng ba phần.
    """
    # TODO
    raise NotImplementedError


def max_context(config: dict, dtype: str, budget_bytes: float, batch: int = 1, kv_dtype: str = "fp16",
                overhead: float = 0.2) -> int:
    """seq_len lớn nhất (int) để estimate_memory(...)["total"] <= budget_bytes.

    Không vượt max_position_embeddings của model. Trọng số (kèm overhead) đã vượt ngân sách thì trả 0.
    """
    # TODO
    raise NotImplementedError
