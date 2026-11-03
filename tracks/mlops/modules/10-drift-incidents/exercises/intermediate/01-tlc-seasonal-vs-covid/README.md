---
title: Drift mùa vụ và drift COVID trên NYC TLC thật
level: intermediate
services: []
files:
  - path: starter/tlc_drift.ipynb
    note: 6 hàm TODO, cell explore
  - path: tests/test_tlc_drift.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py nyc-tlc
  - uv run python data/download_dataset.py nyc-tlc-2020
  - uv run pytest tracks/mlops/modules/10-drift-incidents/exercises/intermediate/01-tlc-seasonal-vs-covid -q
---

## Mục tiêu

So hai cặp tháng của dữ liệu thật: 2019-07 sang 2019-12 (đổi mùa) và 2020-02 sang 2020-04 (cú sốc COVID). Đo drift từng feature, đo chất lượng model ETA, và thấy rằng kích cỡ drift
đầu vào không tiên đoán được kích cỡ thiệt hại.

## Đề bài

Làm việc trong `starter/tlc_drift.ipynb`. Hằng `MONTHS`, `SAMPLE_N=100_000`, `SEED=0`, `COLUMNS`, `FEATURES`, `MODEL_FEATURES` đã có sẵn. Điền 6 hàm trong các cell chấm điểm:

- `load_sample(path, n, seed)`: chỉ đọc các cột trong `COLUMNS`, lấy `n` dòng bằng `DataFrame.sample(n=..., random_state=seed)` trên cả tháng.
- `prepare(df)`: trả bản sao (không sửa đầu vào) có thêm `duration_min` (`dropoff - pickup` tính bằng phút) và `hour` (giờ của `pickup`), rồi chỉ giữ dòng thoả cả bốn luật:
  `0 < duration_min < 180`, `trip_distance > 0`, `fare_amount > 0`; kết quả `reset_index(drop=True)`.
- `psi(reference, current, bins=10, eps=1e-4)`: bỏ NaN ở từng tập; biên bin là quantile (`np.linspace(0, 1, bins + 1)`) của `reference`, qua `np.unique`, hai biên ngoài cùng đặt `-inf` và `+inf`;
  tỉ lệ mỗi bin chặn dưới bằng `eps` (`np.clip`); $$\mathrm{PSI} = \sum_i (c_i - r_i)\ln(c_i / r_i)$$ với $$r_i$$, $$c_i$$ là tỉ lệ của reference và current.
- `psi_by_column(reference, current, columns=FEATURES)`: dict `{cột: PSI}` theo đúng thứ tự `columns`.
- `missing_share(df, column)`: tỉ lệ NaN của một cột (float).
- `eta_mae(reference, current, seed=SEED)`: `train_test_split(reference, test_size=0.2, random_state=seed)`; `HistGradientBoostingRegressor(random_state=seed, max_iter=100)` học `duration_min` từ
  `MODEL_FEATURES` trên 80%; trả `(MAE trên 20% holdout của reference, MAE trên toàn bộ current)`.

Chạy các cell `explore`: chúng tải dữ liệu nếu thiếu, in bảng PSI hai cặp tháng, MAE, đối chiếu PSI với Evidently và vẽ biểu đồ (tạo `psi_seasonal_vs_covid.png`). Cell Evidently có dòng vá tương thích
`pandas` 3 (xem phần 0 của lý thuyết). Sau đó làm phần trắc nghiệm trong app. Test chạy mẫu thật của cả bốn tháng (mỗi tháng đọc có kiểm sha256; tự skip nếu chưa tải).

## Tiêu chí đạt

- Test pass trên khung nhỏ (luật lọc, PSI tính tay 4 bin, model phát hiện quan hệ đã đổi) và trên mẫu thật (PSI hour 2020-02 sang 2020-04 ≈ 0.152, MAE 3.10 sang 5.01).
- Tự kiểm (test không chạy cell `explore`): notebook chạy trọn vẹn kể cả cell `explore`, không lỗi.
- Trắc nghiệm đúng ít nhất 6/7 câu.

## Gợi ý

### Gợi ý 1

`np.quantile(reference, np.linspace(0, 1, bins + 1))`, rồi `np.histogram(x, edges)[0] / len(x)` cho tỉ lệ từng bin. `np.unique` loại biên trùng khi dữ liệu có nhiều giá trị lặp (vd. `hour`).

### Gợi ý 2

`(df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]).dt.total_seconds() / 60` cho số phút. `train_test_split` chạy trên DataFrame và giữ cột; dự đoán xong tính MAE bằng `np.abs(pred - y).mean()`.
