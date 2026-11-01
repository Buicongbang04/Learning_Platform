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
    cache: dict[str, torch.Tensor] = {}
    handles = []
    n_head = model.config.n_head

    def save_input(name):
        def hook(module, args):
            cache[name] = args[0].detach().clone()
        return hook

    def save_output(name):
        def hook(module, args, output):
            cache[name] = output.detach().clone()
        return hook

    def save_z(name):
        def hook(module, args):
            x = args[0].detach().clone()
            cache[name] = x.view(*x.shape[:-1], n_head, x.shape[-1] // n_head)
        return hook

    for l, block in enumerate(model.blocks):
        handles += [
            block.register_forward_pre_hook(save_input(f"resid_pre.{l}")),
            block.attn.register_forward_hook(save_output(f"attn_out.{l}")),
            block.ln2.register_forward_pre_hook(save_input(f"resid_mid.{l}")),
            block.mlp.register_forward_hook(save_output(f"mlp_out.{l}")),
            block.register_forward_hook(save_output(f"resid_post.{l}")),
            block.attn.attn_dropout.register_forward_hook(save_output(f"pattern.{l}")),
            block.attn.proj.register_forward_pre_hook(save_z(f"z.{l}")),
        ]
    was_training = model.training
    model.eval()
    try:
        with torch.no_grad():
            logits, _ = model(idx)
    finally:
        for h in handles:
            h.remove()
        model.train(was_training)
    return logits, cache


def head_contributions(model, cache: dict[str, torch.Tensor], layer: int) -> torch.Tensor:
    """Đóng góp của từng head vào residual stream ở Block `layer`, shape (B, T, n_head, C).

    Tổng theo head cộng `attn.proj.bias` bằng `attn_out.layer`.
    """
    z = cache[f"z.{layer}"]
    W_O = model.blocks[layer].attn.proj.weight.detach()
    n_head, head_dim = z.shape[-2], z.shape[-1]
    W_O = W_O.view(W_O.shape[0], n_head, head_dim)
    return torch.einsum("bthd,chd->bthc", z, W_O)


def residual_components(model, cache: dict[str, torch.Tensor], idx: torch.Tensor) -> dict[str, torch.Tensor]:
    """Tách residual stream cuối (`resid_post` của Block cuối) thành các thành phần cộng lại đúng bằng nó.

    Khoá theo thứ tự: `tok_emb`, `pos_emb`, rồi `attn_out.l`, `mlp_out.l` cho l = 0..L-1. Mỗi giá trị shape (B, T, C).
    """
    T = idx.shape[1]
    with torch.no_grad():
        parts = {
            "tok_emb": model.tok_emb(idx).detach(),
            "pos_emb": model.pos_emb(torch.arange(T, device=idx.device)).detach().expand(idx.shape[0], T, -1),
        }
    for l in range(len(model.blocks)):
        parts[f"attn_out.{l}"] = cache[f"attn_out.{l}"]
        parts[f"mlp_out.{l}"] = cache[f"mlp_out.{l}"]
    return parts
