"""Hộp bao (bounding box), IoU và Non-Maximum Suppression bằng numpy.

Hai định dạng hộp, mỗi hộp một dòng của mảng shape (N, 4), số thực, đơn vị pixel:
    xyxy    (x1, y1, x2, y2): góc trên trái, góc dưới phải (định dạng của torchvision, Pascal VOC)
    cxcywh  (cx, cy, w, h):   tâm và kích thước (định dạng nhãn YOLO, trước khi chia kích thước ảnh)
Diện tích hộp xyxy là (x2 - x1) * (y2 - y1); hộp có x2 <= x1 hoặc y2 <= y1 có diện tích 0.
Chỉ dùng numpy trong tệp này.
"""

from __future__ import annotations

import numpy as np


def cxcywh_to_xyxy(boxes: np.ndarray) -> np.ndarray:
    # TODO
    raise NotImplementedError


def xyxy_to_cxcywh(boxes: np.ndarray) -> np.ndarray:
    # TODO
    raise NotImplementedError


def box_area(boxes: np.ndarray) -> np.ndarray:
    """Diện tích từng hộp xyxy, shape (N,); hộp suy biến (x2 <= x1 hoặc y2 <= y1) cho 0."""
    # TODO
    raise NotImplementedError


def box_iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Ma trận IoU shape (N, M) giữa hộp xyxy a (N, 4) và b (M, 4). Không vòng lặp Python.

    Hợp bằng 0 (hai hộp suy biến) thì IoU là 0, không phải nan.
    """
    # TODO: broadcast a[:, None, :] với b[None, :, :] để có giao của mọi cặp
    raise NotImplementedError


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> np.ndarray:
    """Greedy NMS. Trả chỉ số (int64) các hộp được giữ, theo score GIẢM dần.

    Lặp: lấy hộp score cao nhất còn lại, giữ nó, bỏ mọi hộp còn lại có IoU với nó LỚN HƠN HẲN
    iou_threshold. Hộp IoU đúng bằng ngưỡng được giữ (như torchvision.ops.nms).
    """
    # TODO
    raise NotImplementedError


def batched_nms(boxes: np.ndarray, scores: np.ndarray, classes: np.ndarray, iou_threshold: float) -> np.ndarray:
    """NMS riêng cho từng lớp: hộp khác lớp không bao giờ loại nhau. Trả chỉ số theo score giảm dần."""
    # TODO
    raise NotImplementedError
