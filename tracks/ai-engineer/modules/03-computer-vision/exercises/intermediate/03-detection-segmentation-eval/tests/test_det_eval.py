import math

import numpy as np
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("det_eval.ipynb")


# ---------- 1. mask → hộp ----------

def test_instance_masks(nb):
    m = np.zeros((4, 6), dtype=np.uint8)
    m[0, 0:2] = 3
    m[2:4, 4] = 1
    out = nb.instance_masks(m)
    assert out.shape == (2, 4, 6) and out.dtype == bool
    assert out[0].sum() == 2 and out[0][2, 4], "thứ tự theo id tăng dần: id 1 trước id 3"
    assert out[1][0, 0] and out[1][0, 1]
    assert nb.instance_masks(np.zeros((3, 3), np.uint8)).shape == (0, 3, 3)


def test_masks_to_boxes_pixel_edges(nb):
    m = np.zeros((2, 10, 12), dtype=bool)
    m[0, 2:5, 3:6] = True            # dòng 2..4, cột 3..5
    m[1, 9, 11] = True               # một pixel ở góc
    boxes = nb.masks_to_boxes(m)
    assert boxes.shape == (2, 4)
    np.testing.assert_array_equal(boxes, [[3, 2, 6, 5], [11, 9, 12, 10]])


# ---------- 2. ghép prediction ----------

GT = np.array([[0, 0, 10, 10], [20, 0, 30, 10]], dtype=float)


def test_match_duplicates_and_threshold(nb):
    preds = np.array([[0, 0, 10, 10], [0, 0, 10, 9], [20, 0, 30, 10], [40, 40, 50, 50]], dtype=float)
    scores = np.array([0.6, 0.9, 0.5, 0.95])
    tp = nb.match_image(preds, scores, GT, 0.5)
    assert tp.dtype == bool
    # [0,0,10,9] score 0.9 chiếm người 1 trước; [0,0,10,10] score 0.6 là trùng lặp → FP
    np.testing.assert_array_equal(tp, [False, True, True, False])


def test_match_inclusive_threshold_and_best_iou(nb):
    gt = np.array([[0, 0, 10, 10], [5, 0, 15, 10]], dtype=float)
    # P1 (score cao): IoU 0.43 với người 0, 0.82 với người 1; P2: IoU 1 với người 0.
    # Ghép đúng: P1 → người 1, P2 → người 0. Ghép với người ĐẦU TIÊN vượt ngưỡng thì P1 chiếm người 0, P2 thành FP.
    preds = np.array([[4, 0, 14, 10], [0, 0, 10, 10]], dtype=float)
    tp = nb.match_image(preds, np.array([0.9, 0.8]), gt, 0.4)
    assert tp.tolist() == [True, True], "ghép với ground truth chưa bị chiếm có IoU LỚN NHẤT"
    half = np.array([[0, 0, 10, 5]], dtype=float)                      # IoU đúng 0.5 với người 0
    assert nb.match_image(half, np.array([1.0]), gt[:1], 0.5).tolist() == [True], "IoU >= ngưỡng là TP"


def test_match_greedy_by_score_takes_best_free_gt(nb):
    # pred A (score cao) chồng cả hai người, gần người 2 hơn; pred B chỉ khớp người 2.
    gt = np.array([[0, 0, 10, 10], [6, 0, 16, 10]], dtype=float)
    preds = np.array([[5, 0, 15, 10], [6, 0, 16, 10]], dtype=float)
    tp = nb.match_image(preds, np.array([0.9, 0.8]), gt, 0.5)
    np.testing.assert_array_equal(tp, [True, False])
    # đổi score: B chiếm người 2 trước, A chỉ còn người 1 với IoU 0.33 → FP
    tp = nb.match_image(preds, np.array([0.7, 0.8]), gt, 0.5)
    np.testing.assert_array_equal(tp, [False, True])


def test_match_empty(nb):
    assert nb.match_image(np.zeros((0, 4)), np.zeros(0), GT, 0.5).shape == (0,)
    assert nb.match_image(GT, np.array([0.5, 0.4]), np.zeros((0, 4)), 0.5).tolist() == [False, False]


# ---------- 3. AP ----------

def test_average_precision_known_values(nb):
    assert nb.average_precision(np.array([True, True]), np.array([0.9, 0.8]), 2) == pytest.approx(1.0)
    # TP, FP, TP với 2 gt: precision 1, 0.5, 0.667; recall 0.5, 0.5, 1 → làm đơn điệu: 1, 0.667, 0.667
    ap = nb.average_precision(np.array([True, False, True]), np.array([0.9, 0.8, 0.7]), 2)
    assert ap == pytest.approx(0.5 * 1 + 0.5 * (2 / 3))
    # thứ tự đầu vào không quan trọng: sắp theo score
    ap2 = nb.average_precision(np.array([True, True, False]), np.array([0.7, 0.9, 0.8]), 2)
    assert ap2 == pytest.approx(ap)


def test_average_precision_interpolation_matters(nb):
    # FP, TP, TP, FP với 4 gt: không làm đơn điệu thì 0.25*0.5 + 0.25*0.667 = 0.292
    ap = nb.average_precision(np.array([False, True, True, False]), np.array([4, 3, 2, 1.0]), 4)
    assert ap == pytest.approx(0.5 * (2 / 3))
    # recall tối đa 0.5 vì một nửa số người không bao giờ được tìm thấy
    assert nb.average_precision(np.array([True, True]), np.array([2, 1.0]), 4) == pytest.approx(0.5)


def test_average_precision_edge_cases(nb):
    assert nb.average_precision(np.zeros(0, bool), np.zeros(0), 3) == 0.0
    assert nb.average_precision(np.array([False, False]), np.array([0.5, 0.4]), 3) == 0.0
    assert math.isnan(nb.average_precision(np.array([False]), np.array([0.5]), 0))


def test_evaluate_detections_thresholds(nb):
    # pred khớp người 1 với IoU 0.62: TP ở ngưỡng 0.50, 0.55, 0.60; FP từ 0.65
    gts = [np.array([[0, 0, 100, 100]], dtype=float), np.array([[0, 0, 50, 50]], dtype=float)]
    preds = [(np.array([[0, 0, 100, 62]], dtype=float), np.array([0.9])),
             (np.array([[0, 0, 50, 50], [60, 60, 70, 70]], dtype=float), np.array([0.8, 0.95]))]
    res = nb.evaluate_detections(preds, gts)
    assert set(res) >= {"AP50", "AP75", "AP"}
    # ngưỡng thấp: thứ tự score 0.95 FP, 0.9 TP, 0.8 TP; precision 0, 1/2, 2/3 → làm đơn điệu: 2/3, 2/3
    hi = 2 / 3
    # ngưỡng cao: chỉ ảnh 2 khớp: 0.95 FP, 0.9 FP, 0.8 TP → AP = 0.5 * (1/3)
    lo = 0.5 / 3
    assert res["AP50"] == pytest.approx(hi)
    assert res["AP75"] == pytest.approx(lo)
    assert res["AP"] == pytest.approx((3 * hi + 7 * lo) / 10)


def test_iou_thresholds_constant(nb):
    np.testing.assert_allclose(nb.IOU_THRS, np.arange(10) * 0.05 + 0.5, atol=1e-9)


# ---------- 4. mIoU ----------

def test_confusion_and_miou(nb):
    gt = np.array([[0, 0, 1, 1], [0, 0, 1, 1]])
    pred = np.array([[0, 1, 1, 1], [0, 0, 0, 1]])
    cm = nb.confusion_matrix(pred, gt, 2)
    np.testing.assert_array_equal(cm, [[3, 1], [1, 3]])
    per_class, miou = nb.iou_from_confusion(cm)
    np.testing.assert_allclose(per_class, [0.6, 0.6])
    assert miou == pytest.approx(0.6)


def test_miou_is_dataset_level_and_skips_absent_class(nb):
    cm = nb.confusion_matrix(np.array([0, 0, 2, 2]), np.array([0, 0, 2, 0]), 3)
    per_class, miou = nb.iou_from_confusion(cm)
    assert math.isnan(per_class[1]), "lớp không có trong nhãn lẫn dự đoán: nan"
    assert per_class[0] == pytest.approx(2 / 3) and per_class[2] == pytest.approx(0.5)
    assert miou == pytest.approx((2 / 3 + 0.5) / 2)
    # cộng confusion qua nhiều ảnh = tính trên tổng pixel
    a = nb.confusion_matrix(np.ones(10, int), np.ones(10, int), 2)
    b = nb.confusion_matrix(np.zeros(90, int), np.r_[np.ones(10, int), np.zeros(80, int)], 2)
    assert nb.iou_from_confusion(a + b)[0][1] == pytest.approx(0.5)


# ---------- 5. dữ liệu thật: tự skip nếu chưa tải Penn-Fudan ----------

def test_load_pennfudan_real(nb):
    root = ex.dataset("penn-fudan") / "PennFudanPed"
    items = nb.load_pennfudan(root)
    assert len(items) == 170
    assert items[0]["name"] == "FudanPed00001" and items[-1]["name"] == "PennPed00096"
    assert sum(len(it["boxes"]) for it in items) == 423
    np.testing.assert_array_equal(items[0]["boxes"], [[159, 181, 302, 431], [419, 170, 535, 486]])
