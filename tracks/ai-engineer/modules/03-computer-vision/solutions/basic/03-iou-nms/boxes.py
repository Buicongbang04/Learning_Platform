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
    cx, cy, w, h = boxes.T
    return np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=1)


def xyxy_to_cxcywh(boxes: np.ndarray) -> np.ndarray:
    x1, y1, x2, y2 = boxes.T
    return np.stack([(x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1], axis=1)


def box_area(boxes: np.ndarray) -> np.ndarray:
    """Diện tích từng hộp xyxy, shape (N,); hộp suy biến (x2 <= x1 hoặc y2 <= y1) cho 0."""
    return np.clip(boxes[:, 2] - boxes[:, 0], 0, None) * np.clip(boxes[:, 3] - boxes[:, 1], 0, None)


def box_iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Ma trận IoU shape (N, M) giữa hộp xyxy a (N, 4) và b (M, 4). Không vòng lặp Python.

    Hợp bằng 0 (hai hộp suy biến) thì IoU là 0, không phải nan.
    """
    lt = np.maximum(a[:, None, :2], b[None, :, :2])
    rb = np.minimum(a[:, None, 2:], b[None, :, 2:])
    wh = np.clip(rb - lt, 0, None)
    inter = wh[..., 0] * wh[..., 1]
    union = box_area(a)[:, None] + box_area(b)[None, :] - inter
    return np.divide(inter, union, out=np.zeros_like(inter, dtype=float), where=union > 0)


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> np.ndarray:
    """Greedy NMS. Trả chỉ số (int64) các hộp được giữ, theo score GIẢM dần.

    Lặp: lấy hộp score cao nhất còn lại, giữ nó, bỏ mọi hộp còn lại có IoU với nó LỚN HƠN HẲN
    iou_threshold. Hộp IoU đúng bằng ngưỡng được giữ (như torchvision.ops.nms).
    """
    order = np.argsort(-scores, kind="stable")
    keep = []
    while order.size:
        i = order[0]
        keep.append(i)
        if order.size == 1:
            break
        ious = box_iou(boxes[i:i + 1], boxes[order[1:]])[0]
        order = order[1:][ious <= iou_threshold]
    return np.array(keep, dtype=np.int64)


def batched_nms(boxes: np.ndarray, scores: np.ndarray, classes: np.ndarray, iou_threshold: float) -> np.ndarray:
    """NMS riêng cho từng lớp: hộp khác lớp không bao giờ loại nhau. Trả chỉ số theo score giảm dần."""
    keep = [np.flatnonzero(classes == c)[nms(boxes[classes == c], scores[classes == c], iou_threshold)]
            for c in np.unique(classes)]
    keep = np.concatenate(keep) if keep else np.zeros(0, dtype=np.int64)
    return keep[np.argsort(-scores[keep], kind="stable")].astype(np.int64)
