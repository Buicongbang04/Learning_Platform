# Lời giải: kế hoạch canary có guardrail

## Hướng làm

Mỗi con số trong kế hoạch phải đi cùng một lý do; chấm ở độ cụ thể và độ trung thực về điều canary không bắt được.

## Các bước gợi ý

| Bước | Canary | Dừng tối thiểu | Lý do |
| --- | --- | --- | --- |
| 0 | Shadow 100% | 1 giờ cao điểm | Không ảnh hưởng người dùng; kiểm lỗi, độ trễ, độ lệch dự đoán |
| 1 | 1% | 30 phút | Phát hiện lỗi nặng, p95 |
| 2 | 5% | 2 giờ cao điểm | Đủ mẫu cho tỉ lệ lỗi, phân phối dự đoán |
| 3 | 25% | 1 chu kỳ nhãn (30 phút) + 1 giờ | Nhãn về, so MAE |
| 4 | 100% | giữ bản cũ sẵn sàng 24 giờ | Rollback vẫn một lệnh |

## Cỡ mẫu

Giờ cao điểm 200 rps, bước 1%: 2 request/giây tới canary, 120 mỗi phút. Phát hiện lỗi tăng từ 0.4% lên 1.0%
với 95% tin cậy, 80% sức mạnh cần khoảng 1 000 request mỗi nhánh (công thức hai tỉ lệ cho ~1 100): ~9 phút cho canary 1%. Nhưng chỉ
có ý nghĩa nếu so với stable cùng cửa sổ. Về đêm 20 rps: bước 1% chỉ 12 request mỗi phút, ~90 phút cho 1 000; không đủ mẫu, nên các bước tỉ lệ thấp phải chạy ban ngày
hoặc dùng bước 5% về đêm và chấp nhận phát hiện chậm hơn. Không bao giờ promote dựa trên "không thấy lỗi" khi mẫu nhỏ.

## Guardrail

| Chỉ số | So với | Ngưỡng chặn |
| --- | --- | --- |
| Tỉ lệ lỗi 5xx | stable cùng cửa sổ | canary > stable + 0.5 điểm phần trăm, 2 cửa sổ 5 phút liên tiếp |
| p95 | stable cùng cửa sổ | canary > 1.2 x stable hoặc > 150 ms |
| Phân phối dự đoán (trung bình, p5, p95) | stable | lệch > 10% hoặc KS lớn bất thường |
| Tỉ lệ dự đoán ngoài miền hợp lý (ETA âm, > 4 giờ) | tuyệt đối | > 0.1% |
| MAE theo nhãn trễ (bước 3) | stable cùng slice | canary tệ hơn > 3% trên bất kỳ slice lớn |

## Rollback tự động

Điều kiện: bất kỳ guardrail vận hành vi phạm 2 cửa sổ liên tiếp. Hành động: một job đổi alias `champion` về version cũ rồi
gọi `/admin/reload`, ghi sự kiện (ai/cái gì, chỉ số vi phạm) và báo người trực. Nó **không** tự promote: đi tiếp một
bước luôn cần con người hoặc cổng (module 08), vì lỗi dương tính giả của rollback rẻ, của promote đắt.

## Rủi ro còn lại

Nhãn trễ nên MAE chỉ chặn ở bước cuối (bù bằng guardrail phân phối dự đoán và shadow trước); slice hiếm (sân bay, đêm) cần
mẫu riêng hoặc canary theo slice; mùa vụ (cuối tuần) cần dừng qua ít nhất một chu kỳ tuần trước khi đóng bản cũ.

## Rubric (tối đa 20 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Các bước có tỉ lệ, thời gian dừng và lý do | 4 |
| Ít nhất năm guardrail có ngưỡng, so cùng cửa sổ | 5 |
| Phép tính cỡ mẫu cụ thể, xử lý được ban đêm | 4 |
| Quy tắc rollback đo được, tự động, và nói rõ điều nó không làm | 4 |
| Rủi ro còn lại trung thực, có cách bù | 3 |

Từ 14 điểm trở lên là đạt. Lỗi hay gặp: so với số của hôm qua thay vì stable cùng cửa sổ; quên nhãn đến trễ; để rollback
tự động kiêm luôn promote.
