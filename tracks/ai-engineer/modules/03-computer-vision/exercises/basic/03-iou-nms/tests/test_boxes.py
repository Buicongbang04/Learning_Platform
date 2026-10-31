import time

import numpy as np
import pytest
import torch
from torchvision import ops

from testkit import Exercise

ex = Exercise(__file__)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def B():
    return ex.module("boxes.py")


def random_boxes(n: int, seed: int, size: float = 100.0) -> np.ndarray:
    """Hộp xyxy ngẫu nhiên trong ảnh size x size, nhiều hộp chồng nhau."""
    rng = np.random.default_rng(seed)
    xy = rng.uniform(0, size * 0.8, (n, 2))
    wh = rng.uniform(5, size * 0.3, (n, 2))
    return np.concatenate([xy, xy + wh], axis=1)


def test_only_numpy():
    src = ex.read("boxes.py")
    assert "import torch" not in src and "from torch" not in src, "chỉ dùng numpy trong boxes.py"


def test_format_roundtrip(B):
    b = random_boxes(20, 0)
    c = B.xyxy_to_cxcywh(b)
    np.testing.assert_allclose(c, ops.box_convert(torch.tensor(b), "xyxy", "cxcywh").numpy(), atol=1e-12)
    np.testing.assert_allclose(B.cxcywh_to_xyxy(c), b, atol=1e-12)
    np.testing.assert_allclose(B.cxcywh_to_xyxy(np.array([[50.0, 40.0, 20.0, 10.0]])), [[40, 35, 60, 45]])


def test_box_area(B):
    b = np.array([[0, 0, 4, 3], [2, 2, 2, 5], [5, 5, 1, 1]], dtype=float)
    np.testing.assert_allclose(B.box_area(b), [12, 0, 0])


def test_iou_matches_torchvision(B):
    a, b = random_boxes(30, 1), random_boxes(17, 2)
    iou = B.box_iou(a, b)
    assert iou.shape == (30, 17)
    np.testing.assert_allclose(iou, ops.box_iou(torch.tensor(a), torch.tensor(b)).numpy(), atol=1e-12)


def test_iou_known_values(B):
    a = np.array([[0, 0, 2, 2]], dtype=float)
    b = np.array([[1, 1, 3, 3], [0, 0, 2, 2], [2, 0, 4, 2], [5, 5, 6, 6], [0, 0, 1, 1]], dtype=float)
    np.testing.assert_allclose(B.box_iou(a, b)[0], [1 / 7, 1, 0, 0, 0.25], atol=1e-12)


def test_iou_degenerate_is_zero_not_nan(B):
    z = np.array([[3, 3, 3, 3]], dtype=float)
    with np.errstate(all="raise"):
        assert B.box_iou(z, z)[0, 0] == 0.0


def test_iou_vectorized(B):
    # 2.25 triệu cặp: bản broadcast khoảng 0.2 s, vòng lặp Python qua từng cặp vài giây trở lên
    a, b = random_boxes(1500, 3), random_boxes(1500, 4)
    start = time.perf_counter()
    B.box_iou(a, b)
    assert time.perf_counter() - start < 3.0, "box_iou 1500 x 1500 phải dưới 3 s: còn vòng lặp Python qua từng cặp?"


@pytest.mark.parametrize("seed,thr", [(5, 0.5), (6, 0.3), (7, 0.7), (8, 0.0), (9, 1.0)])
def test_nms_matches_torchvision(B, seed, thr):
    boxes = random_boxes(200, seed)
    scores = np.random.default_rng(seed + 100).permutation(200) / 200.0   # không có score bằng nhau
    keep = B.nms(boxes, scores, thr)
    assert keep.dtype == np.int64
    ref = ops.nms(torch.tensor(boxes), torch.tensor(scores), thr).numpy()
    np.testing.assert_array_equal(keep, ref)


def test_nms_threshold_is_strict(B):
    boxes = np.array([[0, 0, 2, 1], [0, 0, 1, 1]], dtype=float)   # IoU đúng bằng 0.5
    scores = np.array([0.9, 0.8])
    np.testing.assert_array_equal(B.nms(boxes, scores, 0.5), [0, 1])
    np.testing.assert_array_equal(B.nms(boxes, scores, 0.49), [0])


def test_nms_empty(B):
    keep = B.nms(np.zeros((0, 4)), np.zeros(0), 0.5)
    assert keep.shape == (0,) and keep.dtype == np.int64


def test_nms_is_not_one_pass(B):
    # A > B > C theo score; A loại B, còn C chỉ chồng B: C phải được giữ.
    # Cách sai: so mỗi hộp với MỌI hộp score cao hơn (kể cả hộp đã bị loại) sẽ loại cả C.
    boxes = np.array([[0, 0, 10, 10], [5, 0, 15, 10], [10, 0, 20, 10]], dtype=float)
    scores = np.array([0.9, 0.8, 0.7])
    np.testing.assert_array_equal(B.nms(boxes, scores, 0.3), [0, 2])


@pytest.mark.parametrize("seed", [10, 11, 12])
def test_batched_nms_matches_torchvision(B, seed):
    rng = np.random.default_rng(seed)
    boxes = random_boxes(150, seed)
    scores = rng.permutation(150) / 150.0
    classes = rng.integers(0, 4, 150)
    keep = B.batched_nms(boxes, scores, classes, 0.5)
    ref = ops.batched_nms(torch.tensor(boxes), torch.tensor(scores), torch.tensor(classes), 0.5).numpy()
    np.testing.assert_array_equal(keep, ref)


def test_batched_nms_classes_do_not_suppress_each_other(B):
    boxes = np.array([[0, 0, 10, 10], [0, 0, 10, 10]], dtype=float)
    keep = B.batched_nms(boxes, np.array([0.9, 0.8]), np.array([0, 1]), 0.5)
    np.testing.assert_array_equal(keep, [0, 1])
