"""Đọc model card và config.json của model trên Hugging Face: giấy phép, số tham số, VRAM, KV cache.

Dùng thư viện chuẩn và `yaml` (PyYAML) trong tệp này. Không dùng transformers.
"""

from __future__ import annotations

import yaml


def read_frontmatter(text: str) -> dict:
    """Metadata YAML ở đầu model card (README.md của repo), giữa dòng `---` đầu tiên và dòng `---` kế tiếp.

    Không có frontmatter (dòng đầu không phải `---`) hoặc frontmatter rỗng thì trả `{}`.
    """
    # TODO
    raise NotImplementedError


def count_params(config: dict, active: bool = False) -> int:
    """Số tham số của một LLM decoder-only kiểu Llama/Qwen/Mistral (kể cả MoE kiểu Qwen3) từ config.json.

    `active=True`: số tham số một token thực sự đi qua (MoE chỉ tính `num_experts_per_tok` expert mỗi layer;
    model dense thì bằng tổng).
    """
    # TODO
    raise NotImplementedError


def weights_gb(n_params: int, bits: float) -> float:
    """Dung lượng trọng số, GB = 10^9 byte."""
    # TODO
    raise NotImplementedError


def kv_cache_gb(config: dict, seq_len: int, batch: int = 1, bytes_per_value: float = 2) -> float:
    """KV cache cho `batch` chuỗi dài `seq_len` token: 2 (K và V) × layer × head KV × head_dim × token × batch × byte."""
    # TODO
    raise NotImplementedError


def fits_on_gpu(config: dict, vram_gb: float, bits: float, seq_len: int, batch: int = 1,
                overhead_gb: float = 0.5) -> bool:
    """Trọng số (MỌI tham số, kể cả expert không hoạt động) ở `bits` bit + KV cache bf16 + `overhead_gb` <= `vram_gb`."""
    # TODO
    raise NotImplementedError


def card_summary(readme_text: str, config: dict) -> dict:
    """Tóm tắt những gì cần biết trước khi đưa model vào sản phẩm.

    Khoá: `license` (giá trị `license`; nếu là "other" thì lấy `license_name`), `base_model` (chuỗi; frontmatter ghi
    danh sách thì lấy phần tử đầu; không có thì None), `params`, `active_params`, `context_length`
    (`max_position_embeddings`), `moe` (bool).
    """
    # TODO
    raise NotImplementedError
