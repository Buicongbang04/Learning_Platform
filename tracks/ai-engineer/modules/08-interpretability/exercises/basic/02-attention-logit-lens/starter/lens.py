"""Chấm điểm head attention, logit lens và direct logit attribution trên GPT mini của module 05."""

from __future__ import annotations

import torch


def repeated_tokens(vocab_size: int, half: int, batch: int, generator: torch.Generator, prefix: int | None = None) -> torch.Tensor:
    """Dãy ngẫu nhiên lặp lại hai lần: [prefix] + r + r, r gồm `half` token rút đều từ [0, vocab_size).

    r lấy bằng một lệnh `torch.randint(vocab_size, (batch, half), generator=generator)`. Shape (batch, 2*half) hoặc
    (batch, 1 + 2*half) nếu có `prefix`.
    """
    # TODO
    raise NotImplementedError


def prev_token_score(pattern: torch.Tensor) -> torch.Tensor:
    """pattern (B, H, T, T) -> (H,): attention trung bình từ vị trí t tới t-1, trên mọi b và t >= 1."""
    # TODO
    raise NotImplementedError


def induction_score(pattern: torch.Tensor, half: int) -> torch.Tensor:
    """Với dãy [prefix] + r + r (nửa sau là `half` vị trí cuối): attention trung bình từ mỗi vị trí t của nửa sau tới
    vị trí t - half + 1 (token đứng **sau** lần xuất hiện trước của token hiện tại). Trả (H,)."""
    # TODO
    raise NotImplementedError


def duplicate_token_score(pattern: torch.Tensor, half: int) -> torch.Tensor:
    """Như `induction_score` nhưng tới vị trí t - half (chính lần xuất hiện trước của token hiện tại). Trả (H,)."""
    # TODO
    raise NotImplementedError


def logit_lens(model, resid: torch.Tensor) -> torch.Tensor:
    """Đọc residual stream ở giữa chừng ra logits theo đúng đường mà residual stream cuối đi qua để thành logits.

    Không gradient. Ở stream cuối, kết quả phải bằng logits của model."""
    # TODO
    raise NotImplementedError


def token_rank(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """Hạng của token đích trong logits (0 là cao nhất): số token có logit lớn hơn hẳn logit của đích. Shape bằng targets."""
    # TODO
    raise NotImplementedError


def direct_logit_attribution(model, components: dict[str, torch.Tensor], final_resid: torch.Tensor, direction: torch.Tensor) -> dict[str, torch.Tensor]:
    """Direct logit attribution: đóng góp của từng thành phần residual vào `ln_f(final_resid) @ direction`.

    `direction` shape (C,), ví dụ `lm_head.weight[a] - lm_head.weight[b]` (khi đó tổng là logit[a] - logit[b]). Thang của
    `ln_f` (độ lệch chuẩn của `final_resid`) giữ cố định, nên phép chiếu tuyến tính và tổng mọi thành phần cộng
    `ln_f.bias @ direction` bằng đúng `ln_f(final_resid) @ direction`. Mỗi giá trị trả về shape (B, T).
    """
    # TODO
    raise NotImplementedError
