import importlib.util
import io
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import torch
from fastapi.testclient import TestClient
from PIL import Image

import segkit
from testkit import Exercise

ex = Exercise(__file__)
FIXTURES = Path(__file__).parent / "fixtures"
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


device_module = load(FIXTURES / "device.py", "incident_device")


class Normalized(torch.nn.Module):
    def __init__(self, inner):
        super().__init__()
        self.inner = inner
        self.register_buffer("mean", torch.from_numpy(MEAN).view(1, 3, 1, 1))
        self.register_buffer("std", torch.from_numpy(STD).view(1, 3, 1, 1))

    def forward(self, x):
        return self.inner(x * self.std + self.mean)


def model_file(tmp_path):
    return segkit.export(Normalized(segkit.tiny_model(seed=9)).eval(), tmp_path / "seg.onnx")


def image_bytes(seed, size=(96, 80)):
    pixels = np.random.default_rng(seed).integers(0, 256, (size[1], size[0], 3), dtype=np.uint8)
    buffer = io.BytesIO()
    Image.fromarray(pixels).save(buffer, format="PNG")
    return buffer.getvalue()


def expected_mask(path, data):
    image = Image.open(io.BytesIO(data))
    resized = image.convert("RGB").resize((64, 64), Image.BILINEAR)
    x = ((np.asarray(resized, dtype=np.float32) / 255.0 - MEAN) / STD).transpose(2, 0, 1)[None]
    logits = segkit.ort_session(path).run(None, {"pixel_values": np.ascontiguousarray(x, dtype=np.float32)})[0][0]
    return np.asarray(Image.fromarray(logits.argmax(0).astype(np.uint8), mode="L").resize(image.size, Image.NEAREST))


def post(client, data):
    return client.post("/segment", files={"file": ("pet.png", data, "image/png")})


def burst(client, payloads):
    with ThreadPoolExecutor(len(payloads)) as pool:
        return list(pool.map(lambda data: post(client, data), payloads))


def service(path=None):
    return load(path or ex.path("service.py"), "incident_service")


def test_incident_build_reproduces_the_symptom(tmp_path):
    module = service(FIXTURES / "service_incident.py")
    device = device_module.SimulatedGPU()
    with TestClient(module.create_app(model_file(tmp_path), device)) as client:
        assert all(post(client, image_bytes(i)).status_code == 200 for i in range(5))
        codes = [r.status_code for r in burst(client, [image_bytes(i) for i in range(48)])]
        assert any(code != 200 for code in codes), "bản lúc sự cố phải lỗi khi có đợt request đồng thời"
        assert post(client, image_bytes(99)).status_code == 504, "...và không phục vụ được request nào sau đó"
        assert client.get("/healthz").status_code == 200


def test_sequential_requests_keep_working(tmp_path):
    path = model_file(tmp_path)
    with TestClient(service().create_app(path, device_module.SimulatedGPU())) as client:
        for i in range(5):
            response = post(client, image_bytes(i))
            assert response.status_code == 200
            assert response.headers["x-model-version"] == "seg-tiny-1"
            np.testing.assert_array_equal(np.asarray(Image.open(io.BytesIO(response.content))), expected_mask(path, image_bytes(i)))


def check_burst(tmp_path, device, count):
    path = model_file(tmp_path)
    payloads = [image_bytes(i, size=(64 + i, 70)) for i in range(count)]
    with TestClient(service().create_app(path, device)) as client:
        for _ in range(2):
            responses = burst(client, payloads)
            assert [r.status_code for r in responses] == [200] * count, [r.status_code for r in responses]
            for data, response in zip(payloads, responses):
                got = np.asarray(Image.open(io.BytesIO(response.content)))
                np.testing.assert_array_equal(got, expected_mask(path, data))
        assert post(client, image_bytes(500)).status_code == 200
    return device


def test_survives_bursts_on_the_production_card(tmp_path):
    device = check_burst(tmp_path, device_module.SimulatedGPU(), 32)
    assert max(device.runs) > 1, f"service phải giữ việc gom request đồng thời: {device.runs}"


def test_survives_bursts_on_a_smaller_card(tmp_path):
    device = check_burst(tmp_path, device_module.SimulatedGPU(total_mib=2048), 24)
    assert max(device.runs) > 1, f"service phải giữ việc gom request đồng thời: {device.runs}"


def test_inference_error_fails_fast_and_service_recovers(tmp_path):
    device = device_module.SimulatedGPU()
    with TestClient(service().create_app(model_file(tmp_path), device)) as client:
        assert post(client, image_bytes(1)).status_code == 200
        device.inject_failure()
        assert post(client, image_bytes(2)).status_code == 500
        assert [post(client, image_bytes(i)).status_code for i in range(3, 6)] == [200, 200, 200]
