---
title: Thiết kế data platform Olist trên một cloud, kèm ước tính chi phí
level: advanced
services: []
files:
  - path: starter/design.md
    note: Tài liệu thiết kế, thay mọi TODO
  - path: starter/estimate.py
    note: Mô hình chi phí, 3 TODO
  - path: tests/test_architecture.py
    note: Không sửa. Kiểm tra cấu trúc tài liệu và tính nhất quán của mô hình chi phí
run:
  - uv run pytest tracks/data-engineer/modules/11-cloud/exercises/advanced/01-data-platform-architecture -q
---

## Mục tiêu

Làm bài toán giống vòng **system design** khi phỏng vấn Data Engineer: chọn một cloud, thiết kế
nền tảng dữ liệu end-to-end cho Olist, giải thích từng quyết định bằng đánh đổi, và đưa ra con số
chi phí hàng tháng có căn cứ.

## Đề bài

Bối cảnh: Olist muốn rời hạ tầng tự quản sang cloud. Số liệu:

- Nguồn: Postgres OLTP (orders, order_items, payments, customers, sellers, products, reviews),
  khoảng **2 GB dữ liệu thô mới mỗi ngày**; sự kiện thanh toán real-time ~50 sự kiện/giây lúc cao điểm.
- Giữ dữ liệu thô 1 năm (có thể rẻ hơn sau 30 ngày), dữ liệu curated 3 năm.
- ~30 analyst, ~200 truy vấn BI/ngày, dashboard doanh thu cần cập nhật mỗi giờ; một dashboard
  fraud cần độ trễ < 1 phút.
- Đội 3 Data Engineer, không có đội platform riêng → ưu tiên managed/serverless.
- PII (`customer_unique_id`, zip code) phải mã hoá và chỉ nhóm được duyệt mới xem bản gốc.
- Ngân sách mục tiêu: **< 1,500 USD/tháng** cho môi trường prod.

Việc cần làm:

1. Chọn **một** cloud (AWS, Azure hoặc GCP), đặt `CLOUD` trong `starter/estimate.py`.
2. Viết `starter/design.md` với đủ các mục (giữ đúng tên heading đã có trong starter):
   bối cảnh/yêu cầu, sơ đồ kiến trúc (khối ` ```mermaid `), bảng dịch vụ dùng cho từng lớp
   (ingestion, storage, processing, warehouse, streaming, orchestration, BI), ước tính chi phí,
   ít nhất **3 quyết định dạng ADR** (`### ADR-1: ...`, có *Bối cảnh, Lựa chọn, Lý do, Đánh đổi*),
   bảo mật & IAM (role/managed identity/service account, mạng, mã hoá, PII), vận hành (monitoring,
   CI/CD, IaC, DR, dọn tài nguyên).
3. Hoàn thiện `starter/estimate.py`: bảng giá `PRICES` của cloud đã chọn (ghi nguồn/ngày tra giá
   trong comment) và hàm `estimate(workload, prices=PRICES)` trả dict USD/tháng.

## Tiêu chí đạt

- `design.md` không còn `TODO`, có đủ 7 heading của template, có sơ đồ mermaid, ≥ 3 mục `### ADR-`.
- Tài liệu nhắc tới dịch vụ của đúng cloud đã chọn cho ít nhất 5 trong 6 nhóm compute, object
  storage, managed SQL, ETL, warehouse, streaming.
- Mục bảo mật nhắc tới cơ chế danh tính (IAM role / managed identity / service account), mã hoá và mạng riêng.
- `estimate()` trả các khoá `storage`, `compute`, `warehouse`, `streaming`, `egress`, `other`, `total`;
  không âm; `total` bằng tổng các khoá còn lại; tăng dữ liệu thì tăng chi phí storage; tăng số truy
  vấn thì chi phí warehouse không giảm.
- Với `DEFAULT_WORKLOAD`, tổng chi phí nằm trong khoảng hợp lý 20 – 5,000 USD/tháng, và con số đó
  xuất hiện trong mục chi phí của `design.md` (sai lệch ≤ 10%).

## Gợi ý

### Gợi ý 1

Storage tăng dần theo thời gian: sau 12 tháng có `2 GB x 365` dữ liệu thô. Ước tính ở **trạng thái
ổn định** (đủ thời gian lưu), tách raw (sau 30 ngày chuyển class lạnh) và curated (Parquet, nén ~4 lần).

### Gợi ý 2

Warehouse serverless tính theo byte quét: `số truy vấn/tháng x GB quét mỗi truy vấn`. Với partition
theo ngày + định dạng cột, một truy vấn dashboard chỉ quét vài trăm MB. So sánh với phương án
provisioned (Redshift Serverless RPU-giờ, Synapse dedicated DWU) trong một ADR.
