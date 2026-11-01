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
    return np.argmin(sq_dists(x, centroids), axis=1).astype(np.int64)


def kmeans(x: np.ndarray, n_clusters: int, n_iter: int = 20, seed: int = 0) -> np.ndarray:
    """Lloyd k-means. Khởi tạo: x[rng.choice(len(x), n_clusters, replace=False)] với rng = default_rng(seed).

    Mỗi vòng: gán mọi điểm vào centroid gần nhất, rồi đặt centroid bằng trung bình các điểm của nó; cụm rỗng giữ
    centroid cũ. Trả float32 (n_clusters, d).
    """
    x = np.asarray(x, dtype=np.float32)
    rng = np.random.default_rng(seed)
    centroids = x[rng.choice(len(x), n_clusters, replace=False)].copy()
    for _ in range(n_iter):
        labels = assign(x, centroids)
        for c in range(n_clusters):
            members = x[labels == c]
            if len(members):
                centroids[c] = members.mean(axis=0)
    return centroids


class IVFIndex:
    def __init__(self, nlist: int, n_iter: int = 20, seed: int = 0):
        self.nlist, self.n_iter, self.seed = nlist, n_iter, seed
        self.centroids: np.ndarray | None = None
        self.lists: list[np.ndarray] = []
        self.vectors = np.zeros((0, 0), dtype=np.float32)

    def train(self, x: np.ndarray) -> None:
        """Học centroid bằng kmeans(x, nlist, n_iter, seed); tạo nlist danh sách rỗng."""
        self.centroids = kmeans(x, self.nlist, self.n_iter, self.seed)
        self.lists = [np.zeros(0, dtype=np.int64) for _ in range(self.nlist)]
        self.vectors = np.zeros((0, self.centroids.shape[1]), dtype=np.float32)

    def add(self, x: np.ndarray) -> None:
        """Thêm vector; id nối tiếp từ số vector đã có (0, 1, 2...). Mỗi id vào đúng danh sách của centroid gần nhất."""
        x = np.asarray(x, dtype=np.float32)
        start = len(self.vectors)
        labels = assign(x, self.centroids)
        for c in range(self.nlist):
            new = start + np.flatnonzero(labels == c)
            self.lists[c] = np.concatenate([self.lists[c], new]).astype(np.int64)
        self.vectors = np.concatenate([self.vectors, x])

    def search(self, q: np.ndarray, k: int, nprobe: int = 1) -> tuple[list[int], int]:
        """Top-k id gần q nhất trong nprobe danh sách có centroid gần q nhất, và số vector đã so khoảng cách.

        Thứ tự: khoảng cách tăng dần, bằng nhau thì id nhỏ trước. Centroid bằng khoảng cách thì chỉ số nhỏ trước.
        """
        q = np.asarray(q, dtype=np.float32)[None, :]
        probe = np.argsort(sq_dists(q, self.centroids)[0], kind="stable")[:nprobe]
        candidates = np.sort(np.concatenate([self.lists[c] for c in probe]))
        d = sq_dists(q, self.vectors[candidates])[0]
        order = np.argsort(d, kind="stable")[:k]
        return [int(i) for i in candidates[order]], len(candidates)
