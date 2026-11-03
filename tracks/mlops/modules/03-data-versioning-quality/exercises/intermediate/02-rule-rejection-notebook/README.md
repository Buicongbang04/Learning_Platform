---
title: Đo tỉ lệ dòng bị loại theo từng luật trên NYC TLC 2019-01 thật
level: intermediate
services: []
files:
  - path: starter/rejection.ipynb
    note: 4 hàm TODO, cell explore
  - path: tests/test_rejection.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py nyc-tlc
  - uv run pytest tracks/mlops/modules/03-data-versioning-quality/exercises/intermediate/02-rule-rejection-notebook -q
---

## Mục tiêu

Biến các luật chất lượng thành số đo: mỗi luật loại bao nhiêu dòng trên dữ liệu thật, bao nhiêu dòng giữ lại, để quyết định luật nào là
lỗi hợp đồng (chặn cả lô) và luật nào chỉ là lọc.

## Đề bài

Làm việc trong `starter/rejection.ipynb` trên tháng 2019-01 của bộ `nyc-tlc` (tải bằng lệnh đầu của `run`). Điền 4 hàm trong các cell
chấm điểm; hằng `MONTH`, `SAMPLE_N=200_000`, `SEED=0`, `COLUMNS`, `RULES` đã có sẵn.

- `load_sample(path, n, seed)`: chỉ đọc các cột trong `COLUMNS` (không đọc cả bảng 19 cột), lấy mẫu `n` dòng xác định theo `seed`
  bằng `DataFrame.sample(n=..., random_state=seed)` trên toàn bộ tháng.
- `rule_masks(df, month)`: trả dict, **đúng thứ tự khoá** như `RULES`, mỗi giá trị là Series boolean (True = dòng vi phạm):
  - `duration`: `dropoff <= pickup`
  - `distance`: `trip_distance <= 0`
  - `pickup_month`: `pickup` ngoài `[đầu tháng, đầu tháng sau)`
  - `zone_range`: `PULocationID` hoặc `DOLocationID` ngoài 1 đến 265
  - `zone_unknown`: `PULocationID` hoặc `DOLocationID` là 264 hoặc 265
- `rejection_counts(df, month)`: số dòng vi phạm từng luật, mỗi luật tính độc lập (một dòng có thể tính ở nhiều luật).
- `rows_kept(df, month)`: số dòng không vi phạm luật nào.

Chạy các cell `explore` để thấy tỉ lệ và biểu đồ, rồi làm phần trắc nghiệm trong app. Test kiểm hàm trên khung dữ liệu nhỏ và kiểm đúng con số trên mẫu thật.

## Tiêu chí đạt

- Test pass trên khung nhỏ (kể cả dòng vi phạm nhiều luật) và trên mẫu thật.
- Tự kiểm (test không chạy cell `explore`): notebook chạy trọn vẹn kể cả cell `explore`, không lỗi.
- Trắc nghiệm đúng ít nhất 5/6 câu.

## Gợi ý

### Gợi ý 1

`pd.read_parquet(path, columns=COLUMNS)` đọc cột, không đọc cả bảng. Ghép các mask bằng `pd.concat(masks.values(), axis=1).any(axis=1)`.

### Gợi ý 2

Cửa sổ tháng nửa mở: `start = pd.Timestamp(month + "-01")`, `end = start + pd.offsets.MonthBegin(1)`.
Dùng `Series.between(1, 265)` rồi phủ định để bắt ngoài khoảng.
