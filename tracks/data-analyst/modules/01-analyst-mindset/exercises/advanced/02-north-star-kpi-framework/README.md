---
title: Thiết kế north star, input metric, guardrail và scorecard 28 ngày cho Capital Bikeshare
level: advanced
services: []
files:
  - path: starter/scorecard.ipynb
    note: 1 hàm TODO (scorecard so với 364 ngày trước) + ứng viên north star
  - path: starter/KPI_FRAMEWORK.md
    note: Bộ KPI gửi ban giám đốc
  - path: tests/test_scorecard.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py bike-sharing-uci
  - uv run jupyter lab tracks/data-analyst/modules/01-analyst-mindset/exercises/advanced/02-north-star-kpi-framework/starter/scorecard.ipynb
  - uv run pytest tracks/data-analyst/modules/01-analyst-mindset/exercises/advanced/02-north-star-kpi-framework -q
---

## Mục tiêu

Thay một dashboard 40 chỉ số bằng một bộ KPI có cấu trúc: một north star thể hiện giá trị khách nhận được, vài input
metric mỗi cái một team điều khiển, cặp leading/lagging, guardrail chặn tối ưu sai, metric tree, nhịp xem; và một
scorecard so sánh công bằng với năm trước.

## Đề bài

Bộ `bike-sharing-uci`, `day.csv` (731 ngày, 2011–2012), có thể dùng thêm `hour.csv`. Ban giám đốc mới nói: *"Cho tôi
một con số để cả công ty cùng kéo, vài con số từng team điều khiển được, và một scorecard xem mỗi tháng."* Mở
`starter/scorecard.ipynb`:

1. `kpi_scorecard(day, end, window=28)`: năm metric (`rides`, `registered_rides`, `rides_per_day`,
   `registered_share`, `bad_weather_days`) cho `window` ngày kết thúc ở `end` và cho cùng độ dài kết thúc ở
   `end - 364 ngày`, cột `current`, `previous`, `change_pct`.
2. Chạy các cell `explore`: scorecard vài tháng cuối 2012, lượt thành viên theo tuần và tăng trưởng so với 52 tuần trước.
3. Viết `starter/KPI_FRAMEWORK.md` theo khung bảy mục (300–900 từ): north star có định nghĩa và giá trị hiện tại, input
   metrics, leading và lagging, ít nhất hai guardrail, metric tree bằng sơ đồ mermaid, nhịp xem và chủ sở hữu, rủi ro
   game metric và dữ liệu còn thiếu.

## Tiêu chí đạt

- `kpi_scorecard` đúng trên dữ liệu nhỏ: kỳ gồm cả hai đầu, kỳ so sánh lệch đúng 364 ngày, `change_pct` là `NaN` khi
  kỳ trước bằng 0.
- Trên bộ thật: 28 ngày tới 31/10/2012 có 179 852 lượt so với 113 566 cùng kỳ; lượt thành viên +63.4%; thành viên
  chiếm 81.8%; ngày xấu trời 1 so với 3. 28 ngày tới 30/09/2012: lượt mỗi ngày +82.1%.
- `KPI_FRAMEWORK.md` không còn TODO, đủ bảy mục theo thứ tự, có sơ đồ mermaid, north star có con số. Nội dung chấm theo
  rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Lệch 364 ngày (52 tuần) thay vì một năm lịch để mỗi kỳ có cùng số thứ Hai, thứ Bảy... Lượt thuê ngày làm việc và cuối
tuần rất khác nhau; so cùng ngày lịch năm trước thì mỗi ngày bị so với ngày lệch một thứ (lệch hai thứ nếu khoảng
giữa có ngày 29/02, như năm 2012).

### Gợi ý 2

North star không phải metric "lớn nhất" mà là metric thể hiện khách nhận được giá trị và dẫn tới doanh thu dài hạn.
Với hệ thống thuê xe có hai loại khách trả tiền khác nhau, hỏi: loại khách nào quyết định doanh thu năm sau? Bộ dữ liệu
không có doanh thu, số thành viên, số xe: ghi rõ cần nguồn nào.
