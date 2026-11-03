# Lời giải và rubric: ba tình huống quyết định

| Tình huống | Quyết định | Câu hỏi quyết định |
| --- | --- | --- |
| `holiday-week` | `keep` | Drift lớn (PSI 0.31, 0.27) nhưng nhãn đã về 94% cho thấy MAE 3.62 sang 3.66: tác động chất lượng không đáng kể |
| `bad-release` | `rollback` | Feature không đổi (PSI 0.04) nhưng dự đoán nhảy 38% ngay sau deploy; bản v6 chạy shadow có MAE 3.7 so với 6.9 của v7 trên cùng lưu lượng |
| `covid-lockdown` | `retrain` | MAE 3.10 sang 5.01 (+61.7%), thiên lệch +4.4 phút, không có bản trước nào tốt hơn, nguyên nhân là thay đổi bền vững của hành vi |

**`holiday-week` (keep).** Nếu chỉ nhìn dashboard drift, đây là ca "đỏ nhất". Nhưng drift mùa lễ là dự đoán được (cùng kỳ năm trước PSI tương đương) và đo tác động trực tiếp trên nhãn cho thấy model vẫn đúng.
Train lại ngay trên dữ liệu một tuần lễ còn có thể làm model tệ đi khi tuần sau quay về bình thường. Việc nên làm: giữ, ghi chú vào lịch, theo dõi tiếp, và đặt ngân sách cảnh báo theo mùa.

**`bad-release` (rollback).** Dấu hiệu quyết định là *thời điểm* và *so sánh trực tiếp*: dự đoán đổi ngay sau deploy trong khi đầu vào không đổi (PSI nhỏ) nên nguyên nhân là phiên bản mới, không phải thế giới.
Có bản trước tốt hơn rõ ràng trên cùng lưu lượng thì rollback nhanh và ít rủi ro nhất; train lại là chậm và không giải quyết lỗi của phiên bản mới. Sau rollback: postmortem về cách v7 qua được cổng kiểm.

**`covid-lockdown` (retrain).** Chất lượng giảm thật (có nhãn), model bias hệ thống, và không có bản trước tốt hơn để rollback. Retrain trên cửa sổ dữ liệu gần đây, so với model hiện tại trên holdout gần đây, rồi mới promote
(champion/challenger, shadow nếu có thể). Cẩn thận: dữ liệu quá ngắn của giai đoạn bất thường dễ làm model quá khớp với nó.

## Rubric cho `reasons` (mỗi tình huống tối đa 4 điểm, đạt ≥ 3)

| Tiêu chí | Điểm |
| --- | --- |
| Nêu số đo chất lượng (từ nhãn) và so với baseline, không chỉ nêu drift | 1 |
| Giải thích vì sao drift một mình chưa đủ (keep) hoặc đủ kết hợp với chất lượng (retrain, rollback) | 1 |
| Xét lựa chọn thay thế và nói vì sao không chọn (vd. vì sao không retrain ở `bad-release`, vì sao không rollback ở `covid-lockdown`) | 1 |
| Nêu bước tiếp theo hoặc điều kiện đổi ý (theo dõi gì, ngưỡng nào, kiểm gì sau khi hành động) | 1 |

Trừ điểm: "drift lớn nên retrain" mà không có bằng chứng chất lượng (-2); chọn `rollback` khi không có bản nào tốt hơn đã đo (-2).
