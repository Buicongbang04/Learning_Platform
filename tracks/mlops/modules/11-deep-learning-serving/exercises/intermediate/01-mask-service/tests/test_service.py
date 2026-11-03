import io

import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient
from PIL import Image

import segkit
from testkit import Exercise

ex = Exercise(__file__)
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
VERSION = "seg-tiny-3"


class Normalized(torch.nn.Module):
    def __init__(self, inner):
        super().__init__()
        self.inner = inner
        self.register_buffer("mean", torch.from_numpy(MEAN).view(1, 3, 1, 1))
        self.register_buffer("std", torch.from_numpy(STD).view(1, 3, 1, 1))

    def forward(self, x):
        return self.inner(x * self.std + self.mean)


def model_file(tmp_path, trained=False):
    inner = segkit.trained_model() if trained else segkit.tiny_model(seed=7)
    return segkit.export(Normalized(inner).eval(), tmp_path / "seg.onnx")


def png(image, fmt="PNG"):
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


def post(client, data, name="pet.png"):
    return client.post("/segment", files={"file": (name, data, "application/octet-stream")})


def expected_mask(path, image):
    resized = image.convert("RGB").resize((64, 64), Image.BILINEAR)
    x = ((np.asarray(resized, dtype=np.float32) / 255.0 - MEAN) / STD).transpose(2, 0, 1)[None].astype(np.float32)
    logits = segkit.ort_session(path).run(None, {"pixel_values": np.ascontiguousarray(x)})[0]
    mask = Image.fromarray(logits[0].argmax(0).astype(np.uint8), mode="L").resize(image.size, Image.NEAREST)
    return np.asarray(mask)


def noise_image(width, height, mode="RGB", seed=0):
    rng = np.random.default_rng(seed)
    channels = {"RGB": 3, "RGBA": 4, "L": 1}[mode]
    pixels = rng.integers(0, 256, (height, width, channels), dtype=np.uint8)
    return Image.fromarray(pixels[..., 0] if channels == 1 else pixels, mode=mode)


def test_preprocess_shape_dtype_and_normalization():
    service = ex.module("service.py")
    x = service.preprocess(Image.new("RGBA", (300, 200), (255, 0, 128, 10)))
    assert x.shape == (1, 3, 64, 64) and x.dtype == np.float32
    assert x[0, :, 10, 10] == pytest.approx((np.array([1.0, 0.0, 128 / 255]) - MEAN) / STD, abs=1e-5)


def test_postprocess_returns_png_in_original_size():
    service = ex.module("service.py")
    logits = np.zeros((1, 3, 64, 64), np.float32)
    logits[0, 1, :32] = 5
    logits[0, 2, 32:, :16] = 5
    mask = Image.open(io.BytesIO(service.postprocess(logits, (128, 100))))
    assert mask.format == "PNG" and mask.mode == "L" and mask.size == (128, 100)
    values = np.asarray(mask)
    assert values[0, 0] == 1 and values[-1, 0] == 2 and values[-1, -1] == 0
    assert set(np.unique(values)) == {0, 1, 2}


def test_segment_returns_exact_mask_and_version(tmp_path):
    service = ex.module("service.py")
    path = model_file(tmp_path)
    image = noise_image(150, 90)
    with TestClient(service.create_app(path, VERSION)) as client:
        response = post(client, png(image))
        assert response.status_code == 200, response.text
        assert response.headers["content-type"] == "image/png"
        assert response.headers["x-model-version"] == VERSION
        assert client.get("/healthz").json() == {"status": "ok", "model_version": VERSION}
    mask = Image.open(io.BytesIO(response.content))
    assert mask.mode == "L" and mask.size == (150, 90)
    np.testing.assert_array_equal(np.asarray(mask), expected_mask(path, image))


@pytest.mark.parametrize("mode,fmt", [("L", "PNG"), ("RGBA", "PNG"), ("RGB", "JPEG")])
def test_accepts_grayscale_rgba_and_jpeg(tmp_path, mode, fmt):
    service = ex.module("service.py")
    with TestClient(service.create_app(model_file(tmp_path), VERSION)) as client:
        response = post(client, png(noise_image(64, 48, mode), fmt))
    assert response.status_code == 200, response.text
    assert Image.open(io.BytesIO(response.content)).size == (64, 48)


def test_rejects_bad_input(tmp_path):
    service = ex.module("service.py")
    with TestClient(service.create_app(model_file(tmp_path), VERSION)) as client:
        assert post(client, b"not an image at all").status_code == 400
        assert post(client, png(noise_image(20, 200))).status_code == 422
        assert post(client, png(noise_image(1100, 600))).status_code == 422
        assert post(client, png(noise_image(1024, 32))).status_code == 200
        assert post(client, b"\x89PNG" + b"0" * (10 * 1024 * 1024 + 10)).status_code == 413
        assert client.post("/segment").status_code == 422


def test_session_is_created_once(tmp_path, monkeypatch):
    service = ex.module("service.py")
    calls = []
    real = service.ort.InferenceSession
    monkeypatch.setattr(service.ort, "InferenceSession", lambda *a, **k: calls.append(1) or real(*a, **k))
    with TestClient(service.create_app(model_file(tmp_path), VERSION)) as client:
        for seed in range(4):
            assert post(client, png(noise_image(80, 80, seed=seed))).status_code == 200
    assert calls == [1]


def test_trained_model_segments_the_pet(tmp_path):
    service = ex.module("service.py")
    images, masks = segkit.synthetic(6, seed=42)
    with TestClient(service.create_app(model_file(tmp_path, trained=True), VERSION)) as client:
        scores = []
        for image, mask in zip(images, masks):
            pil = Image.fromarray((image.transpose(1, 2, 0) * 255).round().astype(np.uint8)).resize((200, 150), Image.BILINEAR)
            truth = np.asarray(Image.fromarray(mask.astype(np.uint8)).resize((200, 150), Image.NEAREST))
            pred = np.asarray(Image.open(io.BytesIO(post(client, png(pil)).content)))
            scores.append(np.logical_and(pred == 1, truth == 1).sum() / np.logical_or(pred == 1, truth == 1).sum())
    assert np.mean(scores) > 0.8, f"IoU lớp thú cưng {np.mean(scores):.2f}"
