---
title: EDA có câu hỏi trên Telco churn - khách nào rời bỏ, nên nhắm nhóm nào
level: intermediate
services: []
files:
  - path: starter/churn_eda.ipynb
    note: 4 hàm TODO + EDA theo câu hỏi, đề xuất phân khúc
  - path: tests/test_churn_eda.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py telco-churn
  - uv run jupyter lab tracks/data-analyst/modules/07-descriptive-eda/exercises/intermediate/01-telco-churn-eda/starter/churn_eda.ipynb
  - uv run pytest tracks/data-analyst/modules/07-descriptive-eda/exercises/intermediate/01-telco-churn-eda -q
---

## Mục tiêu

Chạy một vòng EDA bắt đầu từ câu hỏi kinh doanh và kết thúc bằng một đề xuất có con số: làm sạch có hiểu biết
(ô trống là ai), bảng tỉ lệ có n và tỉ trọng, so phân phối bằng median/IQR, phân tầng để không đọc nhầm biến gây
nhiễu, và chọn phân khúc theo tác động chứ không theo tỉ lệ cao nhất.

## Đề bài

Head of Retention có ngân sách cho **một** chương trình giữ chân và hỏi: *"Khách rời bỏ là ai? Nên nhắm nhóm nào
để giảm nhiều khách rời nhất?"* Dữ liệu: bộ `telco-churn` (7 043 khách). Mở `starter/churn_eda.ipynb`:

1. `clean_telco(raw)`: bản sao với `TotalCharges` kiểu `float` (ô trống hoặc chỉ có khoảng trắng → NaN, giá trị
   không phải số → lỗi), `SeniorCitizen` thành `"Yes"`/`"No"`, thêm cột bool `churned`.
2. `add_tenure_band(df)`: thêm cột categorical có thứ tự `tenure_band` gồm `0-6`, `7-12`, `13-24`, `25-48`,
   `49-72` (cận phải tính vào nhóm).
3. `rate_table(df, col, target="churned")`: cột `n`, `churned`, `rate`, `share_of_n`, `share_of_churned`, `lift`,
   index tên `col`, sắp `rate` giảm dần, bỏ nhóm categorical rỗng.
4. `compare_numeric(df, col, target="churned")`: index `False`/`True` (tên `target`), cột `n`, `mean`, `median`,
   `std`, `iqr`, `skew`.
5. Chạy các cell `explore` theo thứ tự: ô trống là ai, bảng tỉ lệ cho 7 biến, ECDF ba biến số, phân tầng
   `TotalCharges` theo nhóm tenure, so các phân khúc ứng viên. Viết ra headline, nhóm đề xuất, điều chưa biết.
   Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook.

Các hàm không được sửa DataFrame đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ sinh trong test pass: kiểu cột, ô trống, lỗi khi gặp chuỗi lạ, nhóm tenure ở cận, thứ tự
  cột và cách sắp, nhóm rỗng bị bỏ, NaN không được đếm vào `n`.
- Trên bộ thật: 1 869 khách rời bỏ; 11 ô `TotalCharges` trống đều là khách `tenure = 0`; month-to-month churn
  42.71% và chiếm 88.55% số khách rời; nhóm 0–6 tháng churn 52.94%; median tenure 38 (ở lại) và 10 tháng (rời).
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`df.groupby(col, observed=True)[target]` rồi `size()` và `sum()`. Cột bool cộng ra số `True`. Tỉ lệ churn chung là
`churned.sum() / n.sum()` của chính bảng, không cần tính lại từ `df`.

### Gợi ý 2

Khi một biến số (như `TotalCharges`) là tích của biến khác (`tenure`) với một thứ gì đó, so nó giữa hai nhóm có
`tenure` rất khác nhau là so táo với cam. Giữ `tenure` cố định (so trong từng `tenure_band`) rồi mới kết luận.
