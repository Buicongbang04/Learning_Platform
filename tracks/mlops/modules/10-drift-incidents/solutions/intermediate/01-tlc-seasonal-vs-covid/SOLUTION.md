# Lời giải: drift mùa vụ và drift COVID

Mẫu 100 000 chuyến mỗi tháng (`seed=0`), sau `prepare` còn khoảng 98 400 dòng (2020-04: 96 700).

| Cặp tháng | PSI trip_distance | PSI fare_amount | PSI hour | passenger_count thiếu | MAE holdout | MAE tháng sau | Thay đổi |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2019-07 sang 2019-12 | 0.0015 | 0.0010 | 0.0016 | 0,6% sang 0,7% | 3.63 | 4.03 | +11% |
| 2020-02 sang 2020-04 | 0.023 | 0.050 | 0.152 | 0,8% sang 8,2% | 3.10 | 5.01 | +62% |

Điều rút ra:

- **Đổi mùa**: PSI gần 0 ở cả ba feature, MAE tăng 11%. Dự đoán trung bình thấp hơn thực tế khoảng 0.9 phút (tháng 12 chậm hơn tháng 7 một chút): một dịch chuyển nhẹ, đáng theo dõi, chưa phải sự cố.
- **COVID**: PSI chỉ ở mức "vừa" ở một feature (`hour` 0.152) và thấp ở hai feature còn lại, nhưng MAE tăng 62% và dự đoán cao hơn thực tế trung bình 4.4 phút. Hành vi thay đổi (chuyến vắng, đường thông, giờ cao điểm biến mất):
  quan hệ từ feature sang thời lượng đổi, tức **concept drift** đi kèm dịch chuyển phân phối nhỏ. Nhìn mỗi PSI bạn sẽ bỏ qua nó; nhìn MAE (khi nhãn về) bạn mới thấy.
- **Tín hiệu phụ có giá trị**: tỉ lệ `passenger_count` thiếu nhảy từ 0.8% lên 8.2% trong khi model không dùng cột này. Nó không giải thích MAE, nhưng báo rằng nguồn dữ liệu đã đổi: đáng mở ticket cho đội data.
- **Cách chia bin đổi con số.** Evidently (bin rộng bằng nhau) cho PSI `fare_amount` ≈ 0.005 và `hour` ≈ 0.17 trên cặp COVID, trong khi quantile cho 0.050 và 0.152. Quyết định "drift hay không" không nên chỉ dựa vào một con số PSI từ một công cụ.

Hệ quả cho khung quyết định: PSI/KS trả lời "đầu vào có khác không"; chỉ nhãn (hoặc proxy tốt) mới trả lời "model có còn đúng không". Hai cặp tháng này cho hai kết luận khác nhau
(đổi mùa: giữ và theo dõi; COVID: có bằng chứng chất lượng giảm, cần train lại) mà PSI một mình sẽ gần như không phân biệt được.
