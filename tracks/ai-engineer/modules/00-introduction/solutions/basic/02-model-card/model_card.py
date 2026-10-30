"""Đọc model card và config.json của model trên Hugging Face: giấy phép, số tham số, VRAM, KV cache.

Dùng thư viện chuẩn và `yaml` (PyYAML) trong tệp này. Không dùng transformers.
"""

from __future__ import annotations

import yaml


def read_frontmatter(text: str) -> dict:
    """Metadata YAML ở đầu model card (README.md của repo), giữa dòng `---` đầu tiên và dòng `---` kế tiếp.

    Không có frontmatter (dòng đầu không phải `---`) hoặc frontmatter rỗng thì trả `{}`.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            data = yaml.safe_load("\n".join(lines[1:end]))
            return data if isinstance(data, dict) else {}
    return {}


def _head_dim(config: dict) -> int:
    return config.get("head_dim") or config["hidden_size"] // config["num_attention_heads"]


def count_params(config: dict, active: bool = False) -> int:
    """Số tham số của một LLM decoder-only kiểu Llama/Qwen/Mistral (kể cả MoE kiểu Qwen3) từ config.json.

    `active=True`: số tham số một token thực sự đi qua (MoE chỉ tính `num_experts_per_tok` expert mỗi layer;
    model dense thì bằng tổng).
    """
    h = config["hidden_size"]
    n_heads = config["num_attention_heads"]
    n_kv = config.get("num_key_value_heads") or n_heads
    hd = _head_dim(config)
    model_type = config["model_type"]

    attn = h * n_heads * hd + 2 * h * n_kv * hd + n_heads * hd * h  # q, k, v, o
    if model_type == "qwen2":
        attn += n_heads * hd + 2 * n_kv * hd  # Qwen2 có bias ở q, k, v (không ở o)
    elif config.get("attention_bias"):
        attn += n_heads * hd + 2 * n_kv * hd + h  # bias ở cả q, k, v, o
    if model_type in ("qwen3", "qwen3_moe"):
        attn += 2 * hd  # q_norm, k_norm (RMSNorm trên mỗi head)

    if "num_experts" in config:
        n_exp = config["num_experts_per_tok"] if active else config["num_experts"]
        mlp = n_exp * 3 * h * config["moe_intermediate_size"] + h * config["num_experts"]  # experts + router
    else:
        mlp = 3 * h * config["intermediate_size"]  # gate, up, down

    per_layer = attn + mlp + 2 * h  # 2 RMSNorm
    embed = config["vocab_size"] * h
    lm_head = 0 if config["tie_word_embeddings"] else embed
    return config["num_hidden_layers"] * per_layer + h + embed + lm_head  # + norm cuối


def weights_gb(n_params: int, bits: float) -> float:
    """Dung lượng trọng số, GB = 10^9 byte."""
    return n_params * bits / 8 / 1e9


def kv_cache_gb(config: dict, seq_len: int, batch: int = 1, bytes_per_value: float = 2) -> float:
    """KV cache cho `batch` chuỗi dài `seq_len` token: 2 (K và V) × layer × head KV × head_dim × token × batch × byte."""
    n_kv = config.get("num_key_value_heads") or config["num_attention_heads"]
    return 2 * config["num_hidden_layers"] * n_kv * _head_dim(config) * seq_len * batch * bytes_per_value / 1e9


def fits_on_gpu(config: dict, vram_gb: float, bits: float, seq_len: int, batch: int = 1,
                overhead_gb: float = 0.5) -> bool:
    """Trọng số (MỌI tham số, kể cả expert không hoạt động) ở `bits` bit + KV cache bf16 + `overhead_gb` <= `vram_gb`."""
    need = weights_gb(count_params(config), bits) + kv_cache_gb(config, seq_len, batch) + overhead_gb
    return need <= vram_gb


def card_summary(readme_text: str, config: dict) -> dict:
    """Tóm tắt những gì cần biết trước khi đưa model vào sản phẩm.

    Khoá: `license` (giá trị `license`; nếu là "other" thì lấy `license_name`), `base_model` (chuỗi; frontmatter ghi
    danh sách thì lấy phần tử đầu; không có thì None), `params`, `active_params`, `context_length`
    (`max_position_embeddings`), `moe` (bool).
    """
    meta = read_frontmatter(readme_text)
    license_ = meta.get("license")
    if license_ == "other":
        license_ = meta.get("license_name", license_)
    base = meta.get("base_model")
    if isinstance(base, list):
        base = base[0] if base else None
    return {
        "license": license_,
        "base_model": base,
        "params": count_params(config),
        "active_params": count_params(config, active=True),
        "context_length": config["max_position_embeddings"],
        "moe": "num_experts" in config,
    }
