---
title: FinOps - chọn storage class và giảm chi phí scan
level: intermediate
services: []
files:
  - path: starter/finops.py
    note: 5 TODO
  - path: tests/test_finops.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/11-cloud/exercises/intermediate/03-finops-optimizer -q
---

## Mục tiêu

Ra quyết định tối ưu chi phí bằng số liệu, không bằng cảm tính: storage class nào rẻ nhất cho
một kiểu truy cập, partition + định dạng cột tiết kiệm bao nhiêu tiền scan, và lập báo cáo tiết
kiệm cho cả data lake.

## Đề bài

`starter/finops.py` có bảng giá **minh hoạ** `STORAGE_CLASSES` (giá lưu trữ USD/GB-tháng, phí đọc
lại USD/GB, có phải dạng archive cần "restore" hàng giờ hay không), xếp theo thứ tự từ nóng tới lạnh.
Hoàn thiện:

1. **TODO 1** `monthly_cost(size_gb, storage_class, gb_read_per_month) -> float`:
   `size_gb * storage + gb_read_per_month * retrieval`. Class lạ thì `ValueError`.
2. **TODO 2** `best_storage_class(size_gb, gb_read_per_month) -> str`: class có `monthly_cost`
   nhỏ nhất. Class archive (`DEEP_ARCHIVE`) **chỉ được xét khi `gb_read_per_month == 0`**. Bằng
   tiền nhau thì chọn class đứng trước (nóng hơn) trong `STORAGE_CLASSES`.
3. **TODO 3** `scanned_gb(table_gb, partitions_total, partitions_read, columns_total, columns_read,
   columnar) -> float`: số GB một truy vấn phải đọc. Partition pruning nhân với
   `partitions_read / partitions_total`. Nếu `columnar=True` (Parquet/ORC, BigQuery) thì nhân thêm
   `columns_read / columns_total`; định dạng dòng (CSV, JSON) phải đọc mọi cột. `partitions_read`
   lớn hơn tổng, hoặc tham số không dương, thì `ValueError`.
4. **TODO 4** `query_cost(gb, price_per_tib=6.25, min_mb=10) -> float`: kiểu BigQuery on-demand:
   mỗi truy vấn tính tối thiểu `min_mb` MB, 1 TiB = 1024 GB, 1 GB = 1024 MB.
5. **TODO 5** `savings_report(datasets) -> list[dict]`: mỗi dataset là dict
   `{"name", "size_gb", "storage_class", "gb_read_per_month"}`. Trả list dict
   `{"name", "current", "recommended", "current_cost", "recommended_cost", "monthly_savings"}`
   (chi phí làm tròn 2 chữ số, `monthly_savings = current_cost - recommended_cost` làm tròn 2 chữ
   số), **chỉ gồm dataset tiết kiệm được > 0**, sắp xếp `monthly_savings` giảm dần.

## Tiêu chí đạt

- `monthly_cost` đúng theo bảng giá, class lạ ném `ValueError`.
- Dữ liệu đọc nhiều chọn `STANDARD`, ít đọc chọn class lạnh hơn, không bao giờ đọc chọn `DEEP_ARCHIVE`.
- `scanned_gb` phản ánh đúng pruning và columnar; tham số sai ném `ValueError`.
- `query_cost` áp mức tối thiểu 10 MB.
- `savings_report` đúng giá trị, lọc và sắp xếp đúng.

## Gợi ý

### Gợi ý 1

`min(candidates, key=lambda c: monthly_cost(...))` trả phần tử nhỏ nhất **đầu tiên** khi bằng
nhau, nên chỉ cần duyệt `candidates` theo thứ tự của `STORAGE_CLASSES`.

### Gợi ý 2

So sánh `round(cost, 2)` khi làm báo cáo để tránh lỗi số thực kiểu `0.30000000000000004`.
Tính `monthly_savings` từ hai giá trị đã làm tròn.
