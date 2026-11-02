import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("video.ipynb")


def test_clip_generator_is_intact(nb):
    spec = nb.make_spec(3)
    assert set(spec["answers"]) == {"scene_count", "first_shape", "last_number", "has_red_triangle", "ball_direction",
                                    "flash_count"}
    assert spec["answers"]["scene_count"] == len(spec["scenes"])
    assert abs(spec["scenes"][-1]["end"] - spec["seconds"]) < 1e-6


def test_read_frames_order(nb, tmp_path):
    path = str(tmp_path / "tiny.mp4")
    import imageio.v2 as imageio

    with imageio.get_writer(path, fps=5, codec="libx264", quality=8, macro_block_size=8) as w:
        for k in range(10):
            w.append_data(np.full((32, 48, 3), k * 25, np.uint8))
    frames = nb.read_frames(path, [7, 2, 2])
    assert len(frames) == 3
    assert all(f.dtype == np.uint8 and f.shape == (32, 48, 3) for f in frames)
    assert abs(float(frames[0].mean()) - 175) < 8 and abs(float(frames[1].mean()) - 50) < 8
    np.testing.assert_array_equal(frames[1], frames[2])


def test_scene_change_indices(nb):
    gray = np.zeros((10, 4, 4), np.uint8)
    gray[3:] = 200          # đổi cảnh ở frame 3
    gray[6] = 255           # frame 6 loé: khác frame 5 và frame 7
    gray[8:] = 190          # đổi nhẹ: dưới ngưỡng
    assert nb.scene_change_indices(gray, threshold=20.0) == [0, 3, 6, 7]
    assert nb.scene_change_indices(gray, threshold=5.0) == [0, 3, 6, 7, 8]
    equal = np.array([np.zeros((2, 2)), np.full((2, 2), 20)], np.uint8)
    assert nb.scene_change_indices(equal, threshold=20.0) == [0], "chỉ tính khi lớn hơn hẳn ngưỡng"


def test_scene_change_uses_signed_difference(nb):
    gray = np.array([np.full((2, 2), 200), np.full((2, 2), 10), np.full((2, 2), 10)], np.uint8)
    assert nb.scene_change_indices(gray, threshold=50.0) == [0, 1], "200 -> 10 là thay đổi lớn, không được tràn số uint8"


def test_segment_middles(nb):
    assert nb.segment_middles([0, 3, 6, 7], 10) == [1, 4, 6, 8]
    assert nb.segment_middles([0], 300) == [149]
    assert nb.segment_middles([0, 1], 2) == [0, 1]


def test_tile_grid(nb):
    frames = [np.full((2, 3, 3), k + 1, np.uint8) for k in range(5)]
    grid = nb.tile_grid(frames, cols=2)
    assert grid.shape == (6, 6, 3) and grid.dtype == np.uint8
    assert grid[0, 0, 0] == 1 and grid[0, 3, 0] == 2, "frame 1 nằm bên phải frame 0"
    assert grid[2, 0, 0] == 3 and grid[4, 0, 0] == 5
    assert (grid[4:, 3:] == 0).all(), "ô thừa màu đen"
    assert nb.tile_grid(frames[:4], cols=4).shape == (2, 12, 3)


def test_video_messages(nb):
    msgs = nb.video_messages("Q?", ["a", "b", "c"], [0.5, 1.5, 12.25])
    assert msgs == [
        {"role": "user", "content": "Q?\nThe images are frames of one video in chronological order, taken at: 0.5s, 1.5s, 12.2s.",
         "images": ["a", "b", "c"]},
        {"role": "assistant", "content": "{"},
    ]


def test_score_answers(nb):
    truth = {"scene_count": 5, "first_shape": "circle", "has_red_triangle": True, "ball_direction": "left_to_right",
             "flash_count": 0}
    pred = {"scene_count": "5", "first_shape": " Circle ", "has_red_triangle": "yes", "ball_direction": "right_to_left",
            "flash_count": False}
    assert nb.score_answers(pred, truth) == {"scene_count": True, "first_shape": True, "has_red_triangle": True,
                                             "ball_direction": False, "flash_count": False}
    assert nb.score_answers({"has_red_triangle": 1, "scene_count": 5.0}, {"has_red_triangle": True, "scene_count": 5}) == \
        {"has_red_triangle": False, "scene_count": True}
    assert nb.score_answers({"scene_count": "năm"}, {"scene_count": 5}) == {"scene_count": False}
    assert nb.score_answers(None, {"flash_count": 2}) == {"flash_count": False}
