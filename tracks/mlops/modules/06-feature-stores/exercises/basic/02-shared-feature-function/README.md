---
title: Một hàm tính feature cho cả train và serve
level: basic
services: []
files:
  - path: starter/features.py
    note: compute_features, train_matrix, serve_one cần viết
  - path: tests/test_parity.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/06-feature-stores/exercises/basic/02-shared-feature-function -q
---

## Mục tiêu

Chặn training-serving skew ở nguồn: đúng **một** hàm tính feature, được cả đường train (cả bảng) và đường serve (một yêu cầu)
gọi. Bạn xử lý các ca biên (giờ 23 sang 0, zone thiếu) và chứng minh parity bằng test.

## Đề bài

Trong `starter/features.py`:

`compute_features(df)` nhận DataFrame có cột `pickup_ts` (thời điểm đón), `zone_id` (có thể thiếu hoặc `NaN`), `trip_distance`
(có thể thiếu), trả DataFrame **cùng chỉ số** với đúng các cột sau, theo thứ tự này, kiểu `float64`:

| Cột | Quy tắc |
| --- | --- |
| `hour_sin`, `hour_cos` | `sin` và `cos` của `2*pi*giờ/24`, `giờ` là giờ nguyên 0..23 của `pickup_ts`; nhờ đó 23 giờ và 0 giờ nằm sát nhau như 0 giờ và 1 giờ |
| `is_night` | 1 nếu giờ >= 22 hoặc giờ < 6, ngược lại 0 |
| `is_weekend` | 1 nếu thứ Bảy hoặc Chủ nhật, ngược lại 0 |
| `zone_id` | Giá trị gốc nếu nằm trong 1..265; thiếu, `NaN`, 0 hoặc ngoài khoảng đó thì **default 0** |
| `zone_known` | 1 nếu `zone_id` gốc hợp lệ (1..265), ngược lại 0 |
| `trip_distance` | Giá trị gốc; thiếu thì **default `DEFAULT_DISTANCE = 1.5`**; số âm thì cắt về 0 |

`FEATURE_COLUMNS` (đã có trong tệp) liệt kê đúng danh sách cột trên. DataFrame rỗng trả DataFrame rỗng có đủ cột.

- `train_matrix(df)`: ma trận feature cho huấn luyện; **phải gọi `compute_features`** (không tính lại).
- `serve_one(request)`: `request` là `dict` có `pickup_ts` (chuỗi ISO hoặc `Timestamp`, bắt buộc, thiếu thì `ValueError`),
  `zone_id` và `trip_distance` (tuỳ chọn, thiếu hoặc `None` thì dùng default như trên). Trả `dict` tên cột sang `float`;
  **cũng phải gọi `compute_features`**, đúng một lần mỗi yêu cầu. Test thay thế `compute_features` bằng bản đã biến đổi
  để kiểm cả hai đường đều đi qua nó.

Test còn so `serve_one` với `train_matrix` trên 400 chuyến thật của tháng 3/2019 (`mlopskit.real_month`), trong đó cố ý
xoá một phần `zone_id` và `trip_distance`.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/06-feature-stores/exercises/basic/02-shared-feature-function -q` pass.
- Giải thích được vì sao bảng ca biên trong test là thứ nên chạy trong CI của mọi feature pipeline.

## Gợi ý

### Gợi ý 1

`serve_one` chỉ cần biến yêu cầu thành DataFrame một dòng, gọi hàm chung, lấy dòng đó ra. Nếu bạn thấy mình viết lại
`np.sin` trong `serve_one`, bạn đang tạo ra nguồn skew.

### Gợi ý 2

`pd.to_numeric(..., errors="coerce")` biến `None` và chuỗi lạ thành `NaN` một cách thống nhất cho cả cột lẫn một dòng.
`Series.between(1, 265)` trả `False` với `NaN`.
