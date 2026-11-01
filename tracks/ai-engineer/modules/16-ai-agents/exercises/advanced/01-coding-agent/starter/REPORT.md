# Coding agent trên 12 task: pass@1 và phân tích lỗi

TODO: viết theo khung trong README của bài (ít nhất 500 từ). Người đọc là trưởng nhóm đang cân nhắc cho một model nhỏ
chạy local làm coding agent: họ cần biết nó làm được gì, hỏng ở đâu, và thiết kế nào giúp.

## Tóm tắt

TODO: 3–4 câu có số. pass@1 của model chính, khoảng dao động giữa các seed, thay đổi thiết kế có tác dụng lớn nhất và
nó đổi pass@1 bao nhiêu.

## Thiết lập

TODO: bộ task (bao nhiêu, loại gì, test thấy được và test ẩn), sandbox (thư mục tạm, timeout, mạng, môi trường), tool và
giao diện ghi tệp, prompt, ngân sách bước, model, `temperature`, seed, `num_ctx`, phần cứng, thời gian chạy.

## Kết quả

TODO: bảng pass@1 theo task và theo cấu hình (ít nhất hai cấu hình agent khác nhau), số bước, số lần chạy test, thời
gian. Câu đọc bảng tách chênh lệch thật khỏi nhiễu của 12 task.

## Phân tích lỗi

TODO: taxonomy lỗi có đếm, mỗi loại một ví dụ trace thật. Có lần nào agent sửa test thay vì sửa mã không? Có task nào
test thấy được pass mà test ẩn fail không, và vì sao?

## Khuyến nghị và giới hạn

TODO: thay đổi tiếp theo nên thử, model nào đáng thử (và chi phí), những gì bộ 12 task này không đo được.
