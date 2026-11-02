import io
import struct
import wave

import jiwer
import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("speech.ipynb")


def wav_bytes(samples: np.ndarray, rate: int, fmt: str, extra_chunk: bytes = b"") -> bytes:
    """WAV tự dựng: fmt 'pcm16' hoặc 'float32'; samples dạng (n,) hoặc (n, ch)."""
    x = samples if samples.ndim == 2 else samples[:, None]
    channels = x.shape[1]
    if fmt == "pcm16":
        tag, bits, data = 1, 16, (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    else:
        tag, bits, data = 3, 32, x.astype("<f4").tobytes()
    fmt_chunk = struct.pack("<HHIIHH", tag, channels, rate, rate * channels * bits // 8, channels * bits // 8, bits)
    body = b"WAVE" + b"fmt " + struct.pack("<I", 16) + fmt_chunk + extra_chunk + b"data" + struct.pack("<I", len(data)) + data
    return b"RIFF" + struct.pack("<I", len(body)) + body


# ---------- WER/CER dán từ Basic 01 ----------

def test_asr_metrics_pasted(nb):
    refs = ["Mặt khác, băng và tuyết là hiện tượng.", "Đây là cách rất quan trọng"]
    hyps = ["Mạc khác băng và tiết là hiện tượng", "đây là cách gác quan trọng để"]
    nr, nh = [nb.normalize_vi(x) for x in refs], [nb.normalize_vi(x) for x in hyps]
    assert nb.wer(refs, hyps) == pytest.approx(jiwer.wer(nr, nh))
    assert nb.cer(refs, hyps) == pytest.approx(jiwer.cer(nr, nh))
    assert nb.wer(["xin chào", "a b c d e f g h i"], ["xin chao", "a b c d e f g h i"]) == pytest.approx(1 / 11)


# ---------- WAV ----------

def test_read_wav_float32_mono(nb):
    x = np.linspace(-0.5, 0.5, 1000).astype(np.float32)
    out, rate = nb.read_wav(wav_bytes(x, 16000, "float32"))
    assert rate == 16000 and out.dtype == np.float32 and out.shape == (1000,)
    np.testing.assert_array_equal(out, x)


def test_read_wav_pcm16_matches_stdlib(nb):
    x = (np.sin(np.arange(800) / 10) * 0.7).astype(np.float32)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(22050)
        f.writeframes((x * 32767).astype("<i2").tobytes())
    out, rate = nb.read_wav(buf.getvalue())
    assert rate == 22050
    np.testing.assert_allclose(out, (x * 32767).astype(np.int16) / 32768, atol=1e-7)


def test_read_wav_stereo_and_extra_chunks(nb):
    left = np.full(10, 0.5, np.float32)
    right = np.full(10, -0.25, np.float32)
    odd = b"LIST" + struct.pack("<I", 3) + b"abc" + b"\x00"   # chunk lẻ có byte đệm
    out, rate = nb.read_wav(wav_bytes(np.stack([left, right], 1), 8000, "float32", extra_chunk=odd))
    assert rate == 8000
    np.testing.assert_allclose(out, np.full(10, 0.125))


@pytest.mark.parametrize("data", [b"not a wav file at all", b"RIFF\x04\x00\x00\x00WAVE"])
def test_read_wav_rejects(nb, data):
    with pytest.raises(ValueError):
        nb.read_wav(data)


def test_read_wav_rejects_8bit(nb):
    fmt_chunk = struct.pack("<HHIIHH", 1, 1, 8000, 8000, 1, 8)
    body = b"WAVE" + b"fmt " + struct.pack("<I", 16) + fmt_chunk + b"data" + struct.pack("<I", 4) + b"\x80\x80\x80\x80"
    with pytest.raises(ValueError):
        nb.read_wav(b"RIFF" + struct.pack("<I", len(body)) + body)


def test_pinned_subset(nb):
    rows = [["7", "a.wav", "câu 7"], ["7", "b.wav", "câu 7"], ["3", "c.wav", "câu 3"], ["9", "d.wav", "câu 9"],
            ["3", "e.wav", "câu 3"], ["1", "f.wav", "câu 1"]]
    assert [r[1] for r in nb.pinned_subset(rows, 3)] == ["a.wav", "c.wav", "d.wav"]
    assert [r[1] for r in nb.pinned_subset(rows, 10)] == ["a.wav", "c.wav", "d.wav", "f.wav"]


# ---------- đọc số ----------

@pytest.mark.parametrize("n, words", [
    (0, "không"), (5, "năm"), (10, "mười"), (11, "mười một"), (14, "mười bốn"), (15, "mười lăm"), (20, "hai mươi"),
    (21, "hai mươi mốt"), (24, "hai mươi tư"), (25, "hai mươi lăm"), (100, "một trăm"), (105, "một trăm linh năm"),
    (114, "một trăm mười bốn"), (310, "ba trăm mười"), (1005, "một nghìn không trăm linh năm"),
    (1015, "một nghìn không trăm mười lăm"), (45_000, "bốn mươi lăm nghìn"),
    (1_250_000, "một triệu hai trăm năm mươi nghìn"), (2_000_500, "hai triệu năm trăm"),
    (1_000_001, "một triệu không trăm linh một"), (1_000_000_000, "một tỷ"),
    (-7, "âm bảy"), (2026, "hai nghìn không trăm hai mươi sáu"),
])
def test_read_number_vi(nb, n, words):
    assert nb.read_number_vi(n) == words


def test_read_number_vi_errors(nb):
    with pytest.raises(ValueError):
        nb.read_number_vi(10**12)
    with pytest.raises(TypeError):
        nb.read_number_vi(3.0)
    with pytest.raises(TypeError):
        nb.read_number_vi(True)


def test_normalize_for_tts(nb):
    assert nb.normalize_for_tts("Hôm nay tôi mua cà phê hết 45.000 đồng.") == "Hôm nay tôi mua cà phê hết bốn mươi lăm nghìn đồng."
    assert nb.normalize_for_tts("Tiền điện là 785.000đ.") == "Tiền điện là bảy trăm tám mươi lăm nghìn đồng."
    assert nb.normalize_for_tts("Chuyển 2.500.000 VND, còn 14.500 vnđ") == \
        "Chuyển hai triệu năm trăm nghìn đồng, còn mười bốn nghìn năm trăm đồng"
    assert nb.normalize_for_tts("có 12 tháng") == "có mười hai tháng"
    assert nb.normalize_for_tts("bản 3.5 và 1,5 kg") == "bản 3.5 và 1,5 kg"
    assert nb.normalize_for_tts("không có số") == "không có số"
