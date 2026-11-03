# API dự đoán giá cước (hợp đồng với app khách hàng)

`POST /predict` nhận JSON, trả về giá cước dự đoán bằng USD.

| Trường | Kiểu | Bắt buộc | Ý nghĩa |
| --- | --- | --- | --- |
| `pickup_ts` | chuỗi ISO 8601 | có | Thời điểm đón, giờ địa phương New York |
| `zone_id` | số nguyên | không | Mã zone đón (1..265); không gửi thì coi như chưa biết |
| `distance_km` | số thực | có | Quãng đường ước tính do app tính từ lộ trình, tính bằng kilomet |

Hợp đồng này đã phát hành cho app iOS và Android, không đổi.
