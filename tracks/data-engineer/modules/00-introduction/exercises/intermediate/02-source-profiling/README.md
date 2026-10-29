---
title: Đo data collection considerations bằng số - profile bốn nguồn thật
level: intermediate
services: []
files:
  - path: starter/source_profile.ipynb
    note: 7 hàm TODO + 2 biểu đồ; hàm nạp dữ liệu có sẵn
  - path: tests/test_source_profile.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py nasa-http-logs
  - uv run python data/download_dataset.py air-quality-uci
  - uv run pytest tracks/data-engineer/modules/00-introduction/exercises/intermediate/02-source-profiling -q
---

## Mục tiêu

Biến bảng "data collection considerations" của lý thuyết thành **số đo**: viết một profiler dùng lại được
(velocity, độ đều, trùng, thiếu, sentinel, dung lượng), chạy trên log, IoT và hai API thật, rồi đưa ra khuyến
nghị thu thập cho từng nguồn có lý do bằng con số thay vì cảm giác.

## Đề bài

Nguồn: `nasa-http-logs` và `air-quality-uci` (cell đầu tự tải), cộng `open-meteo` (bài basic 01) và
`usgs-earthquakes` (bài intermediate 01) nếu bạn đã thu thập. Các hàm nạp (`load_nasa`, `load_air`,
`load_weather`, `load_usgs`) có sẵn trong notebook.

Mở `starter/source_profile.ipynb`, viết:

1. `profile(df, ts_col, key=None, sentinels=())`: 14 chỉ số trong bảng của notebook (velocity, khoảng lặng,
   trùng dòng, trùng khoá, sentinel, cột thiếu nhiều nhất). Không giả định dữ liệu đã sắp xếp.
2. `gaps(df, ts_col, min_gap_s)`: danh sách khoảng lặng dài hơn ngưỡng.
3. `footprint(df, raw_bytes, path)`: ghi Parquet zstd, đo byte mỗi dòng thô vs Parquet.
4. `yearly_volume_gb(rows_per_day, bytes_per_row)`: ngoại suy một năm.
5. `compare(profiles)` và `write_clean(table, out_dir)`: bảng so sánh, ghi `data/clean/source-profiles/profiles.parquet`.
6. Chạy các cell `explore`, vẽ ít nhất 2 biểu đồ (velocity trục log; byte mỗi dòng).
7. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook. Câu hỏi gồm khuyến nghị thu thập cho từng nguồn (batch/streaming, pull/push, full/incremental, cảnh báo).

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: các chỉ số đúng trên bảng 6 dòng, sentinel chỉ tính khi khai báo, đúng cả khi
  dữ liệu chưa sắp xếp, `footprint` ghi đè.
- Trên dữ liệu thật: log NASA ~68 600 dòng/ngày, khoảng lặng dài nhất 1 326 giây lúc 1995-07-13 23:48:59 UTC,
  835 dòng trùng hoàn toàn; IoT đúng 24 dòng/ngày, 16 701 ô `-200`, `NMHC(GT)` thiếu ~90%; CSV IoT ~84 byte/dòng
  và Parquet nhỏ hơn ít nhất 2 lần.
- Ít nhất 2 cell `explore` vẽ biểu đồ.

## Gợi ý

### Gợi ý 1

Sắp `ts` trước, `step = ts.diff().dt.total_seconds()`; `step.idxmax()` là vị trí dòng **sau** khoảng lặng,
dòng trước đó là điểm bắt đầu. `df.duplicated(key)` đếm dòng trùng khoá với một dòng trước nó.

### Gợi ý 2

Sentinel tính là thiếu: `values.isna() | values.isin(list(sentinels))`, rồi `.mean()` theo cột. Với
`footprint`, đo `path.stat().st_size` **sau** khi ghi. Đọc khuyến nghị ở phần 5–6 của lý thuyết module:
"mặc định batch, pull, incremental; streaming chỉ khi có yêu cầu latency bằng con số".
