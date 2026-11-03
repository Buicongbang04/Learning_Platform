from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
from onnxruntime.quantization import QuantType, quantize_dynamic

INPUT_NAME = "pixel_values"
NUM_CLASSES = 3


def activation_bytes(onnx_path: Path, batch_size: int, bytes_per_element: int = 4) -> int:
    # TODO: cố định trục batch, onnx.shape_inference, cộng số phần tử của input, value_info và output (trừ initializer)
    raise NotImplementedError


def weight_bytes(onnx_path: Path, bytes_per_element: int = 4) -> int:
    # TODO: tổng số phần tử của các initializer nhân bytes_per_element
    raise NotImplementedError


def max_batch_size(onnx_path: Path, budget_bytes: int, bytes_per_element: int = 4, reserve_bytes: int = 0) -> int:
    # TODO: batch lớn nhất mà weight + activation + reserve không vượt budget (0 nếu không vừa batch 1)
    raise NotImplementedError


def quantize_int8(src: Path, dst: Path) -> Path:
    # TODO: quantize_dynamic, trọng số QUInt8
    raise NotImplementedError


def mean_iou(pred: np.ndarray, target: np.ndarray, num_classes: int = NUM_CLASSES) -> float:
    # TODO: trung bình IoU các lớp có mặt (union > 0)
    raise NotImplementedError


def int8_report(fp32_path: Path, int8_path: Path, images: np.ndarray, masks: np.ndarray) -> dict:
    # TODO: fp32_bytes, int8_bytes (kích thước tệp), fp32_miou, int8_miou (ONNX Runtime CPU, argmax theo lớp)
    raise NotImplementedError
