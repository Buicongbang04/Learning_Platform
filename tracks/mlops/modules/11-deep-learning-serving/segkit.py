"""Model phân đoạn tí hon và dữ liệu tổng hợp dùng chung cho test của module 11 (không phải bài tập)."""

from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
from torch import nn

NUM_CLASSES = 3
SIZE = 64
INPUT_NAME = "pixel_values"
OUTPUT_NAME = "logits"


class TinySeg(nn.Module):
    def __init__(self, channels: int = 16, classes: int = NUM_CLASSES):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(3, channels, 3, padding=1), nn.ReLU(),
            nn.Conv2d(channels, 2 * channels, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(2 * channels, 2 * channels, 3, padding=1), nn.ReLU(),
        )
        self.head = nn.Sequential(
            nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False),
            nn.Conv2d(2 * channels, channels, 3, padding=1), nn.ReLU(),
            nn.Conv2d(channels, classes, 1),
        )

    def forward(self, x):
        return self.head(self.encoder(x))


def tiny_model(seed: int = 0, channels: int = 16) -> TinySeg:
    torch.manual_seed(seed)
    return TinySeg(channels).eval()


def synthetic(n: int, size: int = SIZE, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Ảnh nhiễu có một đĩa màu (thú cưng) và viền: mask 0 nền, 1 thú cưng, 2 viền."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size]
    images = rng.normal(0.45, 0.12, (n, 3, size, size)).astype(np.float32)
    masks = np.zeros((n, size, size), dtype=np.int64)
    for i in range(n):
        cy, cx = rng.uniform(size * 0.3, size * 0.7, 2)
        r = rng.uniform(size * 0.15, size * 0.3)
        d = np.hypot(yy - cy, xx - cx)
        color = rng.uniform(0.75, 1.0, 3).astype(np.float32)
        inside = d < r
        border = (d >= r) & (d < r + 2.5)
        images[i][:, inside] = color[:, None] + rng.normal(0, 0.05, (3, int(inside.sum()))).astype(np.float32)
        masks[i][inside] = 1
        masks[i][border] = 2
    return np.clip(images, 0, 1), masks


@lru_cache(maxsize=2)
def trained_model(steps: int = 120, seed: int = 0) -> TinySeg:
    torch.set_num_threads(min(4, torch.get_num_threads()))
    torch.manual_seed(seed)
    model = TinySeg()
    images, masks = synthetic(256, seed=seed + 100)
    x, y = torch.from_numpy(images), torch.from_numpy(masks)
    optimizer = torch.optim.Adam(model.parameters(), lr=3e-3)
    weight = torch.tensor([1.0, 1.0, 3.0])
    generator = torch.Generator().manual_seed(seed)
    model.train()
    for _ in range(steps):
        idx = torch.randint(0, len(x), (32,), generator=generator)
        loss = nn.functional.cross_entropy(model(x[idx]), y[idx], weight=weight)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    return model.eval()


def export(model: nn.Module, path: Path, opset: int = 17, dynamic: bool = True, size: int = SIZE) -> Path:
    dummy = torch.zeros(2, 3, size, size)
    axes = {INPUT_NAME: {0: "batch"}, OUTPUT_NAME: {0: "batch"}} if dynamic else None
    torch.onnx.export(model, (dummy,), str(path), opset_version=opset, input_names=[INPUT_NAME],
                      output_names=[OUTPUT_NAME], dynamic_axes=axes, dynamo=False)
    return Path(path)


def ort_session(path: Path):
    import onnxruntime as ort

    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.log_severity_level = 3
    return ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])


def miou(pred: np.ndarray, target: np.ndarray, classes: int = NUM_CLASSES) -> float:
    scores = []
    for c in range(classes):
        union = np.logical_or(pred == c, target == c).sum()
        if union:
            scores.append(np.logical_and(pred == c, target == c).sum() / union)
    return float(np.mean(scores))
