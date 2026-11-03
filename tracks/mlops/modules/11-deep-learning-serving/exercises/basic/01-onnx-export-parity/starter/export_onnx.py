from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch

INPUT_NAME = "pixel_values"
OUTPUT_NAME = "logits"
OPSET = 17
SIZE = 64


def export(model: torch.nn.Module, path: Path, size: int = SIZE) -> Path:
    # TODO: torch.onnx.export với opset OPSET, tên vào/ra INPUT_NAME/OUTPUT_NAME, trục 0 (batch) động ở cả vào và ra
    raise NotImplementedError


def pick_providers(available: list[str]) -> list[str]:
    # TODO: CUDA trước nếu có, CPU luôn đứng cuối; bỏ mọi provider khác
    raise NotImplementedError


def open_session(path: Path) -> ort.InferenceSession:
    return ort.InferenceSession(str(path), providers=pick_providers(ort.get_available_providers()))


def max_abs_diff(model: torch.nn.Module, session: ort.InferenceSession, batch: np.ndarray) -> float:
    # TODO: chạy cùng batch qua PyTorch (no_grad) và ONNX Runtime, trả sai khác tuyệt đối lớn nhất
    raise NotImplementedError


def verify(model: torch.nn.Module, path: Path, batch_sizes=(1, 4), atol: float = 1e-4, min_opset: int = OPSET) -> dict:
    # TODO: checker, opset, batch động ở vào và ra, so output theo từng batch size; sai thì ValueError
    raise NotImplementedError
