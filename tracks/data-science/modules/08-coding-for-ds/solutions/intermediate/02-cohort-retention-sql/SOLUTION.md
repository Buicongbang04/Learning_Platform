# Lời giải: cohort retention của Olist

## Query

Ba CTE theo đúng thứ tự tư duy: `delivered` (đơn hợp lệ + `customer_unique_id`), `active` (cặp khách,
tháng **không trùng**), `cohort` (`MIN(month)` mỗi khách). Join `active` với `cohort`, tính
`DATE_DIFF('month', cohort, month)` và `COUNT(*)` theo `(cohort, month_index)`. Vì `active` đã
`DISTINCT`, `COUNT(*)` là số khách khác nhau.

Hai lỗi phổ biến mà test bắt:

- Join theo `customer_id`: Olist có 99 441 `customer_id` nhưng 96 096 `customer_unique_id`; mỗi đơn
  một id mới, nên mọi "khách" chỉ mua một lần và retention bằng 0.
- Đếm đơn thay vì khách: khách mua hai lần trong tháng 2 bị đếm 2.

## Ma trận: 0 khác NaN

Số tháng đã quan sát được của cohort c là số tháng từ c tới `last_month`. Ô `(c, k)` với k lớn hơn số
đó là NaN (right-censoring); ô đã quan sát mà không có khách là 0. Cài đặt: `pivot` → `reindex` đủ cột
→ `fillna(0)` → chia cỡ cohort → `mask` theo điều kiện trên.

## Trung bình có trọng số

$$
\bar r_k = \frac{\sum_{c\,:\,c + k \le T} n_{c,k}}{\sum_{c\,:\,c + k \le T} n_{c,0}}
$$

Trên Olist: trung bình có trọng số tháng 1 là 0.483%; trung bình cộng thô của cột là 4.956%, vì cohort
2016-12 có đúng 1 khách và khách đó quay lại (ô 100%). Ở tháng 2 trở đi hai cách gần nhau hơn (0.336%
so với 0.289% ở tháng 2), nhưng không có lý do gì để dùng cách thô.

## Số liệu thật

| Chỉ số | Giá trị |
| --- | --- |
| Khách có đơn giao xong (mua trước 2018-09-01) | 93 350 |
| Tỉ lệ khách có từ 2 đơn giao xong | 3.00% |
| Cohort lớn nhất | 2017-11: 7 059 khách (Black Friday), 40 quay lại tháng 1 |
| Retention tháng 1 / 2 / 3 / 6 / 12 (có trọng số) | 0.483% / 0.336% / 0.255% / 0.232% / 0.166% |

## Kết luận mẫu

Xem cell cuối của notebook lời giải. Ý chính: Olist gần như là doanh nghiệp "mua một lần"; tăng trưởng
đến từ khách mới. Hạn chế phải nêu: khách có thể quay lại qua kênh khác mà dữ liệu không thấy, danh mục
chủ yếu là đồ bền nên tần suất mua tự nhiên thấp, bộ dữ liệu công khai chỉ là một mẫu.
