"""Phân loại chuỗi độ dài thay đổi bằng RNN / GRU / LSTM, có packing và gradient clipping."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence

CELLS = {"rnn": nn.RNN, "gru": nn.GRU, "lstm": nn.LSTM}


def pad_sequences(seqs: list[list[int]], pad_value: int = 0) -> tuple[torch.Tensor, torch.Tensor]:
    """Đệm danh sách chuỗi về cùng độ dài (đệm bên phải).

    Trả về (padded LongTensor (B, T_max), lengths LongTensor (B,)).
    """
    # TODO
    raise NotImplementedError


class SequenceClassifier(nn.Module):
    """Embedding → RNN/GRU/LSTM một chiều, một tầng → Linear trên hidden state cuối của chuỗi.

    "Hidden state cuối" là trạng thái sau token THẬT cuối cùng của mỗi chuỗi, không phải sau
    padding: dùng pack_padded_sequence(..., lengths, batch_first=True, enforce_sorted=False).
    """

    def __init__(self, vocab_size: int, embed_dim: int, hidden_dim: int, n_classes: int,
                 cell: str = "lstm", padding_idx: int = 0):
        super().__init__()
        # TODO: self.embed, self.rnn = CELLS[cell](..., batch_first=True), self.head
        raise NotImplementedError

    def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        """x: (B, T) token id, lengths: (B,) → logits (B, n_classes)."""
        # TODO: embed → pack → rnn → lấy h_n (LSTM trả (h_n, c_n)) → head
        raise NotImplementedError


def clip_gradients(model: nn.Module, max_norm: float) -> float:
    """Cắt gradient sao cho chuẩn L2 của TOÀN BỘ gradient (gộp mọi tham số) không vượt max_norm.

    Trả về chuẩn trước khi cắt, dạng float (hữu ích để log: norm tăng vọt là dấu hiệu exploding gradient).
    """
    # TODO
    raise NotImplementedError


def train_classifier(model: nn.Module, X: torch.Tensor, lengths: torch.Tensor, y: torch.Tensor,
                     epochs: int, lr: float = 1e-3, batch_size: int = 32, clip: float = 1.0,
                     seed: int = 0) -> list[float]:
    """Adam + CrossEntropyLoss; mỗi batch: zero_grad, forward, backward, clip_gradients, step.

    Xáo thứ tự mỗi epoch bằng torch.Generator().manual_seed(seed + epoch).
    Trả loss trung bình theo mẫu của từng epoch.
    """
    # TODO
    raise NotImplementedError
