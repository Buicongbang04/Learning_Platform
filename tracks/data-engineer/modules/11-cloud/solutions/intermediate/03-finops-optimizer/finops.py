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
    if storage_class not in STORAGE_CLASSES:
        raise ValueError(f"Storage class lạ: {storage_class!r}")
    storage, retrieval, _ = STORAGE_CLASSES[storage_class]
    return size_gb * storage + gb_read_per_month * retrieval


def best_storage_class(size_gb: float, gb_read_per_month: float) -> str:
    candidates = [name for name, (_, _, archive) in STORAGE_CLASSES.items()
                  if not archive or gb_read_per_month == 0]
    # min() giữ phần tử đầu tiên khi hoà -> class nóng hơn
    return min(candidates, key=lambda c: round(monthly_cost(size_gb, c, gb_read_per_month), 10))


def scanned_gb(table_gb: float, partitions_total: int, partitions_read: int,
               columns_total: int, columns_read: int, columnar: bool) -> float:
    if table_gb < 0 or partitions_total <= 0 or columns_total <= 0:
        raise ValueError("table_gb >= 0, partitions_total > 0, columns_total > 0")
    if not 0 <= partitions_read <= partitions_total or not 0 <= columns_read <= columns_total:
        raise ValueError("Số partition/cột đọc phải nằm trong [0, tổng]")
    result = table_gb * partitions_read / partitions_total
    if columnar:
        result *= columns_read / columns_total
    return result


def query_cost(gb: float, price_per_tib: float = 6.25, min_mb: float = 10) -> float:
    billed_gb = max(gb, min_mb / 1024)
    return billed_gb / 1024 * price_per_tib


def savings_report(datasets: list[dict]) -> list[dict]:
    report = []
    for ds in datasets:
        size, reads = ds["size_gb"], ds["gb_read_per_month"]
        recommended = best_storage_class(size, reads)
        current_cost = round(monthly_cost(size, ds["storage_class"], reads), 2)
        recommended_cost = round(monthly_cost(size, recommended, reads), 2)
        savings = round(current_cost - recommended_cost, 2)
        if savings > 0:
            report.append({
                "name": ds["name"],
                "current": ds["storage_class"],
                "recommended": recommended,
                "current_cost": current_cost,
                "recommended_cost": recommended_cost,
                "monthly_savings": savings,
            })
    return sorted(report, key=lambda r: r["monthly_savings"], reverse=True)
