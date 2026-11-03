# Lời giải: tỉ lệ loại theo luật

Mẫu 200 000 chuyến của 2019-01 (đọc 5 cột, `sample(random_state=0)` trên 7 696 617 dòng):

| Luật | Dòng vi phạm | Tỉ lệ |
| --- | --- | --- |
| duration | 172 | 0,086% |
| distance | 1 416 | 0,708% |
| pickup_month | 13 | 0,007% |
| zone_range | 0 | 0% |
| zone_unknown | 4 826 | 2,413% |

Giữ lại 194 142 dòng (97,07%). Tổng các số đếm là 6 427 nhưng chỉ 5 858 dòng bị loại: 569 là lượt đếm trùng vì một dòng vi phạm nhiều luật
(vd. 160 dòng vừa thời lượng ≤ 0 vừa distance 0: chuyến huỷ). Vì vậy `rows_kept` dùng hợp (`any`), không cộng.

Điều rút ra:

- Luật **bắt được nhiều nhất không phải luật nghiêm trọng nhất**: `zone_unknown` là mã hợp lệ của TLC. Với model ETA có thể giữ để vẫn dự đoán các chuyến này;
  loại hay không là quyết định theo mục đích, không phải theo mức "bẩn".
- `zone_range` bằng 0 không có nghĩa là luật thừa: nó là **rào chắn** cho ngày nguồn đổi mã zone. Theo dõi số 0 này theo từng tháng.
- `pickup_month` chỉ 13 dòng nhưng mẫu có chuyến từ 2003 tới 7/2019: một dòng như vậy làm hỏng mọi phép chia theo ngày/tháng, và là kiểu lỗi
  hợp đồng nên chặn hoặc cách ly chứ không nên lặng lẽ lọc.
- Đo tỉ lệ theo thời gian: tỉ lệ `distance` tăng gấp ba ở tháng sau là tín hiệu nguồn lỗi, cảnh báo sớm hơn mọi dashboard model.
