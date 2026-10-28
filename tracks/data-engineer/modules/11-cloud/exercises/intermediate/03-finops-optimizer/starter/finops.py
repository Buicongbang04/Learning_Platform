"""FinOps cho data lake: chọn storage class, ước tính scan. Giá minh hoạ (giống S3 us-east-1)."""

from __future__ import annotations

# tên: (USD/GB-tháng lưu trữ, USD/GB đọc lại, archive cần restore hàng giờ?)
# Thứ tự từ nóng tới lạnh.
STORAGE_CLASSES: dict[str, tuple[float, float, bool]] = {
    "STANDARD": (0.023, 0.0, False),
    "STANDARD_IA": (0.0125, 0.01, False),
    "GLACIER_IR": (0.004, 0.03, False),
    "DEEP_ARCHIVE": (0.00099, 0.02, True),
}


def monthly_cost(size_gb: float, storage_class: str, gb_read_per_month: float) -> float:
    # TODO 1: size_gb * storage + gb_read_per_month * retrieval; class lạ -> ValueError
    raise NotImplementedError


def best_storage_class(size_gb: float, gb_read_per_month: float) -> str:
    # TODO 2: class rẻ nhất; archive chỉ xét khi gb_read_per_month == 0; hoà -> class nóng hơn
    raise NotImplementedError


def scanned_gb(table_gb: float, partitions_total: int, partitions_read: int,
               columns_total: int, columns_read: int, columnar: bool) -> float:
    # TODO 3: pruning theo partition; columnar thì nhân thêm tỉ lệ cột
    raise NotImplementedError


def query_cost(gb: float, price_per_tib: float = 6.25, min_mb: float = 10) -> float:
    # TODO 4: tối thiểu min_mb MB mỗi truy vấn; 1 TiB = 1024 GB; 1 GB = 1024 MB
    raise NotImplementedError


def savings_report(datasets: list[dict]) -> list[dict]:
    # TODO 5: chỉ dataset có tiết kiệm > 0, sắp xếp monthly_savings giảm dần
    raise NotImplementedError
