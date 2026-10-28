---
title: So sánh 3 cloud cho cùng một data platform và chống lock-in
level: advanced
services: []
files:
  - path: starter/comparison.md
    note: Tài liệu so sánh, thay mọi TODO
  - path: starter/decision.py
    note: Ma trận quyết định có trọng số, 4 TODO
  - path: tests/test_multi_cloud.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/11-cloud/exercises/advanced/02-multi-cloud-comparison -q
  - uv run python tracks/data-engineer/modules/11-cloud/exercises/advanced/02-multi-cloud-comparison/starter/decision.py
---

## Mục tiêu

Trả lời câu hỏi CTO hay hỏi: "Ta nên lên AWS, Azure hay GCP, và nếu sau này phải chuyển thì mất
bao nhiêu công?". Bạn ánh xạ cùng một kiến trúc sang 3 cloud, chấm điểm có trọng số, và thiết kế
để giảm **vendor lock-in**.

## Đề bài

Lấy kiến trúc ở bài advanced 01 (hoặc kiến trúc capstone: Postgres → lake → warehouse → BI,
cộng nhánh streaming Kafka).

1. `starter/decision.py`:
   - **TODO 1** `SCORES`: điểm 1–5 cho `aws`, `azure`, `gcp` theo **ít nhất 5 tiêu chí**, bắt buộc
     có `cost` và `team_skills` (ví dụ thêm: `managed_services`, `ecosystem`, `compliance`,
     `existing_contracts`, `hiring_market`). Điểm phản ánh bối cảnh **của bạn** (công ty dùng
     Microsoft 365? đội đã biết BigQuery?), không có đáp án đúng.
   - **TODO 2** `WEIGHTS`: trọng số không âm cho đúng các tiêu chí đó.
   - **TODO 3** `weighted_scores(scores, weights) -> dict[str, float]`: trung bình có trọng số (chuẩn
     hoá trọng số về tổng 1), làm tròn 3 chữ số. `ValueError` khi: trọng số âm hoặc tổng bằng 0;
     một cloud thiếu tiêu chí có trong `weights`; điểm ngoài [1, 5].
   - **TODO 4** `rank(scores, weights) -> list[tuple[str, float]]`: sắp xếp điểm giảm dần, hoà thì
     theo tên cloud tăng dần.
2. `starter/comparison.md` với các mục (giữ tên heading của template):
   - **Ánh xạ kiến trúc**: bảng có cột `Thành phần | AWS | Azure | GCP`, **ít nhất 8 dòng**
     (compute, object storage, managed SQL, ETL, warehouse, streaming, orchestration, IAM, BI,
     monitoring...).
   - **Chi phí**: so sánh định tính/định lượng 3 cloud cho workload này (nêu khoản khác biệt lớn
     nhất: egress, warehouse pricing model, orchestration).
   - **Ma trận quyết định**: dán kết quả `rank()` và giải thích trọng số.
   - **Lock-in và tính di động**: thành phần nào khó chuyển nhất, chiến lược giảm (định dạng mở,
     Terraform, Airflow/dbt/Spark, Kubernetes, lớp trừu tượng...), chi phí của việc chống lock-in.
   - **Khuyến nghị**: cloud được chọn và điều kiện khiến bạn đổi ý.

## Tiêu chí đạt

- `SCORES` có đủ 3 cloud, cùng bộ ≥ 5 tiêu chí (có `cost`, `team_skills`), điểm nguyên 1–5;
  `WEIGHTS` không âm, khớp tiêu chí.
- `weighted_scores` và `rank` đúng trên dữ liệu kiểm tra của test, ném `ValueError` đúng trường hợp.
- `comparison.md` không còn `TODO`, có đủ 5 mục, bảng ánh xạ ≥ 8 dòng với 3 cột cloud.
- Mục lock-in nhắc ít nhất 3 công nghệ/kỹ thuật di động (vd. Parquet, Iceberg, Delta, Terraform,
  Airflow, dbt, Spark, Kubernetes, Kafka).
- Mục khuyến nghị nêu tên cloud đứng đầu theo `rank()` của bạn (hoặc giải thích vì sao chọn khác).

## Gợi ý

### Gợi ý 1

Chuẩn hoá: `w = {k: v / total for k, v in weights.items()}` rồi
`sum(scores[cloud][k] * w[k] for k in w)`. Kiểm tra lỗi trước khi tính.

### Gợi ý 2

Lock-in không đều: object storage và Spark gần như chuyển được ngay; warehouse SQL dialect,
IAM, stored procedure, dịch vụ streaming và orchestration native (Step Functions, ADF pipeline JSON)
là phần tốn công. Ước lượng công chuyển theo "người-tuần" cho từng thành phần.
