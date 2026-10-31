import re
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def prep():
    return ex.module("prepare_data.py")


@pytest.fixture(scope="module")
def app():
    return ex.module("app.py")


def person_mask() -> np.ndarray:
    m = np.zeros((40, 50), dtype=np.uint8)
    m[5:25, 10:20] = 2          # người id 2: dòng 5..24, cột 10..19
    m[30:40, 40:50] = 1         # người id 1 ở góc dưới phải
    return m


# ---------- prepare_data.py ----------

def test_mask_to_yolo_lines(prep):
    lines = prep.mask_to_yolo_lines(person_mask())
    assert len(lines) == 2
    vals = [list(map(float, ln.split())) for ln in lines]
    assert all(v[0] == 0 for v in vals), "một lớp duy nhất: 0 = person"
    np.testing.assert_allclose(vals[0][1:], [45 / 50, 35 / 40, 10 / 50, 10 / 40], atol=1e-6)   # id 1 trước
    np.testing.assert_allclose(vals[1][1:], [15 / 50, 15 / 40, 10 / 50, 20 / 40], atol=1e-6)
    assert prep.mask_to_yolo_lines(np.zeros((5, 5), np.uint8)) == []


def test_mask_to_polygon_lines(prep):
    lines = prep.mask_to_polygon_lines(person_mask())
    assert len(lines) == 2
    for ln, box in zip(lines, [(40, 30, 50, 40), (10, 5, 20, 25)]):
        v = np.array(ln.split()[1:], float).reshape(-1, 2)
        assert ln.split()[0] == "0" and len(v) >= 3
        assert np.all((v >= 0) & (v <= 1))
        xs, ys = v[:, 0] * 50, v[:, 1] * 40
        assert box[0] - 1 <= xs.min() and xs.max() <= box[2] and box[1] - 1 <= ys.min() and ys.max() <= box[3]


def test_split_names(prep):
    names = [f"img{i:03d}" for i in range(50)]
    tr, va = prep.split_names(list(reversed(names)), 0.2, seed=0)
    assert len(va) == 10 and len(tr) == 40
    assert not set(tr) & set(va) and set(tr) | set(va) == set(names)
    assert tr == sorted(tr) and va == sorted(va)
    assert prep.split_names(names, 0.2, seed=0) == (tr, va)
    assert prep.split_names(names, 0.2, seed=1)[1] != va


def fake_pennfudan(root: Path, n: int = 5) -> Path:
    pf = root / "PennFudanPed"
    (pf / "PNGImages").mkdir(parents=True)
    (pf / "PedMasks").mkdir()
    rng = np.random.default_rng(0)
    for i in range(n):
        Image.fromarray(rng.integers(0, 255, (40, 50, 3), dtype=np.uint8)).save(pf / "PNGImages" / f"Ped{i:05d}.png")
        Image.fromarray(person_mask()).save(pf / "PedMasks" / f"Ped{i:05d}_mask.png")
    return pf


def test_write_yolo_dataset(prep, tmp_path):
    pf = fake_pennfudan(tmp_path)
    yaml = Path(prep.write_yolo_dataset(pf, tmp_path / "yolo", val_frac=0.4, seed=0))
    assert yaml.name == "data.yaml" and yaml.exists()
    text = yaml.read_text()
    assert re.search(r"^train:\s*images/train\s*$", text, re.M) and re.search(r"^val:\s*images/val\s*$", text, re.M)
    assert "person" in text and str((tmp_path / "yolo").resolve()) in text
    out = tmp_path / "yolo"
    tr = sorted(p.stem for p in (out / "images" / "train").iterdir())
    va = sorted(p.stem for p in (out / "images" / "val").iterdir())
    assert len(tr) == 3 and len(va) == 2 and not set(tr) & set(va)
    for split, names in (("train", tr), ("val", va)):
        for name in names:
            assert cv2.imread(str(out / "images" / split / f"{name}.png")) is not None
            lines = (out / "labels" / split / f"{name}.txt").read_text().split("\n")
            assert [ln for ln in lines if ln.strip()] == prep.mask_to_yolo_lines(person_mask())
    seg = Path(prep.write_yolo_dataset(pf, tmp_path / "seg", val_frac=0.4, seed=0, task="segment"))
    first = next((seg.parent / "labels" / "train").iterdir()).read_text().split("\n")[0]
    assert len(first.split()) >= 7, "task segment: nhãn là đa giác"


# ---------- app.py ----------

def test_parse_source(app):
    assert app.parse_source("0") == 0 and app.parse_source("2") == 2
    assert app.parse_source("video.mp4") == "video.mp4"
    assert app.parse_source("/tmp/frames") == "/tmp/frames"


def test_draw_detections(app):
    frame = np.zeros((60, 80, 3), np.uint8)
    out = app.draw_detections(frame, np.array([[10.4, 20.0, 50.0, 55.0]]), np.array([0.87]), np.array([0]),
                              {0: "person"}, fps=12.3)
    assert out is frame, "vẽ tại chỗ và trả lại chính frame"
    assert out.shape == (60, 80, 3) and out.dtype == np.uint8
    assert out[30, 10].any() and out[30, 50].any(), "có viền hộp ở cạnh trái và phải"
    assert not out[40, 30].any(), "trong lòng hộp không bị tô"
    assert out[5:25, 0:60].any(), "có chữ FPS ở góc trên trái"
    same = np.zeros((60, 80, 3), np.uint8)
    app.draw_detections(same, np.zeros((0, 4)), np.zeros(0), np.zeros(0, int), {0: "person"})
    assert not same.any(), "không có hộp, không có fps: không vẽ gì"
    # hộp tràn ra ngoài ảnh không làm lỗi
    app.draw_detections(np.zeros((60, 80, 3), np.uint8), np.array([[-5, -5, 200, 200]]), np.array([0.5]),
                        np.array([0]), {0: "person"})


def test_fps_meter(app):
    t = iter([0.0, 0.1, 0.2, 0.25, 0.30])
    m = app.FpsMeter(alpha=0.5, clock=lambda: next(t))
    assert m.tick() == 0.0
    assert m.tick() == pytest.approx(10.0)
    assert m.tick() == pytest.approx(10.0)
    assert m.tick() == pytest.approx(0.5 * 20 + 0.5 * 10)
    assert m.tick() == pytest.approx(0.5 * 20 + 0.5 * 15)


def write_video(path: Path, n: int, size=(64, 48)) -> None:
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, size)
    for i in range(n):
        frame = np.full((size[1], size[0], 3), 40 + 10 * i, np.uint8)
        w.write(frame)
    w.release()


def fake_detect(frame):
    return np.array([[5.0, 5.0, 30.0, 40.0]]), np.array([0.9]), np.array([0])


def test_run_on_video_file(app, tmp_path):
    src = tmp_path / "in.avi"
    write_video(src, 12)
    out = tmp_path / "out.mp4"
    seen = []
    stats = app.run(str(src), fake_detect, {0: "person"}, out_path=str(out), on_frame=seen.append)
    assert stats["frames"] == 12 and stats["detections"] == 12 and stats["fps"] > 0
    assert len(seen) == 12 and seen[0].shape == (48, 64, 3)
    cap = cv2.VideoCapture(str(out))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    ok, first = cap.read()
    cap.release()
    assert n == 12 and ok and first.shape == (48, 64, 3)
    assert app.run(str(src), fake_detect, {0: "person"}, max_frames=5)["frames"] == 5


def test_run_on_image_folder(app, tmp_path):
    for i in range(3):
        cv2.imwrite(str(tmp_path / f"f{i}.png"), np.full((30, 40, 3), 100, np.uint8))
    (tmp_path / "notes.txt").write_text("không phải ảnh")
    stats = app.run(str(tmp_path), fake_detect, {0: "person"})
    assert stats["frames"] == 3


def test_run_bad_source(app, tmp_path):
    with pytest.raises(RuntimeError) as err:
        app.run(str(tmp_path / "missing.mp4"), fake_detect, {0: "person"})
    assert not isinstance(err.value, NotImplementedError), "nguồn không mở được: RuntimeError có lời nhắn rõ"


def test_app_does_not_import_ultralytics_at_top(app):
    src = ex.read("app.py")
    top = [ln for ln in src.splitlines() if ln.startswith(("import ", "from "))]
    assert not any("ultralytics" in ln for ln in top), "import ultralytics trong make_detector để app nhẹ khi test"


# ---------- báo cáo ----------

def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 600, "báo cáo portfolio: ít nhất 600 từ"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần ít nhất một bảng (zero-shot so với fine-tune)"
    images = re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", doc)
    assert images, "chèn hình (đường cong train, ảnh có hộp dự đoán), vd. ![](val_pred.jpg)"
    for img in images:
        if not img.startswith("http"):
            assert (ex.path("REPORT.md").parent / img).exists(), f"không thấy tệp hình {img}"
