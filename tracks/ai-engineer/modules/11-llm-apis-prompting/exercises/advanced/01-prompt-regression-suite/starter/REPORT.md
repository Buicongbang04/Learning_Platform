# Prompt regression suite: phân loại cảm xúc UIT-VSFC

TODO: viết theo khung trong README của bài (ít nhất 500 từ). Người đọc là trưởng nhóm phải quyết định thay đổi prompt
nào được đưa lên production: họ cần biết bạn đo gì, cổng chặn gì, tin được tới đâu.

## Quyết định

TODO: với từng ứng viên, merge hay chặn, lý do của cổng, và một câu có số.

## Thiết lập

TODO: tập ghim (bao nhiêu câu, lấy thế nào, vì sao cân bằng), các phiên bản prompt (tóm tắt), model và tham số sinh,
khoá cache, ngưỡng của cổng, bảng giá dùng để ước chi phí (ngày kiểm hoặc "giả định"), phần cứng, thời gian chạy.

## Kết quả

TODO: bảng sinh từ suite (mọi cột), và đọc bảng: chênh lệch nào lớn hơn nhiễu 150 câu, chênh lệch nào không; sàn
nhiễu đo được.

## Vì sao cổng thiết kế như vậy

TODO: từng điều kiện chặn, ngưỡng và lý do; một ca cổng ra quyết định mà bạn không đồng ý, và bạn sẽ sửa cổng thế nào.

## Phân tích lỗi

TODO: ít nhất 5 câu bị thay đổi bị chặn làm sai, đọc tận mắt, xếp loại (ví dụ: ví dụ few-shot lệch nhãn, nhãn
UIT-VSFC đáng ngờ, câu mơ hồ).

## Giới hạn và việc tiếp theo

TODO: những gì bảng này không nói được, và bạn sẽ thêm gì vào suite (câu khó, nhiều model, chạy trong CI).
