import base64

import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def m():
    return ex.module("media.py")


def tone(freq, sr, seconds=1.0):
    t = np.arange(int(sr * seconds)) / sr
    return (0.8 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


# ---------- audio ----------

def test_to_mono_float32_scaling(m):
    out = m.to_mono_float32(np.array([-32768, 0, 16384, 32767], dtype=np.int16))
    assert out.dtype == np.float32 and out.shape == (4,)
    np.testing.assert_allclose(out, [-1.0, 0.0, 0.5, 32767 / 32768], atol=1e-7)
    np.testing.assert_allclose(m.to_mono_float32(np.array([0, 128, 255], dtype=np.uint8)), [-1.0, 0.0, 127 / 128])
    np.testing.assert_allclose(m.to_mono_float32(np.array([-2**31, 2**30], dtype=np.int32)), [-1.0, 0.5])
    f = m.to_mono_float32(np.array([0.25, -0.5], dtype=np.float64))
    assert f.dtype == np.float32
    np.testing.assert_allclose(f, [0.25, -0.5])


def test_to_mono_float32_downmix(m):
    stereo = np.array([[1000, 3000], [-2000, 2000], [0, 0]], dtype=np.int16)
    out = m.to_mono_float32(stereo)
    assert out.shape == (3,) and out.dtype == np.float32
    np.testing.assert_allclose(out, np.array([2000, 0, 0]) / 32768, atol=1e-7)
    with pytest.raises(ValueError):
        m.to_mono_float32(np.zeros((2, 2, 2), dtype=np.float32))


@pytest.mark.parametrize("sr_in, sr_out", [(44100, 16000), (48000, 16000), (8000, 16000), (22050, 16000)])
def test_resample_length_and_dtype(m, sr_in, sr_out):
    x = tone(440, sr_in)
    y = m.resample(x, sr_in, sr_out)
    assert y.dtype == np.float32 and y.ndim == 1
    assert abs(len(y) - len(x) * sr_out / sr_in) <= 1


def test_resample_keeps_in_band_tone(m):
    y = m.resample(tone(440, 44100), 44100, 16000)
    ideal = tone(440, 16000)[: len(y)]
    middle = slice(1000, len(y) - 1000)
    assert np.max(np.abs(y[middle] - ideal[middle])) < 0.02


def test_resample_removes_tone_above_new_nyquist(m):
    # 10 kHz không biểu diễn được ở 16 kHz (Nyquist 8 kHz): phải bị lọc đi, không được "gập" thành 6 kHz
    y = m.resample(tone(10_000, 44100), 44100, 16000)
    rms = float(np.sqrt(np.mean(y[1000:-1000] ** 2)))
    assert rms < 0.05, f"RMS sau resample {rms:.3f}: tín hiệu trên Nyquist mới không bị lọc"


def test_resample_identity_and_errors(m):
    x = tone(440, 16000, 0.1)
    y = m.resample(x, 16000, 16000)
    np.testing.assert_array_equal(y, x)
    assert y is not x
    with pytest.raises(ValueError):
        m.resample(x, 0, 16000)


# ---------- video ----------

def test_sample_frame_indices_uniform(m):
    assert m.sample_frame_indices(300, 10, num=4) == [37, 112, 187, 262]
    assert m.sample_frame_indices(100, 25, num=1) == [50]
    assert m.sample_frame_indices(5, 25, num=8) == [0, 1, 2, 3, 4]
    idx = m.sample_frame_indices(1000, 30, num=16)
    assert len(idx) == 16 and idx == sorted(idx) and idx[0] > 0 and idx[-1] < 999


def test_sample_frame_indices_every(m):
    assert m.sample_frame_indices(300, 10, every_s=5) == [0, 50, 100, 150, 200, 250]
    assert m.sample_frame_indices(25, 10, every_s=1) == [0, 10, 20]
    assert m.sample_frame_indices(300, 29.97, every_s=2.5) == [0, 74, 149, 224, 299]  # clip dài 10.01 s nên t = 10 s vẫn nằm trong
    assert m.sample_frame_indices(20, 10, every_s=0.01) == list(range(20)), "không trùng chỉ số"


def test_sample_frame_indices_errors(m):
    assert m.sample_frame_indices(0, 10, num=4) == []
    with pytest.raises(ValueError):
        m.sample_frame_indices(100, 10)
    with pytest.raises(ValueError):
        m.sample_frame_indices(100, 10, num=4, every_s=1)


# ---------- token ảnh ----------
# Số đo bằng prompt_eval_count của Ollama 0.13.5 (trừ phần chữ của prompt), qwen3-vl:2b
QWEN3_VL = [((64, 64), 64), ((224, 224), 64), ((448, 448), 196), ((512, 256), 128), ((640, 480), 300),
            ((1000, 1000), 961), ((1280, 960), 1200), ((2000, 1500), 2028), ((2560, 1440), 1980), ((3000, 3000), 2025)]
# qwen2.5vl:3b: patch 14, gộp 2x2 nên factor 28
QWEN25_VL = [((224, 224), 64), ((448, 448), 256), ((448, 224), 128), ((640, 480), 391), ((1000, 1000), 1296),
             ((1280, 960), 1564)]


@pytest.mark.parametrize("size, tokens", QWEN3_VL)
def test_vlm_image_tokens_qwen3(m, size, tokens):
    assert m.vlm_image_tokens(*size) == tokens
    assert m.vlm_image_tokens(size[1], size[0]) == tokens


@pytest.mark.parametrize("size, tokens", QWEN25_VL)
def test_vlm_image_tokens_qwen25(m, size, tokens):
    assert m.vlm_image_tokens(*size, factor=28, min_pixels=56 * 56, max_pixels=12_845_056) == tokens


def test_vlm_image_tokens_extremes(m):
    assert m.vlm_image_tokens(10, 10) == 64
    assert m.vlm_image_tokens(8000, 6000) <= 2048
    with pytest.raises(ValueError):
        m.vlm_image_tokens(10_000, 20)


# ---------- message đa phương thức ----------

def test_lc_user_message_blocks(m):
    from langchain_core.messages import HumanMessage

    msg = m.lc_user_message("Tổng tiền bao nhiêu?", images=[(b"\x89PNG-1", "image/png"), (b"\xff\xd8-2", "image/jpeg")],
                            audio=[(b"RIFF-3", "audio/wav")])
    assert isinstance(msg, HumanMessage)
    blocks = msg.content
    assert [b["type"] for b in blocks] == ["text", "image", "image", "audio"]
    assert blocks[0]["text"] == "Tổng tiền bao nhiêu?"
    assert base64.b64decode(blocks[1]["base64"]) == b"\x89PNG-1" and blocks[1]["mime_type"] == "image/png"
    assert base64.b64decode(blocks[2]["base64"]) == b"\xff\xd8-2" and blocks[2]["mime_type"] == "image/jpeg"
    assert base64.b64decode(blocks[3]["base64"]) == b"RIFF-3" and blocks[3]["mime_type"] == "audio/wav"
    assert m.lc_user_message("chỉ chữ").content == [{"type": "text", "text": "chỉ chữ"}]


def test_lc_user_message_converts_for_providers(m):
    from langchain_core.messages.utils import convert_to_openai_messages
    from langchain_ollama import ChatOllama

    msg = m.lc_user_message("Đọc hoá đơn", images=[(b"img-bytes", "image/jpeg")])
    openai = convert_to_openai_messages([msg])[0]["content"]
    assert openai[1] == {"type": "image_url",
                         "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(b"img-bytes").decode()}}
    ollama = ChatOllama(model="offline")._convert_messages_to_ollama_messages([msg])[0]
    assert ollama["images"] == [base64.b64encode(b"img-bytes").decode()]
    assert ollama["content"].strip() == "Đọc hoá đơn"


def test_lc_user_message_rejects_wrong_mime(m):
    with pytest.raises(ValueError):
        m.lc_user_message("x", images=[(b"abc", "audio/wav")])
    with pytest.raises(ValueError):
        m.lc_user_message("x", audio=[(b"abc", "image/png")])
