# GPT mini tiếng Việt từ số 0

TODO: viết theo khung dưới đây (ít nhất 600 từ).

## Tóm tắt

TODO: 3-4 câu. Model (tham số, kiến trúc), dữ liệu (bài, token), bpc trên validation so với LSTM của module 04, phần cứng và
thời gian, một câu về chất lượng văn bản sinh.

## Dữ liệu và tokenizer

TODO: cách chọn bài, tách validation (và vì sao không rò rỉ), số ký tự, số token, ký tự mỗi token, số epoch đã đọc.

## Model và train

TODO: bảng cấu hình (n_layer, n_head, n_embd, block_size, vocab, tham số tổng và non-embedding), optimizer, learning rate,
warmup, batch (kể cả gradient accumulation), số bước, token đã thấy, dtype, VRAM đỉnh, thời gian, token/giây.

## Kết quả

TODO: bảng so sánh bpc (và perplexity theo token) với LSTM module 04 và GPT mini bài Intermediate 01; đường loss train và
validation; nói rõ ngân sách mỗi dòng.

## Văn bản sinh ra

TODO: vài mẫu từ cùng câu mở đầu với các temperature/top-k; distinct-n; nhận xét lỗi (lặp, bịa, sai sự thật).

## Giới hạn và bước tiếp theo

TODO: dữ liệu, kích thước, overfitting, đánh giá; checkpoint cho module 08 và 10 (đường dẫn, định dạng).
