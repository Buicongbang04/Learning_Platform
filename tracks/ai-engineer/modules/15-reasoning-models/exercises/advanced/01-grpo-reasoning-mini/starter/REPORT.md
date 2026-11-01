# Reasoning model mini: GRPO trên Qwen2.5-0.5B-Instruct với GSM8K

TODO: viết theo khung trong README của bài (ít nhất 600 từ). Người đọc là trưởng nhóm muốn biết: GRPO có làm model giỏi
hơn thật không, giỏi hơn bao nhiêu, tốn gì, và tin con số tới đâu.

## Tóm tắt

TODO: 3–4 câu có số: accuracy trước/sau (khoảng tin cậy, số seed), phần nào của mức tăng là định dạng, chi phí train.

## Thiết lập

TODO: model, LoRA, reward (công thức, trọng số), prompt, tập train (bao nhiêu câu đã dùng), tập đo ghim, cấu hình GRPO
(G, batch, lr, beta, loss_type, temperature, độ dài tối đa), phần cứng, thời gian, VRAM đỉnh.

## Kết quả

TODO: bảng trước/sau theo seed (accuracy, boxed_correct, format, độ dài, số câu bị cắt), hiệu kèm khoảng tin cậy theo
cặp, số câu đổi đúng/sai hai chiều. Đường cong reward, độ dài, tỉ lệ nhóm std = 0.

## Độ phủ: pass@1 so với pass@8

TODO: trước/sau trên 200 câu; RL dồn xác suất hay mở rộng khả năng?

## Phân tích lỗi và reward hacking

TODO: đọc ít nhất 20 câu trả lời; những kiểu lỗi nào giảm, kiểu nào còn; có dấu hiệu lách reward (định dạng, nhiều đáp
số, cắt ngắn bất thường) không; ví dụ thật.

## Giới hạn và việc tiếp theo

TODO: cỡ tập đo, số seed, một model, một prompt; nên thử gì tiếp (bước train, G, KL, model lớn hơn, distill trước).
