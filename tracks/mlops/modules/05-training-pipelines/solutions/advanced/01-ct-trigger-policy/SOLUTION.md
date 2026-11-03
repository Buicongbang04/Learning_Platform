# Lời giải: chính sách continuous training

Bài Advanced không có một đáp án duy nhất; `decisions.yaml` có đáp án quyết định (kiểm bằng máy), `POLICY.md` là một bản mẫu đã
chạy qua test. Rubric dưới đây chấm lập luận.

## Các ca trong `decisions.yaml`

| Ca | Quyết định | Vì sao |
| --- | --- | --- |
| C1 | skip | Lịch chạy nhưng dữ liệu mới 0.4% và MAE sát baseline. Lịch là lý do để **xem xét**, không phải để train. |
| C2 | skip | PSI 0.31 sau lễ là mùa vụ; MAE trên nhãn thật không đổi. Drift của đầu vào không đồng nghĩa dự đoán sai. |
| C3 | retrain | Ca "sách giáo khoa": MAE tệ hơn 14%, vượt SLO, đủ nhãn mới, dữ liệu sạch. |
| C4 | investigate | Null rate của `fare_amount` nhảy lên 31% cùng lúc MAE tăng. Train bây giờ là dạy model học dữ liệu hỏng. |
| C5 | retrain | Không có dấu hiệu xấu, nhưng model quá tuổi tối đa. Retrain định kỳ giữ pipeline "còn sống" và chặn tụt hậu âm thầm. |
| C6 | skip | Hash đổi nhưng nhãn về chậm: 35% có nhãn, dưới ngưỡng. Train trên dữ liệu thiếu nhãn là train trên phần thiên lệch. |
| C7 | investigate | Alert lặp lần ba, retrain 20 giờ trước không cải thiện. Lần retrain tiếp theo sau cooldown sẽ cho cùng kết quả; nguyên nhân nằm ngoài "model cũ". |

C2 và C5 là hai ca gây tranh cãi và là chủ ý: C2 chống phản xạ "drift thì retrain", C5 cho thấy có lý do hợp lệ để retrain dù mọi
chỉ số ổn. C7 là ca mà vòng "alert, retrain, alert" bị cắt bằng cooldown cộng với việc coi thất bại của lần retrain trước là
thông tin.

## Vì sao không retrain mù

- **Chi phí:** mỗi lần train tốn tính toán, thời gian người duyệt và rủi ro đưa model kém vào production.
- **Học dữ liệu hỏng:** retrain trên pipeline lỗi (C4) làm lỗi ăn vào model và khó gỡ hơn lỗi dữ liệu.
- **Vòng lặp:** nếu nguyên nhân không nằm ở model (nhãn, nghiệp vụ, đổi hành vi người dùng), retrain không sửa và cảnh báo vẫn bắn.
- **Mất tín hiệu:** model đổi liên tục thì không còn so sánh được trước/sau, không biết thay đổi nào tốt.

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Quyết định đúng, lý do đúng chỗ | 25 | 7 ca đúng; lý do nêu số (14%, 31%, 35%), không chỉ "chưa cần" |
| Cổng kiểm tra chất lượng dữ liệu trước trigger | 15 | Nêu ngưỡng đo được và hành động khi vượt (dừng, gọi người) |
| Dùng hiệu năng trên nhãn thật và xử lý nhãn về muộn | 20 | Phân biệt drift đầu vào với suy giảm hiệu năng; tính độ trễ nhãn vào cửa sổ đo |
| Guardrail chống vòng lặp và chi phí | 15 | Cooldown, trần số lần retrain, xử lý "retrain không cải thiện" |
| Điều kiện đổi quyết định | 15 | Mỗi skip/investigate có điều kiện cụ thể để thành retrain |
| Quan sát chính hệ CT | 10 | Ghi cả quyết định skip, alert khi pipeline CT không chạy |

Dưới 70: thường vì chính sách chỉ liệt kê loại trigger mà không nói trigger nào bị từ chối và vì sao, hoặc ngưỡng chung chung
("khi MAE tệ đi").
