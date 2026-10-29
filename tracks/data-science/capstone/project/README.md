# Olist Customer Experience

> README này là bản nháp cho repo portfolio của bạn. Viết lại dần sau mỗi milestone; sau M07, phần
> đầu trang là khuyến nghị cuối cùng.

Review 1–2 sao của Olist đến từ đâu, và làm gì để giảm nó: EDA và metric → forecast → model rủi ro lúc
giao vận chuyển → causal → thiết kế A/B → MLflow + FastAPI → memo cho ban điều hành.

Thư mục này ban đầu chỉ có README. Bạn tự tạo code theo khung dưới đây; capstone không có lời giải mẫu.

## Quick start

```bash
uv run python data/download_olist.py
export PYTHONPATH=tracks/data-science/capstone/project/src
uv run pytest tracks/data-science/capstone/project/tests -q
uv run jupyter lab tracks/data-science/capstone/project/notebooks
```

## Cấu trúc gợi ý

```
project/
├── README.md
├── src/
│   └── olist_cx/
│       ├── __init__.py
│       ├── tables.py        # M01: orders_cx theo định nghĩa dùng chung
│       ├── series.py        # M02: daily_orders, backtest
│       ├── split.py         # mốc 2018-01-01 / 2018-04-01 / 2018-09-01
│       └── features.py      # M03: features_at("purchase" | "carrier" | "delivered")
├── notebooks/
│   ├── m01_eda.ipynb
│   ├── m02_forecast.ipynb
│   ├── m03_model.ipynb
│   ├── m04_causal.ipynb
│   └── m05_experiment.ipynb
├── serving/                 # M06
│   ├── README.md
│   ├── train.py             # huấn luyện + MLflow + registry
│   ├── app.py               # FastAPI: /predict, /health
│   └── batch_score.py       # chấm theo giờ, idempotent
├── reports/
│   ├── METRICS.md           # M01
│   ├── MEMO_EDA.md          # M01
│   ├── FORECAST.md          # M02
│   ├── MODEL_CARD.md        # M03, M06
│   ├── CAUSAL.md            # M04
│   ├── EXPERIMENT_DESIGN.md # M05 (cập nhật sau M03)
│   ├── NUMBERS.md           # M07
│   ├── DESIGN.md            # M07
│   └── MEMO.md              # M07
├── artifacts/               # parquet, hình, mlflow.db, scores: không commit
└── tests/
    ├── conftest.py          # fixture dữ liệu nhỏ; skip khi chưa tải Olist
    ├── test_tables.py
    ├── test_features.py
    └── test_serving.py
```

| Thư mục | Milestone | Nội dung |
| --- | --- | --- |
| `src/olist_cx/` | M01–M03, M06 | định nghĩa và feature dùng chung, có test |
| `notebooks/` | M01–M05 | phân tích, gọi hàm trong `src/`, không chép logic |
| `serving/` | M06 | train, registry, API, batch |
| `reports/` | tất cả | tài liệu cho người đọc: metric, model card, thiết kế thí nghiệm, memo |
| `tests/` | tất cả | `uv run pytest tracks/data-science/capstone/project/tests -q` |

Thêm `artifacts/` vào `.gitignore` của repo portfolio. Test không được cần mạng; phần chạy trên Olist
thật dùng `pytest.skip` khi `data/raw/olist_orders_dataset.csv` chưa có.

## Con số chính

_(Bảng: con số, giá trị, link notebook. Ví dụ: tỉ lệ review xấu, ATT của giao trễ, precision của chính
sách cảnh báo, cỡ mẫu thí nghiệm.)_

## Decisions

_(Thời điểm dự đoán và lý do, cách chia thời gian, tập điều chỉnh của phân tích nhân quả, đơn vị random,
vì sao batch, luật hay model.)_

## Giới hạn

_(Dữ liệu quan sát, chỉ đơn có review, không có thí nghiệm thật, giả định tiền chưa kiểm chứng.)_
