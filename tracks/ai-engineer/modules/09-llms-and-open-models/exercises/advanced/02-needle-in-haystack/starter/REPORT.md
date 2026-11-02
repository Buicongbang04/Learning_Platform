# Context length thật của qwen2.5:3b qua Ollama

TODO: viết theo khung trong README của bài (ít nhất 400 từ). Người đọc là đồng nghiệp sắp đưa tài liệu dài vào prompt:
họ cần biết dùng được tới đâu, cấu hình gì, và điều gì bài đo này không nói được.

## Tóm tắt

TODO: 3–4 câu có số. Ở cấu hình mặc định dùng được tới bao nhiêu token, vì sao; với cấu hình nào thì tới bao nhiêu; khuyến
nghị cụ thể.

## Thiết lập

TODO: model, phiên bản Ollama, `num_ctx`, filler, needle và câu hỏi (nguyên văn), cách đếm token, lưới thí nghiệm, phần
cứng, thời gian chạy.

## Kết quả

TODO: bảng đúng/sai theo (độ dài, vị trí) cho từng `num_ctx`; bảng số token đếm được so với `prompt_eval_count`.

## Giải thích từng ô sai

TODO: mỗi ô sai một dòng: cơ chế (prompt bị cắt phần nào, needle còn trong phần được đọc không), câu trả lời của model
(trả số khác, bịa, từ chối).

## Khuyến nghị và giới hạn

TODO: cấu hình khuyên dùng (num_ctx, kiểm prompt_eval_count, chunking/RAG), cái giá (bộ nhớ, thời gian), và vì sao bài
needle này dễ hơn việc thật (một needle, khớp chuỗi) nên không chứng minh model "hiểu" được cả tài liệu dài.
