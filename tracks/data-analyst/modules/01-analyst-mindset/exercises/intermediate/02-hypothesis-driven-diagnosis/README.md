---
title: Chẩn đoán theo cây giả thuyết - vì sao lượt thuê tháng 10/2012 giảm 9%?
level: intermediate
services: []
files:
  - path: starter/diagnosis.ipynb
    note: 3 hàm TODO (bảng tháng, phân khúc, so cùng thời tiết) + kết luận
  - path: tests/test_diagnosis.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py bike-sharing-uci
  - uv run jupyter lab tracks/data-analyst/modules/01-analyst-mindset/exercises/intermediate/02-hypothesis-driven-diagnosis/starter/diagnosis.ipynb
  - uv run pytest tracks/data-analyst/modules/01-analyst-mindset/exercises/intermediate/02-hypothesis-driven-diagnosis -q
---

## Mục tiêu

Trả lời một câu hỏi "vì sao" của stakeholder bằng cây giả thuyết MECE viết trước khi nhìn dữ liệu: mỗi nhánh
(lịch, mùa vụ, thời tiết, phân khúc) một con số kiểm, loại dần các nhánh, rồi kết luận đủ để quyết định, có ghi
giới hạn.

## Đề bài

Bộ `bike-sharing-uci`, `day.csv` (731 ngày, 2011–2012). Giám đốc vận hành hỏi: *"Lượt thuê tháng 10/2012 giảm 9%
so với tháng 9. Có phải khách bắt đầu bỏ dịch vụ không?"* Mở `starter/diagnosis.ipynb`, đọc cây giả thuyết ở đầu
notebook rồi:

1. `month_summary(day)`: mỗi tháng một dòng, cột `rides`, `casual`, `registered`, `days`, `per_day`, `clear_days`,
   `bad_days`. Dùng nó kiểm nhánh lịch (mỗi ngày) và nhánh mùa vụ (cùng chuyển tháng năm 2011).
2. `segment_contribution(day, m0, m1)`: thay đổi của `casual` và `registered`, phần trăm, và tỉ trọng trong mức
   thay đổi tổng.
3. `same_weather_change(day, m0, m1)`: lượt trung bình mỗi ngày theo loại thời tiết, tháng sau so với tháng trước,
   chỉ cho loại thời tiết có ở cả hai tháng.
4. Chạy các cell `explore`: cơ cấu thời tiết, tháng 10 với cơ cấu thời tiết của tháng 9, tháng 10 bỏ hai ngày bão
   Sandy, chart cho giám đốc. Viết ba câu kết luận → bằng chứng → giới hạn. Báo cáo bài học: làm phần trắc nghiệm
   trong app sau khi chạy notebook.

Các hàm không được sửa DataFrame đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: tháng theo `dteday`, `bad_days` gồm mọi `weathersit >= 3`, tỉ trọng thay đổi cộng
  bằng 1, chỉ so loại thời tiết có ở cả hai tháng.
- Trên bộ thật: 24 tháng; tháng 9/2012 218 573 lượt, tháng 10/2012 198 841; mỗi ngày −12.0% (năm 2011 cùng chuyển
  tháng −6.2%); ngày quang 22 → 14, ngày xấu 0 → 2; `casual` giảm 21.1% và chiếm 46.8% mức giảm; trong cùng loại
  thời tiết: quang −2.6%, mây −4.2%.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`month = pd.to_datetime(day["dteday"]).dt.to_period("M").dt.to_timestamp()`. Đếm ngày quang: tạo cột
`(day["weathersit"] == 1).astype(int)` rồi cộng theo tháng; số ngày là `size` của nhóm.

### Gợi ý 2

`same_weather_change`: hai `groupby("weathersit")["cnt"].mean()` cho hai tháng; giữ index chung bằng
`before.index.intersection(after.index)`. Một ngày mưa to chỉ có ở tháng sau thì không có gì để so.
