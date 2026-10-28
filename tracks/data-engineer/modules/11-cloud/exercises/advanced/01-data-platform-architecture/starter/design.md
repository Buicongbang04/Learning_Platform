# Thiết kế data platform Olist trên TODO-cloud

## 1. Bối cảnh và yêu cầu

TODO: tóm tắt yêu cầu chức năng (batch hằng giờ, fraud < 1 phút, PII) và phi chức năng
(ngân sách, đội 3 người, độ tin cậy). Ghi rõ giả định.

## 2. Kiến trúc tổng quan

TODO: sơ đồ mermaid từ nguồn tới dashboard, đánh dấu batch và streaming.

## 3. Dịch vụ theo từng lớp

TODO: bảng | Lớp | Dịch vụ | Lý do chọn | cho ingestion, storage, processing, warehouse,
streaming, orchestration, BI.

## 4. Ước tính chi phí

TODO: bảng chi phí theo khoản (khớp kết quả của estimate.py), tổng USD/tháng, giả định và các
cách giảm chi phí nếu vượt ngân sách.

## 5. Quyết định kiến trúc (ADR)

TODO: ít nhất 3 mục `### ADR-n: ...` gồm Bối cảnh, Lựa chọn, Lý do, Đánh đổi.

## 6. Bảo mật và IAM

TODO: danh tính của từng workload, least privilege, mạng riêng (VPC/VNet, private endpoint),
mã hoá at rest/in transit, xử lý PII.

## 7. Vận hành

TODO: monitoring/alert, CI/CD, IaC, backup/DR, dọn tài nguyên và cảnh báo ngân sách.
