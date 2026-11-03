# Lời giải: River online learning so với batch

`online.py` cạnh tệp này là lời giải chạy được.

## Ý chính

- **Prequential = test-then-train.** Mỗi mẫu được đoán trước khi học. Đó là cách duy nhất đo công bằng một model học liên tục; học rồi
  mới đoán cho số đẹp giả.
- **Kết quả trên luồng sinh trong test** (seed 0–2, 4 000 mẫu, đánh giá trên 3 000 mẫu sau): có drift, online khoảng 0.90 còn batch
  khoảng 0.45 (ranh giới quyết định đảo hướng, model đóng băng gần như đoán ngược); ổn định, cả hai khoảng 0.93 (batch nhỉnh hơn
  hoặc bằng). `StandardScaler | LogisticRegression(SGD(0.05))` thích nghi trong vài trăm mẫu; learning rate mặc định chậm hơn (khoảng
  0.83 sau drift).
- **Ổn định thì giữ batch.** Model batch tái lập được (cùng dữ liệu, cùng code, cùng model), qua được cổng đánh giá, rollback bằng một
  dòng registry. Model online đổi mỗi mẫu: khó trả lời "model lúc 14:02 là gì", khó review.

## Khi nào không nên dùng online learning

- Nhãn về chậm (chargeback 60 ngày): "online" chỉ học từ quá khứ xa, mất lợi thế.
- Dữ liệu có thể bị đầu độc hay bẩn: mỗi mẫu xấu đi thẳng vào model đang phục vụ, không có cổng.
- Cần giải trình, kiểm toán (tín dụng, y tế): phải chỉ ra được model đã quyết định.
- Drift chậm theo mùa: huấn luyện lại theo lịch kèm cổng đánh giá rẻ và an toàn hơn.

Phương án thường gặp ở production: model batch làm chính, model online chạy shadow làm **chỉ báo drift** (khi online bắt đầu thắng rõ,
đó là tín hiệu huấn luyện lại batch).

## Lỗi hay gặp

- So online trên toàn luồng với batch trên đoạn sau: hai mẫu số khác nhau, so sánh vô nghĩa.
- Cho model online học trước khi đoán, độ chính xác "100%" trên luồng có nhãn ngay.
- Kết luận từ một seed.
