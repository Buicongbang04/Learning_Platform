---
title: "Olist: chọn thời điểm dự đoán và đổi metric ra tiền"
level: intermediate
services: []
files:
  - path: starter/decision.ipynb
    note: 6 hàm TODO + câu hỏi cuối notebook
  - path: tests/test_decision.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/15-ml-system-design/exercises/intermediate/01-olist-decision-time/starter/decision.ipynb
  - uv run pytest tracks/data-science/modules/15-ml-system-design/exercises/intermediate/01-olist-decision-time -q
---

## Mục tiêu

Làm bước 1–5 của khung system design trên dữ liệu thật: chọn thời điểm dự đoán theo hành động, dựng
feature đúng thời điểm, so hai thời điểm bằng metric offline, đổi sang tiền mỗi tuần, và đặt model cạnh
một luật không ML.

## Đề bài

Hệ thống cảnh báo đơn có nguy cơ giao trễ để CSKH nhắn tin **trước khi** đơn tới tay khách. Khác model
"review xấu lúc đơn vừa giao" ở module 10/11: ở đây ngày giao thực tế, trễ hay không và review đều là
leak. Mở `starter/decision.ipynb`:

1. `build_orders(orders, items, customers, sellers)`: một dòng mỗi đơn giao xong, đúng các cột trong
   docstring.
2. `time_split(df)`: chia theo định nghĩa chung của track.
3. `features_at(decision_time)`: cột feature hợp lệ lúc `"purchase"` và lúc `"carrier"`.
4. `offline_report(y, p, ks)`: prevalence, ROC-AUC, PR-AUC, precision@k.
5. `value_table(y, p, fractions, cost_action, loss_event, effect, n_weeks)`: giá trị tiền khi chọn top
   từng tỉ lệ.
6. `fit_predict(train, test, features)`: model nào cũng được, miễn xử lý được NaN và cột chữ.
7. Chạy các cell `explore`, so với luật "còn dưới 5 ngày", trả lời câu hỏi cuối notebook.

## Tiêu chí đạt

- `build_orders` đúng trên dữ liệu nhỏ: lọc đơn, gộp item nhiều seller, `same_state` chỉ bằng 1 khi mọi
  seller cùng bang với khách, khoảng thời gian là số ngày thực.
- Biên chia thời gian đúng; feature lúc `"purchase"` không chứa thông tin sau khi đặt hàng.
- `offline_report` khớp `sklearn`; `value_table` đúng trên ví dụ tính tay.
- `fit_predict` học được tín hiệu trên dữ liệu giả lập có NaN.
- Trên Olist thật: 96 470 đơn, 8.1% trễ; train / validation / test là 43 693 / 20 627 / 32 150; PR-AUC
  lúc giao vận chuyển cao hơn lúc đặt hàng ít nhất 0.15.

## Gợi ý

### Gợi ý 1

Gộp item: merge bang seller và bang khách vào bảng item, tạo cột `same = seller_state == customer_state`,
rồi `groupby("order_id").agg(..., same_state=("same", "all"))`. Khoảng ngày:
`(a - b) / pd.Timedelta(days=1)`.

### Gợi ý 2

LightGBM nhận NaN và cột `category`; ép `customer_state` sang `pd.CategoricalDtype` dựng từ **train**
để train và test có cùng mã. Với logistic regression thì cần `SimpleImputer` và `OneHotEncoder`
(`handle_unknown="ignore"`) trong một `Pipeline` (module 10).
