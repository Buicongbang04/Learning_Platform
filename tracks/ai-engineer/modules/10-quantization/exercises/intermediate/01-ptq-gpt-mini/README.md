---
title: Post-training quantization cho GPT mini tiếng Việt
level: intermediate
services: []
files:
  - path: starter/ptq.ipynb
    note: 4 hàm TODO
  - path: tests/test_ptq.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py wikipedia-vi
  - uv run jupyter lab tracks/ai-engineer/modules/10-quantization/exercises/intermediate/01-ptq-gpt-mini/starter/ptq.ipynb
  - uv run pytest tracks/ai-engineer/modules/10-quantization/exercises/intermediate/01-ptq-gpt-mini -q
---

## Mục tiêu

Lượng tử hoá trọng số GPT mini tiếng Việt của module 05 sau khi train và đo bằng đúng thước đo của module 05 (bpc trên
validation, cửa sổ trượt). Làm xong bạn có bảng đánh đổi của chính model mình: mỗi bit và mỗi mức chia scale đổi bao nhiêu bpc
lấy bao nhiêu MB, và biết lớp nào cần giữ nhiều bit hơn.

## Đề bài

**Phần cứng:** CPU · ~90 phút

Thời gian trên là thời gian làm bài. Thời gian máy chạy hết notebook lời giải: khoảng 18 phút trên CPU (4 luồng, 20 bài
validation, checkpoint cấu hình PC 13.8 triệu tham số); khoảng 4 phút trên GPU dùng chung (kernel `ai-gpu`, đủ 100 bài).

Checkpoint: tệp `gpt-mini-v1` bạn lưu ở bài Advanced 01 module 05. Chép vào `data/raw/gpt-mini-vi/gpt_mini_vi.pt` (thư mục này
không vào git) hoặc đặt biến môi trường `GPT_MINI_CKPT=<đường dẫn>`. Chưa có thì notebook tự train một GPT nhỏ dự phòng (4
tầng, `n_embd` 128, khoảng 4 phút trên CPU) và lưu lại cho các bài sau. Bản này train quá ngắn nên lượng tử hoá gần như không
làm nó mất gì: so sánh điều đó với checkpoint thật là một bài học, nhưng trắc nghiệm của bài giả định checkpoint của module 05.

Trong `starter/ptq.ipynb`:

1. `fake_quantize_weight(w, bits, granularity, symmetric)`: per-tensor, per-channel hoặc theo nhóm; đối xứng hoặc zero-point.
2. `quantize_model(model, bits, granularity, symmetric, include_embedding)`: bản sao đã quantize mọi `nn.Linear`, xử lý đúng
   weight tying của `lm_head`/`tok_emb`.
3. `weight_storage_bytes(...)`: dung lượng thật của cấu hình đó, tính cả scale và zero-point.
4. `layer_sensitivity(model, names, quantize_fn, eval_fn)`: quantize từng lớp một, đo độ chênh.

Rồi chạy các cell `explore`: bảng bpc/MB cho 13 cấu hình từ int8 tới int2, ảnh hưởng của việc quantize embedding, phân phối
trọng số và tỉ lệ `max|w|/std` theo lớp, độ nhạy từng lớp và mixed precision. Cuối cùng làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `fake_quantize_weight` đúng trên ví dụ tính tay cho cả ba mức chia, cả hai chế độ (kể cả kẹp mã và số 0 chính xác), từ chối
  nhóm không chia hết; mức chia mịn hơn cho sai số nhỏ hơn.
- `quantize_model` không sửa model gốc, chỉ đổi trọng số `nn.Linear`, giữ bias/LayerNorm/`pos_emb`, giữ weight tying, và chỉ
  quantize embedding dùng chung khi được yêu cầu.
- `weight_storage_bytes` khớp công thức (scale fp16, zero 1 byte, tham số dùng chung đếm một lần).
- `layer_sensitivity` đo model gốc đúng một lần, mỗi lần chỉ thay một lớp, không sửa model gốc.

## Gợi ý

### Gợi ý 1

Ba mức chia scale đều quy về một shape `(hàng, số khối, cỡ khối)`: per-tensor là một hàng một khối, per-channel là mỗi hàng một
khối, theo nhóm là mỗi hàng `in // g` khối. Viết công thức lượng tử hoá một lần trên trục cuối của shape đó.

### Gợi ý 2

Để biết một `nn.Linear` có dùng chung trọng số với embedding không, so `id(linear.weight)` với `id` trọng số của các
`nn.Embedding` (hoặc dùng `is`). Sửa trọng số tại chỗ trong `torch.no_grad()` bằng `.copy_()` thì tensor dùng chung vẫn là một
tensor. `model.parameters()` không trả lại tham số dùng chung lần thứ hai.
