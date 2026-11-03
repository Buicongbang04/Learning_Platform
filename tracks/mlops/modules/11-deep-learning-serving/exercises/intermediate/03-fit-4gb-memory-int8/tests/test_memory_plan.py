import json
from pathlib import Path

import numpy as np
import onnx
import pytest

import mlopskit
import segkit
from testkit import Exercise

ex = Exercise(__file__)
ELEMENTS_PER_IMAGE = 3 * 64 * 64 + 2 * 16 * 64 * 64 + 4 * 32 * 32 * 32 + 32 * 64 * 64 + 2 * 16 * 64 * 64 + 3 * 64 * 64


def tiny_onnx(tmp_path, trained=False):
    model = segkit.trained_model() if trained else segkit.tiny_model()
    return segkit.export(model, tmp_path / "seg.onnx")


def test_activation_bytes_counts_every_tensor(tmp_path):
    plan = ex.module("memory_plan.py")
    path = tiny_onnx(tmp_path)
    one = plan.activation_bytes(path, 1)
    assert one == pytest.approx(ELEMENTS_PER_IMAGE * 4, rel=0.01)
    assert plan.activation_bytes(path, 8) == pytest.approx(8 * one, rel=0.01)
    assert plan.activation_bytes(path, 8, bytes_per_element=2) == plan.activation_bytes(path, 8) // 2


def test_weight_bytes(tmp_path):
    plan = ex.module("memory_plan.py")
    path = tiny_onnx(tmp_path)
    params = sum(p.numel() for p in segkit.tiny_model().parameters())
    assert plan.weight_bytes(path) == params * 4
    assert plan.weight_bytes(path, bytes_per_element=2) == params * 2


def test_max_batch_size_fits_budget(tmp_path):
    plan = ex.module("memory_plan.py")
    path = tiny_onnx(tmp_path)
    weights = plan.weight_bytes(path)
    budget = weights + plan.activation_bytes(path, 10) + 1000
    assert plan.max_batch_size(path, budget) == 10
    assert plan.max_batch_size(path, budget, bytes_per_element=2) >= 20
    assert plan.max_batch_size(path, budget, reserve_bytes=plan.activation_bytes(path, 4)) == 6
    assert plan.max_batch_size(path, weights + 100) == 0
    big = 4 * 2**30
    b = plan.max_batch_size(path, big, reserve_bytes=2**30)
    assert weights + 2**30 + plan.activation_bytes(path, b) <= big < weights + 2**30 + plan.activation_bytes(path, b + 1)


def test_mean_iou():
    plan = ex.module("memory_plan.py")
    target = np.array([[0, 0, 1, 1], [0, 2, 2, 1]])
    pred = np.array([[0, 0, 1, 0], [0, 2, 1, 1]])
    expected = np.mean([3 / 4, 2 / 4, 1 / 2])
    assert plan.mean_iou(pred, target) == pytest.approx(expected)
    assert plan.mean_iou(target, target) == 1.0
    assert plan.mean_iou(np.zeros((2, 2)), np.zeros((2, 2))) == 1.0


def test_int8_smaller_and_close_in_quality(tmp_path):
    plan = ex.module("memory_plan.py")
    fp32 = tiny_onnx(tmp_path, trained=True)
    int8 = plan.quantize_int8(fp32, tmp_path / "seg-int8.onnx")
    ops = {n.op_type for n in onnx.load(str(int8)).graph.node}
    assert ops & {"ConvInteger", "MatMulInteger", "QLinearConv", "DynamicQuantizeLinear"}, f"không thấy op lượng tử hoá: {ops}"
    images, masks = segkit.synthetic(64, seed=11)
    report = plan.int8_report(fp32, int8, images, masks)
    assert set(report) == {"fp32_bytes", "int8_bytes", "fp32_miou", "int8_miou"}
    assert report["int8_bytes"] <= 0.5 * report["fp32_bytes"]
    assert report["fp32_miou"] > 0.85
    assert report["fp32_miou"] - report["int8_miou"] <= 0.02, report


GPU_SCRIPT = """
import json, sys
sys.path[:0] = [{module_dir!r}, {target_dir!r}]
import torch, segkit
from gpu_memory import peak_memory_mib
sizes = [1, 8, 32, 64]
runs = {{
    "fp32": peak_memory_mib(segkit.tiny_model(), sizes, size=128, dtype=torch.float32),
    "fp16": peak_memory_mib(segkit.tiny_model(), sizes, size=128, dtype=torch.float16),
    "fp16_cl": peak_memory_mib(segkit.tiny_model(), sizes, size=128, dtype=torch.float16, channels_last=True),
}}
print(json.dumps(runs))
"""


def test_gpu_peak_memory_by_batch_and_dtype(tmp_path):
    mlopskit.require_cuda()
    target = ex.path("gpu_memory.py").parent
    script = GPU_SCRIPT.format(module_dir=str(Path(segkit.__file__).parent), target_dir=str(target))
    result = mlopskit.gpu_python(script, cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(result.stdout.strip().splitlines()[-1])
    runs = {name: [data[name][str(b)] for b in (1, 8, 32, 64)] for name in data}
    fp32 = runs["fp32"]
    assert fp32 == sorted(fp32) and fp32[-1] > 20 * fp32[0], f"bộ nhớ phải tăng gần tuyến tính theo batch: {fp32}"
    assert runs["fp16"][-1] <= fp32[-1], runs
    assert runs["fp16_cl"][-1] < 0.6 * fp32[-1], f"FP16 + channels_last phải gần nửa FP32: {runs}"
