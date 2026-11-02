# Trích xuất phản hồi sinh viên bằng LLM: kết quả và khuyến nghị

TODO: viết theo khung trong README của bài (ít nhất 500 từ). Người đọc là trưởng phòng đào tạo và trưởng nhóm kỹ
thuật: họ cần biết hệ thống trích được gì, đúng tới đâu, tốn bao nhiêu, và có nên dùng cho học kỳ tới không.

## Tóm tắt

TODO: 3–4 câu có số: độ đúng cảm xúc và chủ đề, tỉ lệ bản ghi hợp lệ, độ đồng ý của trường tự do với nhãn của bạn,
chi phí ước lượng mỗi học kỳ, khuyến nghị.

## Thiết kế

TODO: schema (vì sao từng trường), prompt (tóm tắt), quy tắc nghiệp vụ ngoài schema, vòng gọi lại, model và tham số,
phần cứng, thời gian chạy.

## Kết quả

TODO: bảng `score_batch` cho ít nhất hai cấu hình, F1 từng nhãn, số câu cần gọi lại, độ trễ, token; đọc bảng: chênh
lệch nào lớn hơn nhiễu 150 câu.

## Trường không có nhãn: tự chấm 30 câu

TODO: cách chấm `aspects`, `actionable`, `suggestion`, tỉ lệ đồng ý, model sai theo hướng nào (bịa việc cần làm, bỏ
sót, gợi ý chung chung).

## Phân tích lỗi

TODO: ít nhất 5 câu sai đọc tận mắt, xếp loại (nhãn UIT-VSFC đáng ngờ, câu mơ hồ, model nhầm chủ đề, vi phạm quy tắc).

## Chi phí và vận hành

TODO: token đo được, chi phí 10 000 phản hồi một học kỳ qua model API (bảng giá có ngày kiểm hoặc "giả định") so với
chạy local, Batch API, dữ liệu cá nhân trong phản hồi.

## Khuyến nghị và giới hạn

TODO: dùng hay không, cho trường nào, điều kiện, việc tiếp theo; những gì bảng này không nói được.
