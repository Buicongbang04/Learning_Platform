---
title: Sự cố - chạy backfill xong số liệu của các tháng cũ bị đổi
level: intermediate
services: []
files:
  - path: starter/monthly.py
    note: Pipeline kết quả theo tháng, tìm và sửa lỗi
  - path: tests/test_incident.py
    note: Không sửa
  - path: tests/conftest.py
    note: Dựng Prefect tạm, không sửa
run:
  - uv run pytest tracks/mlops/modules/05-training-pipelines/exercises/intermediate/02-incident-backfill-overwrite -q
---

## Mục tiêu

Chẩn đoán một sự cố dữ liệu từ triệu chứng, tìm đúng chỗ trong mã gây ra nó, sửa tối thiểu và có test chứng minh.

## Đề bài

Pipeline `monthly.py` tính chỉ số hằng tháng (số dòng, thời lượng trung bình, MAE của một model tuyến tính) cho dữ liệu
`data_dir/trips-<YYYY-MM>.csv` và ghi `results_dir/<YYYY-MM>.json` với `{"month", "rows", "mean_duration", "mae"}`. Hàng tháng
nó chạy đúng một tháng.

Thứ Hai, sau khi nhóm ETL sửa lỗi nguồn của tháng 8, bạn chạy backfill cho cả ba tháng 2026-08, 2026-09, 2026-10 trong một lần
bằng `run_months(["2026-08", "2026-09", "2026-10"], data_dir, results_dir)`. Sau đó dashboard cho thấy:

- MAE của tháng 9 và tháng 10 bằng đúng MAE của tháng 8, giống nhau tới chữ số thập phân cuối cùng, cả `rows` và
  `mean_duration` cũng vậy. Trước backfill hai tháng này có số riêng và đúng.
- Ba tệp CSV nguồn khác nhau rõ rệt (số dòng khác nhau).
- Chạy lại riêng từng tháng một thì ra số đúng.
- Không có lỗi hay cảnh báo trong log; flow báo xanh.

Hợp đồng test dùng: `run_months(months, data_dir, results_dir)` là flow Prefect, xử lý các tháng theo thứ tự đưa vào và ghi
`results_dir/<tháng>.json`. Tìm nguyên nhân, sửa trong `starter/monthly.py`; không đổi test hay dữ liệu.

## Tiêu chí đạt

- Mỗi tháng trong đợt nhiều tháng có đúng `rows`, `mean_duration`, `mae` tính từ tệp CSV của tháng đó.
- Chạy backfill chứa các tháng đã có kết quả đúng thì các tệp kết quả đó không đổi (từng byte).
- Tháng không nằm trong đợt không bị đụng tới; không tạo thêm tệp ngoài các tháng được yêu cầu.
- Kết quả không phụ thuộc thứ tự tháng; chạy lại cùng đợt cho cùng tệp; sửa dữ liệu nguồn của một tháng rồi chạy tháng đó chỉ
  đổi tệp của tháng đó.

## Gợi ý

### Gợi ý 1

Bắt đầu từ so sánh: cùng một tháng cho số đúng khi chạy một mình nhưng sai khi chạy sau một tháng khác. Điều gì khác nhau giữa
hai lần chạy mà không nằm ở dữ liệu đầu vào của tháng đó?

### Gợi ý 2

Viết một test nhỏ của riêng bạn: chạy hai tháng liên tiếp trong cùng tiến trình và in `rows` của từng tháng ở mỗi bước của
hàm tính chỉ số. Dừng ở bước đầu tiên mà `rows` không khớp với tệp CSV.
