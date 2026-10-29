---
title: Thiết kế lại "slide xấu" Bike Sharing thành một trang storytelling cho COO
level: advanced
services: []
files:
  - path: starter/redesign.ipynb
    note: Slide gốc + 3 hàm TODO (2 hàm số liệu, 1 hàm vẽ trang)
  - path: starter/MEMO.md
    note: Giải thích thiết kế - giữ, đổi, bỏ gì và vì sao
  - path: tests/test_redesign.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py bike-sharing-uci
  - uv run jupyter lab tracks/data-analyst/modules/08-visualization-chart-reading/exercises/advanced/02-redesign-for-stakeholder/starter/redesign.ipynb
  - uv run pytest tracks/data-analyst/modules/08-visualization-chart-reading/exercises/advanced/02-redesign-for-stakeholder -q
---

## Mục tiêu

Biến một slide "đủ dữ liệu nhưng không ai đọc được" thành một trang mà COO nhìn năm giây là trả lời được câu
hỏi của mình: headline là insight, chart đúng loại, annotation tại chỗ, thứ tự kết luận trước, và dám bỏ
những chart không phục vụ câu hỏi.

## Đề bài

Bộ `bike-sharing-uci`, `day.csv` (731 ngày, 2011-2012). Slide gốc gửi COO có một pie theo mùa, một chart dual
axis lượt thuê và nhiệt độ, một bảng số dày đặc. COO hỏi lại: **"Năm nay mình làm tốt hơn không, và cái gì
làm mình mất khách?"** Mở `starter/redesign.ipynb`:

1. Chạy cell slide gốc, ghi lại lỗi của từng phần.
2. `yoy_by_month(day)`: tổng lượt theo tháng lịch của hai năm, cột `prev`, `curr`, `growth`.
3. `weather_effect(day)`: lượt thuê theo `weathersit` so với ngày trời quang **cùng tháng** (trừ mùa vụ và
   tăng trưởng), trừ 1.
4. `build_page(day)`: vẽ trang mới và trả `Figure`: `suptitle` là headline có con số, 2-4 chart có tiêu đề,
   không pie, không dual axis, không bảng, ít nhất một annotation. Số trên trang tính từ `day`.
5. Viết `starter/MEMO.md` theo khung (150-500 từ).

## Tiêu chí đạt

- `yoy_by_month` đúng trên dữ liệu nhỏ (tháng trống là 0, dùng `dteday` chứ không dùng `yr`).
- `weather_effect` dùng mức nền của từng tháng, bỏ ngày ở tháng không có ngày trời quang.
- `build_page` qua các kiểm tra cấu trúc trên dữ liệu sinh ngẫu nhiên.
- Trên bộ thật: 1 243 103 lượt năm 2011, 2 049 576 năm 2012; tháng tăng mạnh nhất là tháng 3 (+157%), chậm
  nhất tháng 6; ngày mây/sương −13.7%, ngày mưa/tuyết nhẹ −56.5% so với ngày quang cùng tháng.
- `MEMO.md` không còn TODO, đủ mục, dòng đầu là headline có con số. Thiết kế chấm theo rubric trong
  `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Viết headline trước khi vẽ. Nếu một chart không giúp trả lời một trong hai câu hỏi của COO, bỏ nó khỏi trang
(để ở phụ lục hoặc dashboard). Hai năm theo tháng là so sánh cùng kỳ: hai đường trên cùng trục, nhãn trực
tiếp ở cuối đường, không cần legend.

### Gợi ý 2

So TB lượt thuê ngày mưa với TB ngày quang trên cả hai năm là so khập khiễng: ngày mưa rơi vào tháng nào,
năm nào? Chia cho mức nền của chính tháng đó trước khi lấy trung bình. Với số âm, bar ngang bắt đầu từ 0 và
ghi nhãn phần trăm ngay trên bar.
