---
title: Điều tra 33 cửa hàng giảm doanh số khi chuỗi vẫn tăng, và viết memo cho Head of Retail Operations
level: advanced
services: []
files:
  - path: starter/store_decline.ipynb
    note: 3 hàm TODO + điều tra tự do
  - path: starter/MEMO.md
    note: Memo một trang - headline, phân rã, nguyên nhân theo nhóm, việc cần làm, giới hạn
  - path: tests/test_store_decline.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py store-sales
  - uv run jupyter lab tracks/data-analyst/modules/13-business-financial-analytics/exercises/advanced/01-store-decline-investigation/starter/store_decline.ipynb
  - uv run pytest tracks/data-analyst/modules/13-business-financial-analytics/exercises/advanced/01-store-decline-investigation -q
---

## Mục tiêu

Làm một cuộc điều tra root cause hoàn chỉnh trên dữ liệu bán lẻ: kiểm con số có so được không, phân rã thay đổi của
từng cửa hàng thành các thành phần, tìm nguyên nhân chung bằng so sánh nhóm có đối chứng, tách phần dữ liệu không
trả lời được, rồi viết memo dẫn tới hành động cụ thể cho từng nhóm cửa hàng.

## Đề bài

Head of Retail Operations hỏi: **"6 tháng đầu 2015 chuỗi tăng 3.4% so với cùng kỳ, nhưng 33 cửa hàng giảm hơn 10%.
Vì sao? Cửa hàng nào cần can thiệp, can thiệp thế nào?"** Dữ liệu: bộ `store-sales` (Rossmann), `train.csv` và
`store.csv`; kỳ so sánh 01/01-30/06/2014 và 01/01-30/06/2015. Mở `starter/store_decline.ipynb`:

1. `store_yoy(train, p0, p1)`: mỗi cửa hàng một dòng với tổng hai kỳ, tăng trưởng, và ba thành phần nhân với nhau
   ra đúng tăng trưởng: số ngày mở cửa, lượt khách mỗi ngày mở cửa, chi tiêu mỗi khách.
2. `competition_timing(stores, p0, p1)`: đối thủ gần nhất mở trước, trong, giữa, hay sau hai kỳ.
3. `group_growth(yoy, labels)`: tăng trưởng gộp, median và tỉ lệ cửa hàng giảm hơn 10% theo nhóm.
4. Điều tra tự do trong các cell `explore`: thành phần nào giảm, nhóm đối thủ mới so với nhóm đối chứng, khoảng cách
   tới đối thủ, cửa hàng đóng cửa dài ngày, các cửa hàng chưa có lời giải thích (xem doanh số theo tháng). Chọn 1-3
   chart cho memo, tiêu đề mỗi chart là kết luận có con số.
5. Viết `starter/MEMO.md` theo khung có sẵn (200-600 từ, đủ các mục, dòng đầu là headline có con số).

## Tiêu chí đạt

- `store_yoy` đúng trên dữ liệu nhỏ: kỳ tính cả hai mút, chỉ cửa hàng có ở cả hai kỳ, ba thành phần nhân lại đúng
  bằng tăng trưởng; không sửa dữ liệu đầu vào.
- `competition_timing` gán đủ sáu nhãn, thiếu tháng hoặc năm là `unknown`; `group_growth` lấy giao của hai index,
  tăng trưởng gộp (không phải trung bình tăng trưởng), sắp tăng dần.
- Trên bộ thật: 1 115 cửa hàng, chuỗi +3.353%; 33 cửa hàng giảm hơn 10% (giảm nhiều nhất là cửa hàng 91), 30 trong
  số đó mất hơn 10% lượt khách mỗi ngày; nhóm đối thủ mở 07-12/2014 (39 cửa hàng) −3.90%, nhóm đối thủ mở trước 2014
  (653 cửa hàng) +3.76%.
- `MEMO.md` không còn TODO, đủ mục, headline có con số. Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Thứ tự hợp lý: con số có so được không (cửa hàng nào thiếu dữ liệu, đóng cửa) → thành phần nào giảm (ngày mở cửa,
khách, giỏ) → nguyên nhân chung nào giải thích được nhiều cửa hàng (đối thủ, đóng cửa) → **nhóm đối chứng** cho
nguyên nhân đó → phần còn lại không giải thích được. Đừng dừng ở "18 cửa hàng có đối thủ mới": cửa hàng có đối thủ từ
lâu tăng bao nhiêu?

### Gợi ý 2

Với cửa hàng không có lời giải thích trong dữ liệu, vẽ doanh số theo tháng 2014-2015: cú giảm dần dần hay tụt thành
bậc ở một tháng cụ thể? Tụt thành bậc gợi ý một sự kiện tại chỗ, và việc cần làm là hỏi người ở hiện trường, không
phải phân tích thêm.
