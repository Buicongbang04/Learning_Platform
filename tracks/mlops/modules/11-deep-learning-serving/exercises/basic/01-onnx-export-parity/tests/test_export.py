import json

import numpy as np
import onnx
import pytest
import torch

import mlopskit
import segkit
from testkit import Exercise

ex = Exercise(__file__)


def dims(value):
    return [d.dim_param or d.dim_value for d in value.type.tensor_type.shape.dim]


def export_tiny(tmp_path):
    mod = ex.module("export_onnx.py")
    model = segkit.tiny_model(seed=1)
    path = mod.export(model, tmp_path / "seg.onnx")
    return mod, model, path


def test_export_names_opset_and_dynamic_batch(tmp_path):
    mod, _, path = export_tiny(tmp_path)
    proto = onnx.load(str(path))
    onnx.checker.check_model(proto)
    assert [i.name for i in proto.graph.input] == ["pixel_values"]
    assert [o.name for o in proto.graph.output] == ["logits"]
    assert next(o.version for o in proto.opset_import if o.domain in ("", "ai.onnx")) == 17
    assert isinstance(dims(proto.graph.input[0])[0], str), "trục 0 của input phải là dim_param (động)"
    assert isinstance(dims(proto.graph.output[0])[0], str), "trục 0 của output phải là dim_param (động)"
    assert dims(proto.graph.input[0])[1:] == [3, 64, 64]


def test_onnxruntime_runs_any_batch_size(tmp_path):
    mod, _, path = export_tiny(tmp_path)
    session = segkit.ort_session(path)
    for size in (1, 3, 8):
        out = session.run(None, {"pixel_values": np.zeros((size, 3, 64, 64), np.float32)})[0]
        assert out.shape == (size, 3, 64, 64)


def test_max_abs_diff_matches_pytorch(tmp_path):
    mod, model, path = export_tiny(tmp_path)
    batch = np.random.default_rng(0).random((5, 3, 64, 64), dtype=np.float32)
    diff = mod.max_abs_diff(model, segkit.ort_session(path), batch)
    assert 0 <= diff < 1e-4
    with torch.no_grad():
        model.head[-1].bias.add_(0.5)
    assert mod.max_abs_diff(model, segkit.ort_session(path), batch) == pytest.approx(0.5, abs=1e-3)


def test_verify_passes_on_good_export(tmp_path):
    mod, model, path = export_tiny(tmp_path)
    report = mod.verify(model, path, batch_sizes=(1, 4, 7))
    assert report["opset"] == 17
    assert report["batch_sizes"] == [1, 4, 7]
    assert 0 <= report["max_abs_diff"] < 1e-4


def test_verify_rejects_fixed_batch(tmp_path):
    mod = ex.module("export_onnx.py")
    model = segkit.tiny_model(seed=2)
    path = segkit.export(model, tmp_path / "fixed.onnx", dynamic=False)
    with pytest.raises(ValueError, match="batch"):
        mod.verify(model, path)


def test_verify_rejects_old_opset(tmp_path):
    mod = ex.module("export_onnx.py")
    model = segkit.tiny_model(seed=3)
    path = segkit.export(model, tmp_path / "old.onnx", opset=13)
    with pytest.raises(ValueError, match="opset"):
        mod.verify(model, path)


def test_verify_rejects_output_drift(tmp_path):
    mod = ex.module("export_onnx.py")
    model = segkit.tiny_model(seed=4)
    path = segkit.export(model, tmp_path / "seg.onnx")
    with torch.no_grad():
        model.encoder[0].weight.mul_(1.001)
    with pytest.raises(ValueError, match="atol"):
        mod.verify(model, path, atol=1e-6)


def test_pick_providers_fallback_order():
    mod = ex.module("export_onnx.py")
    assert mod.pick_providers(["AzureExecutionProvider", "CPUExecutionProvider"]) == ["CPUExecutionProvider"]
    assert mod.pick_providers(["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]) == [
        "CUDAExecutionProvider", "CPUExecutionProvider"]
    assert mod.pick_providers([]) == ["CPUExecutionProvider"]


def test_open_session_on_cpu_env(tmp_path):
    mod, _, path = export_tiny(tmp_path)
    assert mod.open_session(path).get_providers() == ["CPUExecutionProvider"]


GPU_SCRIPT = """
import json, sys
import numpy as np, onnxruntime as ort
ort.preload_dlls()
path = "seg.onnx"
gpu = ort.InferenceSession(path, providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
cpu = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
x = np.random.default_rng(0).random((4, 3, 64, 64), dtype=np.float32)
a = gpu.run(None, {"pixel_values": x})[0]
b = cpu.run(None, {"pixel_values": x})[0]
print(json.dumps({"providers": gpu.get_providers(), "max_diff": float(np.abs(a - b).max())}))
"""


def test_gpu_cuda_provider_matches_cpu(tmp_path):
    mlopskit.require_cuda()
    mod = ex.module("export_onnx.py")
    mod.export(segkit.tiny_model(seed=5), tmp_path / "seg.onnx")
    result = mlopskit.gpu_python(GPU_SCRIPT, cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(result.stdout.strip().splitlines()[-1])
    assert data["providers"][0] == "CUDAExecutionProvider", f"ONNX Runtime lặng lẽ fallback về CPU: {data['providers']}"
    assert data["max_diff"] < 1e-3
