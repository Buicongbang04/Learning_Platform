# Chọn model local cho phân loại chủ đề phản hồi sinh viên (UIT-VSFC)

TODO: viết theo khung trong README của bài (ít nhất 500 từ). Người đọc là trưởng nhóm phải chọn model đưa lên
production: họ cần biết bạn đo gì, tin được tới đâu, và bạn khuyên gì.

## Tóm tắt

TODO: 3–4 câu có số. Model và cấu hình bạn khuyên dùng, hơn các ứng viên khác bao nhiêu (kèm khoảng tin cậy), đổi lại
mất gì (độ trễ, bộ nhớ, giấy phép), và trên phần cứng nào.

## Thiết lập

TODO: mẫu (bao nhiêu câu, lấy thế nào, vì sao cân bằng), prompt (dán nguyên văn), các cấu hình (model, quantize, nơi
chạy GPU/CPU, tham số sinh), cách đọc nhãn, phần cứng và thời gian chạy.

## Kết quả

TODO: bảng mọi cấu hình (macro-F1, accuracy, không đọc được, p50/p95, token/s, bộ nhớ, VRAM), khoảng tin cậy bootstrap
cho các chênh lệch bạn dựa vào để quyết định.

## Phân tích lỗi

TODO: confusion matrix của cấu hình tốt nhất và tệ nhất; ít nhất 5 câu bị phân loại sai đọc tận mắt, xếp nguyên nhân
(nhãn mơ hồ, prompt định nghĩa thiếu, model không theo định dạng, nhãn của bộ dữ liệu đáng ngờ).

## Khuyến nghị và giới hạn

TODO: model khuyên dùng và điều kiện (phần cứng, lưu lượng, giấy phép), việc nên làm tiếp (prompt, few-shot, fine-tune,
model khác), và những gì 120 câu này không nói được, nhất là khi phân phối nhãn thật khác mẫu cân bằng.
