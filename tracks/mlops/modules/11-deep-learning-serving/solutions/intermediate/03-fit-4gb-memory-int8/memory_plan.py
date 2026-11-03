from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
from onnxruntime.quantization import QuantType, quantize_dynamic

INPUT_NAME = "pixel_values"
NUM_CLASSES = 3


def activation_bytes(onnx_path: Path, batch_size: int, bytes_per_element: int = 4) -> int:
    model = onnx.load(str(onnx_path))
    for value in [*model.graph.input, *model.graph.output]:
        value.type.tensor_type.shape.dim[0].dim_value = batch_size
    del model.graph.value_info[:]
    model = onnx.shape_inference.infer_shapes(model, strict_mode=True)
    initializers = {i.name for i in model.graph.initializer}
    elements = 0
    for value in [*model.graph.input, *model.graph.value_info, *model.graph.output]:
        if value.name in initializers:
            continue
        elements += int(np.prod([d.dim_value for d in value.type.tensor_type.shape.dim]))
    return elements * bytes_per_element


def weight_bytes(onnx_path: Path, bytes_per_element: int = 4) -> int:
    model = onnx.load(str(onnx_path))
    return sum(int(np.prod(i.dims)) for i in model.graph.initializer) * bytes_per_element


def max_batch_size(onnx_path: Path, budget_bytes: int, bytes_per_element: int = 4, reserve_bytes: int = 0) -> int:
    fixed = weight_bytes(onnx_path, bytes_per_element) + reserve_bytes

    def fits(batch: int) -> bool:
        return fixed + activation_bytes(onnx_path, batch, bytes_per_element) <= budget_bytes

    if not fits(1):
        return 0
    low, high = 1, 2
    while fits(high):
        low, high = high, high * 2
    while high - low > 1:
        middle = (low + high) // 2
        low, high = (middle, high) if fits(middle) else (low, middle)
    return low


def quantize_int8(src: Path, dst: Path) -> Path:
    quantize_dynamic(str(src), str(dst), weight_type=QuantType.QUInt8)
    return Path(dst)


def mean_iou(pred: np.ndarray, target: np.ndarray, num_classes: int = NUM_CLASSES) -> float:
    scores = []
    for c in range(num_classes):
        union = np.logical_or(pred == c, target == c).sum()
        if union:
            scores.append(np.logical_and(pred == c, target == c).sum() / union)
    return float(np.mean(scores))


def _predict(path: Path, images: np.ndarray) -> np.ndarray:
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    return session.run(None, {INPUT_NAME: images})[0].argmax(axis=1)


def int8_report(fp32_path: Path, int8_path: Path, images: np.ndarray, masks: np.ndarray) -> dict:
    return {
        "fp32_bytes": Path(fp32_path).stat().st_size,
        "int8_bytes": Path(int8_path).stat().st_size,
        "fp32_miou": mean_iou(_predict(fp32_path, images), masks),
        "int8_miou": mean_iou(_predict(int8_path, images), masks),
    }
