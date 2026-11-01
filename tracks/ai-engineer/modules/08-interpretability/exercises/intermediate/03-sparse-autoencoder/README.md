---
title: Sparse autoencoder trên residual stream của GPT-2 small
level: intermediate
services: []
files:
  - path: starter/sae.ipynb
    note: 1 lớp (5 phương thức) và 6 hàm TODO
  - path: tests/test_sae.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py iwslt15-en-vi
  - uv run jupyter lab tracks/ai-engineer/modules/08-interpretability/exercises/intermediate/03-sparse-autoencoder/starter/sae.ipynb
  - uv run pytest tracks/ai-engineer/modules/08-interpretability/exercises/intermediate/03-sparse-autoencoder -q
---

## Mục tiêu

Tự viết sparse autoencoder (ReLU + L1 và TopK), kiểm nó trên dữ liệu đồ chơi có đáp án (đặc trưng chồng chất trong ít chiều hơn),
rồi train trên residual stream tầng giữa của GPT-2 small và đánh giá như một nhóm nghiên cứu: tái dựng (FVU), độ thưa (L0, latent
chết), độ trung thành (cross-entropy khi ghép SAE vào model) và đọc latent bằng ví dụ. Làm xong bạn đọc được một bảng kết quả SAE
của người khác và biết hỏi lại câu nào.

## Đề bài

**Phần cứng:** GPU 4GB · ~150 phút

Thời gian trên là thời gian làm bài. Thời gian máy của notebook lời giải: với kernel `ai-gpu` (1 triệu token, 6 144 latent, 3 SAE)
chạy 4 tới 7 phút (247 và 395 giây ở hai lần chạy, GPU dùng chung với tiến trình khác); không có GPU notebook tự giảm còn 200 nghìn token và 3 072 latent, chạy khoảng 19 phút (1 121 giây) trên CPU 4 luồng (cả hai đo trên PC dùng
chung). VRAM dưới 2 GB. Cần bài Intermediate 01 (`gpt2_into_gpt_mini`, chưa xong thì tự dùng lời giải). Đọc mục 6 phần lý thuyết.
Mở `starter/sae.ipynb`:

1. Lớp `SparseAutoencoder`: khởi tạo, `encode` (ReLU hoặc TopK), `decode`, `forward`, `loss`, `normalize_decoder_`.
2. `activation_scale`, `train_sae`, `sae_metrics` (FVU, L0, tỉ lệ latent chết).
3. `collect_resid_pre` (thu residual stream vào một tầng, bỏ vị trí 0), `sae_splice` (ghép SAE vào model), `ce_loss_recovered`.

Đặc tả chính xác (thứ tự rút số ngẫu nhiên, lịch learning rate) ở docstring. Rồi chạy các cell `explore`: dữ liệu đồ chơi, thu
activation tầng 6 trên văn bản TED, train một SAE TopK và hai SAE L1, cross-entropy khi ghép SAE, đọc latent. Sau đó làm phần trắc
nghiệm của bài trong app.

## Tiêu chí đạt

- Khởi tạo đúng (decoder chuẩn hoá, encoder là bản sao chuyển vị, bias 0); `encode` trừ `b_dec`, TopK giữ đúng k giá trị lớn nhất
  qua ReLU; `loss` đúng công thức (MSE tổng theo chiều, L1 nhân norm hàng decoder).
- `train_sae` tái lập theo seed, dùng `scale`, chuẩn hoá decoder mỗi bước, đúng lịch learning rate; trên dữ liệu đồ chơi SAE TopK
  tìm lại các hướng thật (cosine trung bình trên 0.9).
- `sae_metrics`: FVU so với phương sai quanh trung bình, latent chỉ bật một lần vẫn là sống.
- `collect_resid_pre` lấy stream trước `ln1`, bỏ vị trí 0, đúng thứ tự, float16; `sae_splice` giữ vị trí 0, nhân rồi chia `scale`,
  gỡ hook; `ce_loss_recovered` đúng.
- Cell `explore` chạy hết.

## Gợi ý

### Gợi ý 1

`tensor.topk(k, dim=-1)` trả cả giá trị lẫn chỉ số; `torch.zeros_like(pre).scatter(-1, chỉ_số, giá_trị)` dựng lại tensor thưa.
Với FVU trên dữ liệu lớn, cộng dồn theo batch cả $$\sum \lVert x - \hat x\rVert^2$$ lẫn $$\sum x$$ và $$\sum \lVert x\rVert^2$$: phương sai quanh
trung bình bằng $$\sum\lVert x\rVert^2 - \lVert\sum x\rVert^2 / N$$, không cần giữ cả tập trong bộ nhớ.

### Gợi ý 2

Model đầy đủ tính logits cho mọi vị trí (50 257 cột) kể cả khi bạn chỉ cần một activation giữa chừng: batch 16 ngữ cảnh × 128 token
đã tốn khoảng 400 MB cho logits. Nếu train SAE mà loss không giảm, kiểm `scale` trước (norm trung bình của `x * scale` phải cỡ
$$\sqrt{768}$$), rồi tới learning rate.
