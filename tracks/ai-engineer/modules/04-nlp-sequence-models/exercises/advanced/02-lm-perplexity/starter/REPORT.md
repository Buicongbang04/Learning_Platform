# Language model LSTM tiếng Việt: byte vs BPE

TODO: viết theo khung trong README của bài (ít nhất 500 từ).

## Tóm tắt

TODO: 3-4 câu. Model, dữ liệu, bpc tốt nhất và của tokenizer nào, thời gian, kết luận chính về so sánh perplexity.

## Thiết lập

TODO: dữ liệu (số bài, số ký tự train/val), các tokenizer (vocab, số ký tự mỗi token), kiến trúc, optimizer, số bước,
batch, BPTT, seed, phần cứng, thời gian.

## Kết quả

TODO: bảng: tokenizer, vocab, ký tự/token, perplexity theo token, bits per token, bpc, thời gian. Đường cong loss nếu có.

## Vì sao không so perplexity trực tiếp

TODO: giải thích bằng số của chính bạn.

## Văn bản sinh ra

TODO: vài mẫu từ cùng một câu mở đầu, với các temperature/top-k khác nhau; nhận xét.

## Giới hạn và bước tiếp theo

TODO: ngân sách bước so với ngân sách ký tự, model nhỏ, dữ liệu nhỏ; module 05 (GPT mini) sẽ so thế nào.
