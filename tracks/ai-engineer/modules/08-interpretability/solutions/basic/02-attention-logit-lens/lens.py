"""Chấm điểm head attention, logit lens và direct logit attribution trên GPT mini của module 05."""

from __future__ import annotations

import torch


def repeated_tokens(vocab_size: int, half: int, batch: int, generator: torch.Generator, prefix: int | None = None) -> torch.Tensor:
    """Dãy ngẫu nhiên lặp lại hai lần: [prefix] + r + r, r gồm `half` token rút đều từ [0, vocab_size).

    r lấy bằng một lệnh `torch.randint(vocab_size, (batch, half), generator=generator)`. Shape (batch, 2*half) hoặc
    (batch, 1 + 2*half) nếu có `prefix`.
    """
    r = torch.randint(vocab_size, (batch, half), generator=generator)
    seq = torch.cat([r, r], dim=1)
    if prefix is not None:
        seq = torch.cat([torch.full((batch, 1), prefix, dtype=seq.dtype), seq], dim=1)
    return seq


def prev_token_score(pattern: torch.Tensor) -> torch.Tensor:
    """pattern (B, H, T, T) -> (H,): attention trung bình từ vị trí t tới t-1, trên mọi b và t >= 1."""
    return pattern.diagonal(offset=-1, dim1=-2, dim2=-1).mean(dim=(0, -1))


def _offset_score(pattern: torch.Tensor, half: int, shift: int) -> torch.Tensor:
    T = pattern.shape[-1]
    queries = torch.arange(T - half, T)
    keys = queries - half + shift
    return pattern[:, :, queries, keys].mean(dim=(0, -1))


def induction_score(pattern: torch.Tensor, half: int) -> torch.Tensor:
    """Với dãy [prefix] + r + r (nửa sau là `half` vị trí cuối): attention trung bình từ mỗi vị trí t của nửa sau tới
    vị trí t - half + 1 (token đứng **sau** lần xuất hiện trước của token hiện tại). Trả (H,)."""
    return _offset_score(pattern, half, 1)


def duplicate_token_score(pattern: torch.Tensor, half: int) -> torch.Tensor:
    """Như `induction_score` nhưng tới vị trí t - half (chính lần xuất hiện trước của token hiện tại). Trả (H,)."""
    return _offset_score(pattern, half, 0)


def logit_lens(model, resid: torch.Tensor) -> torch.Tensor:
    """Đọc residual stream ở giữa chừng ra logits như thể nó là stream cuối: `lm_head(ln_f(resid))`."""
    with torch.no_grad():
        return model.lm_head(model.ln_f(resid))


def token_rank(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """Hạng của token đích trong logits (0 là cao nhất): số token có logit lớn hơn hẳn logit của đích. Shape bằng targets."""
    target_logit = logits.gather(-1, targets.unsqueeze(-1))
    return (logits > target_logit).sum(dim=-1)


def direct_logit_attribution(model, components: dict[str, torch.Tensor], final_resid: torch.Tensor, direction: torch.Tensor) -> dict[str, torch.Tensor]:
    """Direct logit attribution: đóng góp của từng thành phần residual vào `ln_f(final_resid) @ direction`.

    `direction` shape (C,), ví dụ `lm_head.weight[a] - lm_head.weight[b]` (khi đó tổng là logit[a] - logit[b]). Thang của
    `ln_f` (độ lệch chuẩn của `final_resid`) giữ cố định, nên phép chiếu tuyến tính và tổng mọi thành phần cộng
    `ln_f.bias @ direction` bằng đúng `ln_f(final_resid) @ direction`. Mỗi giá trị trả về shape (B, T).
    """
    ln = model.ln_f
    with torch.no_grad():
        mean = final_resid.mean(dim=-1, keepdim=True)
        scale = torch.sqrt((final_resid - mean).pow(2).mean(dim=-1, keepdim=True) + ln.eps)
        w = ln.weight * direction
        out = {}
        for name, c in components.items():
            centered = c - c.mean(dim=-1, keepdim=True)
            out[name] = (centered / scale) @ w
    return out
