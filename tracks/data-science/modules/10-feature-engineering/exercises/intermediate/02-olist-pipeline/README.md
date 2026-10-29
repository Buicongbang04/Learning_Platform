---
title: Pipeline và ColumnTransformer cho bài toán review xấu
level: intermediate
services: []
files:
  - path: starter/pipeline.ipynb
    note: 3 hằng + 2 hàm TODO
  - path: tests/test_pipeline.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/10-feature-engineering/exercises/intermediate/02-olist-pipeline/starter/pipeline.ipynb
  - uv run pytest tracks/data-science/modules/10-feature-engineering/exercises/intermediate/02-olist-pipeline -q
---

## Mục tiêu

Dựng một pipeline sklearn hoàn chỉnh trên Olist thật: chọn cột hợp lệ tại thời điểm dự đoán, mã hoá
từng loại cột đúng cách trong một `ColumnTransformer`, fit **chỉ** trên train, và đọc điểm validation
với con mắt nghi ngờ.

## Đề bài

Bài toán: ngay khi đơn vừa giao xong, dự đoán khách có cho review 1–2 sao không. Notebook có sẵn
`load_olist_table` (một dòng mỗi đơn giao xong có review, 41 cột) và `time_split`. Trong
`starter/pipeline.ipynb`:

1. `LEAKY_COLUMNS`: mọi cột của bảng không được dùng làm feature vì là leakage, kể cả chính nhãn.
2. `NUMERIC`, `CATEGORICAL`, `HIGH_CARDINALITY`: chia các cột hợp lệ bạn chọn dùng vào ba nhóm.
3. `build_pipeline(numeric, categorical, high_card, C=1.0)`: `Pipeline` chưa fit gồm `ColumnTransformer`
   (số: impute median + `StandardScaler`; phân loại: impute hằng + `OneHotEncoder` chịu được category
   lạ; nhiều giá trị: `TargetEncoder`) và `LogisticRegression(C=C)`. Nhóm rỗng thì bỏ.
4. `fit_and_score(pipe, train, val, target="bad_review")`: fit trên train, trả ROC-AUC trên val.
5. Chạy các cell `explore`: điểm validation, điều gì xảy ra khi thêm `comment_len`, hệ số lớn nhất,
   và điểm test đo đúng một lần ở cuối.

## Tiêu chí đạt

- `LEAKY_COLUMNS` có đủ mọi cột sinh ra từ review và nhãn, không chứa cột hợp lệ như `delay_days`
  hay `order_estimated_delivery_date`.
- Danh sách feature không trùng nhau, không chứa cột leakage hay cột id thuần.
- Pipeline chịu được NaN, bang lạ, seller mới; không dùng cột nhãn làm feature; fit một lần trên
  train cho cùng kết quả như một pipeline mới fit trên train (validation không ảnh hưởng gì).
- `C` thật sự điều khiển regularization.
- Trên Olist thật: AUC validation từ 0.77 tới 0.86. Lời giải mẫu đạt 0.801; thêm `comment_len` nhảy
  lên 0.876, dấu hiệu leakage.

## Gợi ý

### Gợi ý 1

`ColumnTransformer([("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), numeric), ...])`.
Cột không được nêu tên bị bỏ (`remainder="drop"` mặc định), nên truyền cả DataFrame vào `fit` là an
toàn: cột nhãn không lọt vào feature.

### Gợi ý 2

`OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=20)` gộp category hiếm (dưới 20
dòng) thành một cột và đưa category lạ ở validation vào cột đó. `TargetEncoder(cv=KFold(5, shuffle=True, random_state=0))`
dùng cross fitting khi `fit_transform` trên train (xem bài Intermediate 01), và coi NaN là một
category.
