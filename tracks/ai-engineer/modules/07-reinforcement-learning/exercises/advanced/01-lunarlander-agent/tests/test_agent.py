import re
from types import SimpleNamespace

import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("agent.ipynb")


class Corridor:
    """5 ô, xuất phát ô 0, action 1 sang phải; tới ô 4 thì kết thúc. Reward = số ô đã đi (để return phân biệt được)."""

    def __init__(self, render_mode=None):
        self.observation_space = SimpleNamespace(shape=(1,))
        self.action_space = SimpleNamespace(n=2)
        self.render_mode = render_mode
        self.seeds = []

    def reset(self, seed=None):
        self.seeds.append(seed)
        self.pos = 0 if seed is None else seed % 2
        return np.array([self.pos], dtype=np.float32), {}

    def step(self, action):
        self.pos = min(self.pos + 1, 4) if action == 1 else max(self.pos - 1, 0)
        return np.array([self.pos], dtype=np.float32), float(self.pos), self.pos == 4, False, {}

    def render(self):
        frame = np.zeros((32, 48, 3), dtype=np.uint8)
        frame[:, self.pos * 8:(self.pos + 1) * 8] = 255
        return frame

    def close(self):
        pass


def test_evaluate_policy(nb):
    made = []

    def make():
        made.append(Corridor())
        return made[-1]

    out = nb.evaluate_policy(lambda o: 1, make, 4, 10)
    assert isinstance(out, np.ndarray) and out.shape == (4,)
    np.testing.assert_allclose(out, [1 + 2 + 3 + 4, 2 + 3 + 4, 10, 9])
    assert len(made) == 1 and made[0].seeds == [10, 11, 12, 13], "một env, episode i reset với seed + i"


@pytest.mark.parametrize("suffix", [".mp4", ".gif"])
def test_record_video(nb, tmp_path, suffix):
    imageio = pytest.importorskip("imageio")
    path = tmp_path / "sub" / f"run{suffix}"
    info = nb.record_video(lambda o: 1, lambda: Corridor(render_mode="rgb_array"), path, seed=0, fps=10)
    assert info == {"frames": 5, "steps": 4, "return": 10.0}
    assert path.exists() and path.stat().st_size > 0, "tạo thư mục cha nếu chưa có rồi ghi video"
    frames = list(imageio.v3.imiter(path))
    assert len(frames) == 5, "một khung sau reset, một khung sau mỗi step"
    assert frames[0].shape[:2] == (32, 48)


def test_curve_on_grid(nb):
    end_steps = [100, 250, 300, 900, 1000]
    returns = [1.0, 2.0, 4.0, 8.0, 16.0]
    out = nb.curve_on_grid(end_steps, returns, [300, 600, 1000], 500)
    assert out[0] == pytest.approx((1 + 2 + 4) / 3)
    assert out[1] == pytest.approx((2 + 4) / 2), "(100, 600] gồm 250 và 300; 100 không nằm trong (100, 600]"
    assert out[2] == pytest.approx((8 + 16) / 2)
    gap = nb.curve_on_grid(end_steps, returns, [700], 100)
    assert np.isnan(gap[0])


def test_interquartile_mean(nb):
    assert nb.interquartile_mean([1, 2, 3, 4, 100, -100, 5, 6]) == pytest.approx((2 + 3 + 4 + 5) / 4)
    assert nb.interquartile_mean([1, 2, 3, 4, 5]) == pytest.approx((2 + 3 + 4) / 3)
    rng = np.random.default_rng(0)
    x = rng.normal(size=101)
    s = np.sort(x)
    assert nb.interquartile_mean(x) == pytest.approx(s[25:76].mean())
    assert isinstance(nb.interquartile_mean([1.0, 2.0]), float)


def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 600, "báo cáo portfolio: ít nhất 600 từ"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần ít nhất một bảng kết quả"
    assert re.search(r"seed", doc, re.I), "báo cáo phải nói rõ các seed"
    report_dir = ex.path("REPORT.md").parent
    for img in re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", doc):
        if not img.startswith("http"):
            assert (report_dir / img).exists(), f"không thấy tệp hình {img}"
    videos = re.findall(r"\(([^)\s]+\.(?:mp4|gif|webm))\)", doc)
    assert videos, "báo cáo phải link tới video agent chơi (tệp .mp4/.gif cục bộ hoặc link http)"
    for v in videos:
        if not v.startswith("http"):
            assert (report_dir / v).exists(), f"không thấy tệp video {v}"
