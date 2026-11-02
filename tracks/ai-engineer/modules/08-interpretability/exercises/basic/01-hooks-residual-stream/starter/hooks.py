"""Hook và cache cho GPT mini của module 05 (lớp `GPT` trong `05-transformers-llm-architecture/.../gpt.py`).

Tên khoá trong cache (l là chỉ số Block, bắt đầu từ 0):
- `resid_pre.l`: residual stream đi vào Block l (trước `ln1`); `resid_pre.0` là tok_emb + pos_emb.
- `attn_out.l`: output của `blocks[l].attn` (đã qua `proj`, trước khi cộng vào stream).
- `resid_mid.l`: residual stream sau khi cộng attention (đi vào `ln2`).
- `mlp_out.l`: output của `blocks[l].mlp`.
- `resid_post.l`: residual stream ra khỏi Block l.
- `pattern.l`: ma trận attention sau softmax, shape (B, n_head, T, T).
- `z.l`: input của `blocks[l].attn.proj`, shape (B, T, n_head, head_dim): output từng head trước khi chiếu.
"""

from __future__ import annotations

import torch


def run_with_cache(model, idx: torch.Tensor) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Chạy model ở chế độ eval, không gradient; trả (logits, cache) với đủ các khoá ở đầu tệp cho mọi Block.

    Tensor trong cache tách khỏi graph và là bản sao. Gỡ mọi hook kể cả khi forward lỗi; trả lại chế độ train/eval như trước.
    """
    # TODO
    raise NotImplementedError


def head_contributions(model, cache: dict[str, torch.Tensor], layer: int) -> torch.Tensor:
    """Đóng góp của từng head vào residual stream ở Block `layer`, shape (B, T, n_head, C).

    Tổng theo head cộng `attn.proj.bias` bằng `attn_out.layer`.
    """
    # TODO
    raise NotImplementedError


def residual_components(model, cache: dict[str, torch.Tensor], idx: torch.Tensor) -> dict[str, torch.Tensor]:
    """Tách residual stream cuối (`resid_post` của Block cuối) thành các thành phần cộng lại đúng bằng nó.

    Khoá theo thứ tự: `tok_emb`, `pos_emb`, rồi `attn_out.l`, `mlp_out.l` cho l = 0..L-1. Mỗi giá trị shape (B, T, C).
    """
    # TODO
    raise NotImplementedError
