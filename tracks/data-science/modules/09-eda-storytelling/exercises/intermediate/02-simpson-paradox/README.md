---
title: Simpson's paradox trong dữ liệu Olist thật
level: intermediate
services: []
files:
  - path: starter/simpson.ipynb
    note: 5 hàm TODO + kết luận
  - path: tests/test_simpson.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/09-eda-storytelling/exercises/intermediate/02-simpson-paradox/starter/simpson.ipynb
  - uv run pytest tracks/data-science/modules/09-eda-storytelling/exercises/intermediate/02-simpson-paradox -q
---

## Mục tiêu

Xây công cụ phát hiện Simpson's paradox (tỉ lệ theo tầng, chuẩn hoá trực tiếp, kiểm tra đảo chiều),
dùng nó trên Olist thật, và viết kết luận cho thấy bạn hiểu rằng **cơ chế**, không phải thống kê,
quyết định nên tin bảng gộp hay bảng phân tầng.

## Đề bài

Câu hỏi: khách ở bang SP có tỉ lệ review xấu thấp hơn khách các bang khác. Có phải khách SP dễ tính
hơn? Mở `starter/simpson.ipynb`:

1. `build_orders(orders, reviews, customers)`: một dòng mỗi đơn giao xong có review, cột `order_id`,
   `customer_state`, `late`, `bad`, `delivery_days`, theo định nghĩa dùng chung của track (xem
   docstring).
2. `delivery_bucket(days)`: nhóm số ngày giao vào `[0, 7)`, `[7, 14)`, `[14, 21)`, `[21, 30)`,
   `[30, ∞)` với nhãn `0-6`, `7-13`, `14-20`, `21-29`, `30+`, có thứ tự.
3. `stratified_rates(df, group, stratum, target)`: bảng dài cột `[stratum, group, n, rate]`.
4. `standardized_rates(df, group, stratum, target, weights=None)`: direct standardization

   $$
   \text{rate}^{\text{std}}_g = \sum_s w_s\,\text{rate}_{g,s}
   $$

   với trọng số mặc định là phân bố tầng của chính `df`; chỉ dùng tầng có mặt ở mọi nhóm và chuẩn
   hoá lại trọng số. Phải chạy đúng cả khi tầng là cột bool (`late`).
5. `simpson_check(df, group, stratum, target, a, b) -> dict`: `crude_diff`, `adjusted_diff`,
   `n_strata`, `strata_against_crude`, `reversal` (định nghĩa trong docstring). `reversal` là dạng "yếu"
   (crude và adjusted ngược dấu); dạng "mạnh" là mọi tầng đều ngược chiều crude. Chỉ giữ hai nhóm
   `a`, `b` trước khi tính.
6. Chạy các cell `explore` trên Olist thật: SP với ngoài SP, chia theo số ngày giao rồi theo trễ /
   đúng hẹn. Viết kết luận 5–8 câu ở cell cuối.

## Tiêu chí đạt

- `build_orders` lọc đúng đơn giao xong, lấy review mới nhất, tính trễ theo nguyên timestamp (giao
  15:00 đúng ngày hẹn là trễ), `delivery_days` là số thực.
- `delivery_bucket` đúng ranh giới trái đóng phải mở.
- Trên ví dụ sỏi thận kinh điển, `simpson_check` báo đảo chiều; trên dữ liệu không có mix shift thì
  không; trọng số tự chọn và tầng thiếu ở một nhóm được xử lý đúng; mô phỏng mix shift (5 seed)
  khôi phục chênh lệch thật 2 điểm.
- Trên Olist thật: 95 824 đơn, trễ 7.99%, review xấu 12.81%; SP so với ngoài SP chia theo số ngày
  giao: crude −3.66 điểm, adjusted +2.92 điểm, 4 tầng ngược chiều, `reversal = True`; chia theo trễ:
  adjusted −2.12 điểm, không đảo chiều.
- Kết luận nêu được vì sao hai cách chia cho hai câu chuyện và cách nào hợp với câu hỏi nào (chấm
  theo `SOLUTION.md`).

## Gợi ý

### Gợi ý 1

`df.groupby([stratum, group], observed=True)[target].mean().unstack(group)` cho bảng tầng × nhóm.
`observed=True` để cột categorical không sinh ra tổ hợp rỗng.

### Gợi ý 2

Khi tầng là bool, `table.loc[[False, True]]` bị pandas hiểu là **mask**, không phải nhãn: kết quả chỉ
còn một dòng và tỉ lệ chuẩn hoá sai lặng lẽ. Dùng `table.reindex(keep)` và `weights.reindex(keep)`.
