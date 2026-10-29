---
title: API phân trang, rate limit và thu thập incremental - động đất toàn cầu 2024 (USGS)
level: intermediate
services: []
files:
  - path: starter/earthquakes.ipynb
    note: 6 hàm TODO + 2 biểu đồ; fetch_json có sẵn; cell explore gọi API thật
  - path: starter/report.md
    note: Báo cáo 4 mục, đang là TODO
  - path: tests/test_earthquakes.py
    note: Không sửa; dùng server USGS giả, không gọi mạng
run:
  - uv run pytest tracks/data-engineer/modules/00-introduction/exercises/intermediate/01-paginated-incremental-api -q
---

## Mục tiêu

Viết một bộ thu thập API đúng kiểu production: duyệt **phân trang**, **tự giới hạn tốc độ**, lưu từng trang
thô, và chạy **incremental theo thời điểm cập nhật** (không phải thời điểm xảy ra) với state chỉ ghi khi
lượt chạy thành công. Rồi chứng minh bằng chính dữ liệu vì sao chọn `updated` làm watermark là bắt buộc.

## Đề bài

API [USGS FDSN Event](https://earthquake.usgs.gov/fdsnws/event/1/) (public domain, không cần key). Mốc
ghim: M ≥ 4.5 toàn cầu, `starttime=2024-01-01`, `endtime=2025-01-01`, `orderby=time-asc`, trang 1 000
bản ghi (`offset` bắt đầu từ 1).

Mở `starter/earthquakes.ipynb`, làm lần lượt (đặc tả chi tiết trong markdown của notebook):

1. `page_params(...)`: tham số một trang, thêm `updatedafter` khi có watermark.
2. `fetch_pages(get, params, page_size, min_interval, sleep, clock)`: generator duyệt `offset`, dừng ở trang
   ngắn, hai request cách nhau ít nhất `min_interval` giây.
3. `collect(get, raw_dir, ...)`: ghi `data/raw/usgs-earthquakes/run-NNN/page-NNN.json`; lần đầu lấy hết,
   lần sau chỉ lấy bản ghi có `updated` ≥ watermark; `state.json` chỉ cập nhật khi mọi trang đã ghi xong.
4. `load_events(raw_dir)`: gộp mọi lượt thành bảng một dòng mỗi `id` (giữ bản `updated` mới nhất), thời gian UTC,
   tách `region` từ `place`.
5. `insights(df)`: 14 con số, gồm độ trễ cập nhật và hệ số b của luật Gutenberg–Richter.
6. `write_clean(df, out_dir)`: ghi đè `data/clean/usgs-earthquakes/events.parquet`.
7. Chạy cell `explore: thu thập` (lần đầu ~7 request; chạy lại cell là một lượt incremental), vẽ ít nhất
   2 biểu đồ, viết `starter/report.md`, trả lời câu hỏi về watermark.

## Tiêu chí đạt

- Test với server giả pass: offset 1, 3, 5...; dừng ở trang ngắn; nghỉ đúng 1 giây giữa các request; lượt 2
  gửi `updatedafter` và chỉ nhận bản ghi mới/sửa; bản sửa thắng khi gộp; lỗi giữa chừng không làm hỏng state.
- Trên dữ liệu thật: ~6 400 trận, `id` không trùng; trận lớn nhất M7.5 Noto (Nhật) ngày 2024-01-01; tháng 4 nhiều
  trận nhất; hơn 95% bản ghi được sửa sau hơn 30 ngày; b trong khoảng 1,0–1,3.
- `write_clean` gọi hai lần vẫn đúng số dòng. Ít nhất 2 cell `explore` vẽ biểu đồ.
- `report.md` đủ 4 mục, không còn TODO, Insight có số và trả lời câu hỏi watermark.

## Gợi ý

### Gợi ý 1

`fetch_pages`: giữ `last = clock()` ngay trước mỗi request; trước request kế tiếp
`wait = min_interval - (clock() - last)`, `sleep(wait)` nếu dương. Dùng `yield payload` rồi kiểm tra
`len(payload["features"]) < page_size` để `return`.

### Gợi ý 2

`collect`: duyệt `enumerate(fetch_pages(...), start=1)`, ghi từng trang ngay khi nhận (đừng giữ cả năm trong
bộ nhớ), cộng dồn `max(updated)`, và chỉ ghi `state.json` sau vòng lặp. Upsert khi gộp:
`df.sort_values("updated").drop_duplicates("id", keep="last")`.
