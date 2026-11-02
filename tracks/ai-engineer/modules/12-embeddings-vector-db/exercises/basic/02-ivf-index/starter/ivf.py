"""Inverted File index (IVF): k-means làm coarse quantizer, tìm trong nprobe cụm gần nhất.

Chỉ dùng numpy trong tệp này. Khoảng cách là bình phương khoảng cách Euclid ở mọi bước.
"""

from __future__ import annotations

import numpy as np


def sq_dists(x: np.ndarray, centroids: np.ndarray) -> np.ndarray:
    """Bình phương khoảng cách Euclid (n, n_centroids), không âm. Hàm có sẵn, không phải TODO."""
    x = np.asarray(x, dtype=np.float32)
    c = np.asarray(centroids, dtype=np.float32)
    d = (x * x).sum(1)[:, None] + (c * c).sum(1)[None, :] - 2 * (x @ c.T)
    return np.maximum(d, 0)


def assign(x: np.ndarray, centroids: np.ndarray) -> np.ndarray:
    """Chỉ số centroid gần nhất cho mỗi dòng của x (int64); bằng khoảng cách thì chỉ số nhỏ."""
    # TODO
    raise NotImplementedError


def kmeans(x: np.ndarray, n_clusters: int, n_iter: int = 20, seed: int = 0) -> np.ndarray:
    """Lloyd k-means. Khởi tạo: x[rng.choice(len(x), n_clusters, replace=False)] với rng = default_rng(seed).

    Mỗi vòng: gán mọi điểm vào centroid gần nhất, rồi đặt centroid bằng trung bình các điểm của nó; cụm rỗng giữ
    centroid cũ. Trả float32 (n_clusters, d).
    """
    # TODO
    raise NotImplementedError


class IVFIndex:
    def __init__(self, nlist: int, n_iter: int = 20, seed: int = 0):
        self.nlist, self.n_iter, self.seed = nlist, n_iter, seed
        self.centroids: np.ndarray | None = None
        self.lists: list[np.ndarray] = []
        self.vectors = np.zeros((0, 0), dtype=np.float32)

    def train(self, x: np.ndarray) -> None:
        """Học centroid bằng kmeans(x, nlist, n_iter, seed); tạo nlist danh sách rỗng."""
        # TODO
        raise NotImplementedError

    def add(self, x: np.ndarray) -> None:
        """Thêm vector; id nối tiếp từ số vector đã có (0, 1, 2...). Mỗi id vào đúng danh sách của centroid gần nhất."""
        # TODO
        raise NotImplementedError

    def search(self, q: np.ndarray, k: int, nprobe: int = 1) -> tuple[list[int], int]:
        """Top-k id gần q nhất trong nprobe danh sách có centroid gần q nhất, và số vector đã so khoảng cách.

        Thứ tự: khoảng cách tăng dần, bằng nhau thì id nhỏ trước. Centroid bằng khoảng cách thì chỉ số nhỏ trước.
        """
        # TODO
        raise NotImplementedError
