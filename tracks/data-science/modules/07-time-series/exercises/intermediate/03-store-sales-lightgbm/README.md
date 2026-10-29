---
title: LightGBM với lag feature cho Rossmann, không leakage
level: intermediate
services: []
files:
  - path: starter/lgbm_lags.ipynb
    note: 5 hàm TODO + phần nhận xét
  - path: tests/test_lgbm_lags.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py store-sales
  - uv run jupyter lab tracks/data-science/modules/07-time-series/exercises/intermediate/03-store-sales-lightgbm/starter/lgbm_lags.ipynb
  - uv run pytest tracks/data-science/modules/07-time-series/exercises/intermediate/03-store-sales-lightgbm -q
---

## Mục tiêu

Biến bài toán dự báo thành bài toán supervised learning đúng cách: lag và rolling feature lùi đủ
horizon, một model chung cho nhiều cửa hàng, biến biết trước (lịch khuyến mãi) được dùng, biến
không biết trước (`Customers`) bị loại. Thấy tận mắt leakage làm con số đẹp giả như thế nào.

## Đề bài

Rossmann, 50 cửa hàng id nhỏ nhất trong số cửa hàng đủ mọi ngày, dự báo 42 ngày (6 tuần). Mở
`starter/lgbm_lags.ipynb`:

1. `select_stores(train, n_stores=50)`.
2. `make_features(df, horizon=42)`: đúng các cột `FEATURES` theo bảng định nghĩa trong notebook.
   Mọi feature từ `Sales` chỉ dùng doanh thu tới `t − horizon`, tính riêng trong từng cửa hàng,
   ngày đóng cửa là `NaN` chứ không phải 0.
3. `fit_predict(df, cutoff, horizon)` với `LGBM_PARAMS` cho sẵn, target `log1p(Sales)`, chỉ train
   trên ngày mở cửa trước cutoff.
4. `seasonal_naive_last_week(df, cutoff, horizon)` và `evaluate(df, pred)` (MAE, RMSPE).
5. Chạy các cell `explore`: backtest 3 origin, bản có leakage, sai số theo tuần, feature importance.
   Viết nhận xét.

## Tiêu chí đạt

- Feature không đổi khi sửa doanh thu tương lai, sửa `Customers`, hay sửa doanh thu cửa hàng khác.
- `fit_predict` cho cùng kết quả khi doanh thu của giai đoạn test bị xoá (đúng như lúc dự báo thật).
- Trên dữ liệu thật: 47 100 dòng, seasonal naive MAE 1 501.3 ở origin 2015-06-20, LightGBM MAE nhỏ
  hơn 75% con số đó.
- Nhận xét giải thích vì sao baseline "tuần trước" thua và vì sao con số của bản có leakage vô dụng.

## Gợi ý

### Gợi ý 1

`df.Sales.where(df.Open == 1).groupby(df.Store).shift(k)` lùi k ngày trong từng cửa hàng. Gọi
`.shift` trên cả cột không qua `groupby` sẽ kéo doanh thu cửa hàng trước sang cửa hàng sau.

### Gợi ý 2

Rolling cũng phải trong từng cửa hàng và bắt đầu từ cột **đã lùi**:
`lag_h.groupby(df.Store).transform(lambda x: x.rolling(28, min_periods=1).mean())`.
`x.rolling(28).mean().shift(horizon)` cũng đúng; `x.rolling(28).mean()` không lùi là leakage.
