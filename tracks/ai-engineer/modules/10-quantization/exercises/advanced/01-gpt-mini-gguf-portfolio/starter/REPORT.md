# GPT mini tiếng Việt: quantize và chạy bằng llama.cpp

TODO: viết theo khung dưới đây (ít nhất 600 từ).

## Tóm tắt

TODO: 3-4 câu. Model gốc (tham số, bpc float32), cấu hình bạn khuyên dùng (định dạng, dung lượng, bpc, tốc độ), máy đo.

## Xuất GGUF

TODO: ánh xạ tên tensor, metadata, tokenizer; bằng chứng tệp đúng (tokenizer llama.cpp cho cùng token id, bpc bản f32 chạy bằng
llama.cpp so với PyTorch). Những gì llama.cpp làm khác PyTorch (ví dụ dạng GELU) và ảnh hưởng đo được.

## Bảng đánh đổi

TODO: một bảng: định dạng/phương pháp, bit thực mỗi trọng số hoặc dung lượng tệp, bpc và Δbpc, tốc độ sinh token (ghi CPU/GPU,
số luồng), thời gian quantize. Có cả dòng llama.cpp (`Q8_0`, `Q4_0`, `Q4_K_M`, `Q2_K`...) và dòng tự cài (RTN, GPTQ, AWQ, QAT).

## Phân tích

TODO: kiểu tensor thực tế trong từng tệp GGUF và vì sao; nhỏ hơn có nhanh hơn không và vì sao; phương pháp nào thắng ở mức bit
nào; độ lệch giữa các lần đo tốc độ.

## Giới hạn và bước tiếp theo

TODO: điều kiện đo (máy dùng chung?), những gì chưa đo, cách đưa tệp GGUF vào Ollama (Modelfile) và chia sẻ.
