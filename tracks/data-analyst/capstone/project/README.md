# Dunnhumby Retail Analytics

> README này là bản nháp cho repo portfolio của bạn. Viết lại dần sau mỗi milestone; sau M07, phần đầu
> trang là khuyến nghị cuối cùng cho ban điều hành.

Doanh thu của một chuỗi siêu thị đến từ đâu, khách hàng nào tạo ra nó, và campaign/coupon có hiệu quả
không: nạp và làm sạch → SQL → star schema và metric → dashboard → RFM, cohort, market basket → campaign
như thí nghiệm có giới hạn → memo cho ban điều hành. Dữ liệu thật: dunnhumby "The Complete Journey",
2 500 hộ có thẻ khách hàng trong 711 ngày.

Thư mục này ban đầu chỉ có README. Bạn tự tạo code theo khung dưới đây; capstone không có lời giải mẫu.

## Quick start

```bash
uv run python data/download_dataset.py dunnhumby-complete-journey
export PYTHONPATH=tracks/data-analyst/capstone/project/src
uv run python -m dunnhumby_da.load                       # M01: tạo artifacts/dunnhumby.duckdb
uv run pytest tracks/data-analyst/capstone/project/tests -q
uv run streamlit run tracks/data-analyst/capstone/project/dashboards/streamlit_app.py   # M04
```

## Cấu trúc gợi ý

```
project/
├── README.md
├── src/
│   └── dunnhumby_da/
│       ├── __init__.py
│       ├── load.py          # M01: CSV → DuckDB, ép kiểu, chạy lại được
│       ├── export_pg.py     # M04: đẩy mart sang Postgres cho Metabase/Superset
│       ├── segments.py      # M05: rfm_scores, pair_rules
│       └── campaign.py      # M06: pre_post
├── sql/
│   ├── checks/              # M01: mỗi tệp một kiểm toàn vẹn, mong đợi 0 dòng vi phạm
│   ├── m02/                 # M02: một tệp một câu hỏi business
│   ├── m05/
│   └── m06/
├── dbt/                     # M03: staging + marts (hoặc sql/model/ nếu không dùng dbt)
├── notebooks/
│   ├── m01_load_clean.ipynb
│   ├── m02_sql_eda.ipynb
│   ├── m05_segments.ipynb
│   └── m06_campaign.ipynb
├── dashboards/
│   ├── streamlit_app.py     # M04
│   └── bi_export/           # M04: tệp xuất Metabase/Superset
├── reports/
│   ├── DATA_DICTIONARY.md   # M01
│   ├── CLEANING_LOG.md      # M01
│   ├── SQL_ANSWERS.md       # M02
│   ├── MODEL.md             # M03
│   ├── METRICS.md           # M03, nguồn sự thật cho mọi metric
│   ├── DASHBOARD.md         # M04
│   ├── SEGMENTS.md          # M05
│   ├── CAMPAIGN.md          # M06
│   ├── NUMBERS.md           # M07
│   ├── MEMO.md              # M07
│   ├── QA_PREP.md           # M07
│   ├── slides.pdf           # M07
│   └── img/
├── artifacts/               # dunnhumby.duckdb, parquet, hình tạm: không commit
└── tests/
    ├── conftest.py          # fixture nhỏ tự tạo; skip phần dữ liệu thật khi chưa tải
    ├── test_load.py
    ├── test_model.py
    ├── test_segments.py
    └── test_campaign.py
```

| Thư mục | Milestone | Nội dung |
| --- | --- | --- |
| `src/dunnhumby_da/` | M01, M04–M06 | hàm dùng chung, có test |
| `sql/` | M01, M02, M05, M06 | câu SQL chạy lại được, comment ghi câu hỏi và grain |
| `dbt/` | M03 | star schema + test |
| `notebooks/` | M01, M02, M05, M06 | phân tích, gọi hàm trong `src/` và SQL trong `sql/`, không chép logic |
| `dashboards/` | M04 | Streamlit + tệp xuất BI |
| `reports/` | tất cả | tài liệu cho người đọc |
| `tests/` | tất cả | `uv run pytest tracks/data-analyst/capstone/project/tests -q` |

Thêm `artifacts/` vào `.gitignore` của repo portfolio. Không commit dữ liệu thô dunnhumby (giấy phép cho
phép tải từ Kaggle, repo chỉ chứa code). Test không cần mạng; phần chạy trên dữ liệu thật dùng
`pytest.skip` khi `data/raw/dunnhumby-complete-journey/` chưa có.

## Khuyến nghị

_(Sau M07: 2–3 hành động, ai làm, khi nào, metric đo.)_

## Con số chính

_(Bảng: con số, giá trị, link SQL/notebook. Ví dụ: doanh thu ròng, tỷ trọng ngành, mức tập trung cửa
hàng, số hộ win-back, cặp cross-sell, chênh lệch hộ được gán campaign.)_

## Decisions

_(Định nghĩa doanh thu và cách kiểm, lọc dòng không hợp lệ, xử lý `QUANTITY` của xăng, quy ước "tháng"
4 tuần, ngưỡng quy mô cửa hàng, cấp commodity cho market basket, cách đọc campaign.)_

## Giới hạn

_(Panel 2 500 hộ có thẻ, `DAY` không phải ngày lịch, 32% hộ có nhân khẩu học và không đại diện, campaign
không ngẫu nhiên.)_
