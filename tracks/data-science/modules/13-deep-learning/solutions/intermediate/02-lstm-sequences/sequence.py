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
    lengths = torch.tensor([len(s) for s in seqs], dtype=torch.long)
    padded = torch.full((len(seqs), int(lengths.max())), pad_value, dtype=torch.long)
    for i, s in enumerate(seqs):
        padded[i, :len(s)] = torch.tensor(s, dtype=torch.long)
    return padded, lengths


class SequenceClassifier(nn.Module):
    """Embedding → RNN/GRU/LSTM một chiều, một tầng → Linear trên hidden state cuối của chuỗi.

    "Hidden state cuối" là trạng thái sau token THẬT cuối cùng của mỗi chuỗi, không phải sau
    padding: dùng pack_padded_sequence(..., lengths, batch_first=True, enforce_sorted=False).
    """

    def __init__(self, vocab_size: int, embed_dim: int, hidden_dim: int, n_classes: int,
                 cell: str = "lstm", padding_idx: int = 0):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, embed_dim, padding_idx=padding_idx)
        self.rnn = CELLS[cell](embed_dim, hidden_dim, batch_first=True)
        self.head = nn.Linear(hidden_dim, n_classes)

    def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        """x: (B, T) token id, lengths: (B,) → logits (B, n_classes)."""
        packed = pack_padded_sequence(self.embed(x), lengths.cpu(), batch_first=True, enforce_sorted=False)
        _, state = self.rnn(packed)
        h_n = state[0] if isinstance(state, tuple) else state     # LSTM: (h_n, c_n)
        return self.head(h_n[-1])                                 # h_n: (num_layers, B, H), đã về đúng thứ tự gốc


def clip_gradients(model: nn.Module, max_norm: float) -> float:
    """Cắt gradient sao cho chuẩn L2 của TOÀN BỘ gradient (gộp mọi tham số) không vượt max_norm.

    Trả về chuẩn trước khi cắt, dạng float (hữu ích để log: norm tăng vọt là dấu hiệu exploding gradient).
    """
    return float(nn.utils.clip_grad_norm_(model.parameters(), max_norm))


def train_classifier(model: nn.Module, X: torch.Tensor, lengths: torch.Tensor, y: torch.Tensor,
                     epochs: int, lr: float = 1e-3, batch_size: int = 32, clip: float = 1.0,
                     seed: int = 0) -> list[float]:
    """Adam + CrossEntropyLoss; mỗi batch: zero_grad, forward, backward, clip_gradients, step.

    Xáo thứ tự mỗi epoch bằng torch.Generator().manual_seed(seed + epoch).
    Trả loss trung bình theo mẫu của từng epoch.
    """
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.CrossEntropyLoss()
    history = []
    for epoch in range(epochs):
        model.train()
        order = torch.randperm(len(X), generator=torch.Generator().manual_seed(seed + epoch))
        total = 0.0
        for start in range(0, len(X), batch_size):
            idx = order[start:start + batch_size]
            opt.zero_grad()
            loss = loss_fn(model(X[idx], lengths[idx]), y[idx])
            loss.backward()
            clip_gradients(model, clip)
            opt.step()
            total += loss.item() * len(idx)
        history.append(total / len(X))
    return history
