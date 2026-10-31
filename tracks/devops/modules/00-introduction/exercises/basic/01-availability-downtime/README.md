---
title: Tính availability và error budget từ danh sách incident
level: basic
services: []
files:
  - path: starter/availability.py
    note: 5 TODO
  - path: tests/test_availability.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/00-introduction/exercises/basic/01-availability-downtime -q
---

## Mục tiêu

Tính đúng reliability, metric thứ năm cạnh bốn key của DORA, từ dữ liệu incident thật-dạng: biết SLO 99,9% cho phép
sập bao lâu, và biết vì sao cộng thẳng thời lượng các incident thường cho ra con số sai.

## Đề bài

Tháng 10, Olist Shop có một danh sách incident do hệ thống alert tạo ra. Mỗi incident là một dict:

```python
{"id": "i07", "started_at": "2026-10-10T23:30:00+07:00", "resolved_at": "2026-10-10T17:15:00Z", "impact": "outage"}
```

- `impact` là `"outage"` (người dùng không dùng được dịch vụ) hoặc `"degraded"` (chậm nhưng vẫn dùng được). Chỉ
  `outage` tính vào downtime.
- `resolved_at` là `None` khi incident chưa đóng.
- Thời điểm có múi giờ, nhưng mỗi nguồn alert ghi một kiểu (`+07:00` hoặc `Z`).

Viết 5 hàm trong `starter/availability.py`:

1. `allowed_downtime(slo, window)`: thời gian được phép sập trong cửa sổ `window` với SLO dạng tỉ lệ (`0.999`).
   SLO ngoài khoảng mở `(0, 1)` (ví dụ `1.0` hoặc người dùng gõ `99.9`) báo `ValueError`.
2. `merge_outages(spans)`: nhận list `(bắt_đầu, kết_thúc)`, gộp các khoảng chồng nhau hoặc nối liền nhau, trả list
   đã sắp theo thời gian.
3. `downtime(incidents, start, end)`: tổng thời gian sập trong cửa sổ `[start, end)`. Incident vượt ra ngoài cửa
   sổ chỉ tính phần nằm trong. Incident chưa đóng tính tới `end`. Hai alert cùng một lần sập (API và worker cùng
   kêu) chỉ tính một lần. Thời điểm thiếu múi giờ, hoặc incident đóng trước khi mở, báo `ValueError`.
4. `availability(incidents, start, end)`: `1 - downtime / độ dài cửa sổ`.
5. `budget_remaining(slo, incidents, start, end)`: error budget còn lại, được phép âm khi đã tiêu quá.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/00-introduction/exercises/basic/01-availability-downtime -q` pass toàn bộ.
- Giải thích được vì sao SLO `0.999` trên 30 ngày cho 43 phút 12 giây, và 99,99% chỉ còn khoảng 4 phút 19 giây.
- Nói được hai cách đếm downtime sai mà test bắt: cộng thẳng hai alert chồng nhau, và cắt thời điểm theo chuỗi
  ngày thay vì theo thời điểm tuyệt đối.

## Gợi ý

### Gợi ý 1

`datetime.fromisoformat` (Python 3.11+) đọc được cả `Z`. Thời điểm có múi giờ so sánh và trừ nhau đúng dù khác
offset; `utcoffset()` trả `None` nghĩa là thiếu múi giờ. `timedelta` nhân được với số thực và chia cho nhau ra số.

### Gợi ý 2

Gộp khoảng: sắp theo điểm bắt đầu, đi một lượt; nếu khoảng mới bắt đầu không muộn hơn điểm kết thúc của khoảng
cuối đã gộp thì nới khoảng cuối, ngược lại thêm khoảng mới. Cắt theo cửa sổ **trước** khi gộp, và bỏ khoảng có độ
dài bằng 0 sau khi cắt.
