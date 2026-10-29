---
title: "Olist: phân tích nhân quả giao trễ → review xấu"
level: advanced
services: []
files:
  - path: starter/analysis.ipynb
    note: 3 hàm TODO + phân tích tự do
  - path: starter/REPORT.md
    note: Báo cáo cho Giám đốc Vận hành
  - path: tests/test_analysis.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/06-causal-inference/exercises/advanced/01-olist-late-delivery-review/starter/analysis.ipynb
  - uv run pytest tracks/data-science/modules/06-causal-inference/exercises/advanced/01-olist-late-delivery-review -q
---

## Mục tiêu

Làm trọn một phân tích nhân quả trên dữ liệu quan sát như ở công ty: từ DAG tới tập điều chỉnh,
nhiều ước lượng đối chiếu nhau, chẩn đoán overlap và balance, phân tích độ nhạy, rồi viết kết
luận đủ trung thực để đội vận hành dùng ra quyết định đầu tư.

## Đề bài

Giám đốc Vận hành của Olist hỏi: "Nếu giảm giao trễ thì review xấu giảm bao nhiêu? Đáng đầu tư bao
nhiêu vào logistics?" Trên dữ liệu thật, review xấu ở đơn trễ là 54%, đơn đúng hẹn 9%. Mở
`starter/analysis.ipynb`:

1. `build_orders(orders, reviews, items, customers, sellers)`: bảng một dòng mỗi đơn giao xong có
   review, đúng các cột mô tả trong notebook, theo định nghĩa dùng chung của Olist.
2. Vẽ DAG: confounder, mediator, selection. Chọn tập điều chỉnh và giải thích.
3. `effect_estimates(df, numeric, categorical, treatment="late", outcome="bad_review")`: dict
   `naive`, `regression` (linear probability model), `ipw_att` (logistic propensity, IPW chuẩn hoá).
   Chạy trên dữ liệu thật; kiểm tra overlap, balance, ESS.
4. Phân tích "liều": tỉ lệ review xấu theo số ngày trễ; có bước nhảy ở ngưỡng ngày hẹn không?
5. `e_value(rr)` và phân tích độ nhạy với confounder chưa đo.
6. Viết `REPORT.md` theo khung có sẵn (tối đa hai trang).

## Tiêu chí đạt

- `build_orders` đúng trên dữ liệu nhỏ trong test (lọc đơn, review mới nhất, item đầu tiên, giao
  trong ngày hẹn vẫn tính trễ).
- `effect_estimates` loại được confounding trên dữ liệu mô phỏng (tác động thật +0.30, sai số dưới
  0.03 qua 5 seed) và bằng `naive` khi không có covariate.
- `e_value` đúng công thức, cả khi RR < 1.
- Trên Olist thật: 95 824 đơn, 8.0% trễ, review xấu 54.1% / 9.2%; với covariate trong test, ước
  lượng hồi quy nằm giữa 0.40 và con số ngây thơ (≈ 0.448).
- `REPORT.md` không còn TODO, ít nhất 400 từ. Phần còn lại chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`(a - b) / pd.Timedelta(days=1)` cho số ngày dạng số thực. Seller của đơn là seller của dòng có
`order_item_id == 1`, không phải dòng xuất hiện đầu tiên. Đơn mua năm 2016 rất ít và có tháng toàn
đơn trễ: logistic với dummy tháng sẽ gặp separation (propensity bằng 0 hoặc 1). Cắt propensity về
`[1e-6, 1 − 1e-6]`, hoặc bỏ giai đoạn đó và nói rõ.

### Gợi ý 2

Đừng điều chỉnh cho thứ xảy ra **sau** khi đơn đã trễ: thời gian giao thực tế, việc khách liên hệ
CSKH, nội dung review. Đó là mediator hoặc chính outcome. Và hãy nghĩ về một vấn đề không biến
nào sửa được: bảng chỉ có đơn **có review**. Nếu giao trễ làm thay đổi việc khách có viết review hay
không, ước lượng của bạn đang điều kiện trên một collider.
