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
    model.eval()
    dummy = torch.zeros(2, 3, size, size)
    torch.onnx.export(
        model,
        (dummy,),
        str(path),
        opset_version=OPSET,
        input_names=[INPUT_NAME],
        output_names=[OUTPUT_NAME],
        dynamic_axes={INPUT_NAME: {0: "batch"}, OUTPUT_NAME: {0: "batch"}},
        dynamo=False,
    )
    return Path(path)


def pick_providers(available: list[str]) -> list[str]:
    providers = ["CUDAExecutionProvider"] if "CUDAExecutionProvider" in available else []
    return providers + ["CPUExecutionProvider"]


def open_session(path: Path) -> ort.InferenceSession:
    return ort.InferenceSession(str(path), providers=pick_providers(ort.get_available_providers()))


def max_abs_diff(model: torch.nn.Module, session: ort.InferenceSession, batch: np.ndarray) -> float:
    with torch.no_grad():
        expected = model.eval()(torch.from_numpy(batch)).numpy()
    actual = session.run([OUTPUT_NAME], {INPUT_NAME: batch})[0]
    if actual.shape != expected.shape:
        raise ValueError(f"shape lệch: ONNX {actual.shape}, PyTorch {expected.shape}")
    return float(np.max(np.abs(actual - expected)))


def _batch_dim_is_dynamic(value_info) -> bool:
    dims = value_info.type.tensor_type.shape.dim
    return bool(dims) and bool(dims[0].dim_param) and not dims[0].HasField("dim_value")


def verify(model: torch.nn.Module, path: Path, batch_sizes=(1, 4), atol: float = 1e-4, min_opset: int = OPSET) -> dict:
    proto = onnx.load(str(path))
    onnx.checker.check_model(proto)
    opset = next(o.version for o in proto.opset_import if o.domain in ("", "ai.onnx"))
    if opset < min_opset:
        raise ValueError(f"opset {opset} thấp hơn mức tối thiểu {min_opset}")
    for value in (proto.graph.input[0], proto.graph.output[0]):
        if not _batch_dim_is_dynamic(value):
            raise ValueError(f"trục batch của '{value.name}' bị cố định, cần dim_param")
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    worst = 0.0
    for size in batch_sizes:
        batch = np.random.default_rng(size).random((size, 3, SIZE, SIZE), dtype=np.float32)
        diff = max_abs_diff(model, session, batch)
        if diff > atol:
            raise ValueError(f"batch {size}: output lệch {diff:.2e} > atol {atol:.0e}")
        worst = max(worst, diff)
    return {"opset": opset, "max_abs_diff": worst, "batch_sizes": list(batch_sizes)}
