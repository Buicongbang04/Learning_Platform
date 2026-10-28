"""Mô hình chi phí hàng tháng (USD) cho data platform Olist trên một cloud."""

from __future__ import annotations

CLOUD = "TODO"  # TODO 1: "aws", "azure" hoặc "gcp"

DEFAULT_WORKLOAD = {
    "raw_gb_per_day": 2.0,          # dữ liệu thô mới mỗi ngày
    "raw_retention_days": 365,
    "raw_hot_days": 30,             # sau số ngày này chuyển class lạnh
    "curated_retention_days": 3 * 365,
    "compression_ratio": 4.0,       # CSV/JSON -> Parquet
    "queries_per_day": 200,
    "scan_gb_per_query": 0.5,       # sau partition pruning + định dạng cột
    "etl_hours_per_day": 1.0,
    "etl_workers": 2,               # DPU / vCPU / worker
    "stream_events_per_sec": 50,
    "egress_gb_per_month": 50,
}

# TODO 2: bảng giá của cloud đã chọn. Ghi nguồn và ngày tra giá. Ví dụ khoá gợi ý:
PRICES = {
    # "storage_hot_gb_month": ...,
    # "storage_cold_gb_month": ...,
    # "etl_worker_hour": ...,
    # "scan_per_tb": ...,
    # "stream_fixed_month": ...,
    # "egress_per_gb": ...,
    # "other_fixed_month": ...,   # orchestration, monitoring, NAT, metadata DB...
}


def estimate(workload: dict = DEFAULT_WORKLOAD, prices: dict = PRICES) -> dict[str, float]:
    """Trả dict USD/tháng với các khoá storage, compute, warehouse, streaming, egress, other, total."""
    # TODO 3: tính từng khoản ở trạng thái ổn định; total = tổng các khoản; làm tròn 2 chữ số
    raise NotImplementedError


if __name__ == "__main__":
    for item, usd in estimate().items():
        print(f"{item:>10}: {usd:10.2f} USD")
