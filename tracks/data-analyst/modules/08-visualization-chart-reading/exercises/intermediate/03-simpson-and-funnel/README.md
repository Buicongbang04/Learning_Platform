---
title: Simpson's paradox tuyển sinh Berkeley 1973 và funnel đơn hàng Olist
level: intermediate
services: []
files:
  - path: starter/simpson_funnel.ipynb
    note: 4 hàm TODO + đọc chart
  - path: tests/test_simpson_funnel.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-analyst/modules/08-visualization-chart-reading/exercises/intermediate/03-simpson-and-funnel/starter/simpson_funnel.ipynb
  - uv run pytest tracks/data-analyst/modules/08-visualization-chart-reading/exercises/intermediate/03-simpson-and-funnel -q
---

## Mục tiêu

Không tin một tỉ lệ gộp trước khi hỏi về cơ cấu: tính tỉ lệ theo nhóm và theo tầng, phát hiện đảo chiều
(Simpson's paradox) bằng chuẩn hoá trực tiếp, và trình bày một funnel có cả tỉ lệ so với bước đầu lẫn so
với bước trước, kèm giới hạn của dữ liệu.

## Đề bài

Phần A dùng bảng 6 khoa của tuyển sinh sau đại học UC Berkeley mùa thu 1973 (Bickel, Hammel & O'Connell,
*Science* 187: 398-404, 1975; cùng số liệu với `UCBAdmissions` của R), đã nhập sẵn thành hằng
`BERKELEY` (cột `dept`, `gender`, `applied`, `admitted`). Phần B dùng `olist_orders_dataset.csv` thật
trong `data/raw/` (tải bằng `data/download_olist.py`, cần Kaggle token). Mở
`starter/simpson_funnel.ipynb`, làm lần lượt:

1. `admit_rate(df, by) -> Series`: tổng `admitted` / tổng `applied` theo các cột `by`, tên `admit_rate`.
2. `simpson_flip(df) -> bool`: `True` khi hiệu tỉ lệ gộp giữa hai giới và hiệu tỉ lệ khử cơ cấu khoa khác
   dấu (cả hai khác 0). Tỉ lệ khử cơ cấu của một giới = trung bình tỉ lệ theo khoa của giới đó, trọng số là
   tổng hồ sơ của khoa (hai giới cộng lại). Không đúng hai giới thì `ValueError`.
3. `order_funnel(orders) -> Series`: số đơn có mốc không null ở `order_purchase_timestamp`,
   `order_approved_at`, `order_delivered_carrier_date`, `order_delivered_customer_date`; index
   `purchased, approved, carrier, delivered`; đếm từng cột độc lập; tên `orders`.
4. `step_conversion(funnel) -> Series`: tỉ lệ so với bước trước, bước đầu `1.0`.
5. Chạy các cell vẽ: tỉ lệ gộp và theo khoa, funnel có nhãn hai loại tỉ lệ, trạng thái đơn dừng giữa funnel,
   tỉ lệ đã giao theo tháng mua. Đọc theo quy trình 5 bước. Báo cáo bài học: làm phần trắc nghiệm trong app
   sau khi chạy notebook.

Các hàm không được sửa dữ liệu đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ sinh trong test pass: tỉ lệ cộng số đếm chứ không lấy trung bình tỉ lệ; phát hiện
  đảo chiều khi có và không báo khi cùng chiều; funnel đếm từng cột độc lập.
- Trên số liệu Berkeley: tỉ lệ gộp nam 44.5%, nữ 30.4%; `simpson_flip(BERKELEY)` là `True`.
- Trên Olist thật: bước `purchased` có 99 441 đơn (mọi đơn có mốc mua); funnel giảm dần qua 4 bước và khớp
  số tham chiếu trong test.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`df.groupby(by)[["applied", "admitted"]].sum()` rồi chia hai cột. Tỉ lệ theo khoa dạng bảng:
`admit_rate(df, ["dept", "gender"]).unstack("gender")`; trọng số `df.groupby("dept")["applied"].sum()`;
tỉ lệ khử cơ cấu `rates.mul(w, axis=0).sum() / w.sum()`. So dấu bằng `np.sign`.

### Gợi ý 2

`orders[cols].notna().sum()` đếm không null theo cột; đặt lại index bằng tên bước. `funnel / funnel.shift(1)`
cho bước đầu là `NaN`: `.fillna(1.0)`.
