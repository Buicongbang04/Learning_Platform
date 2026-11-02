---
title: Đọc GPT-2 small từ bên trong (head attention, logit lens, probe)
level: intermediate
services: []
files:
  - path: starter/inside_gpt2.ipynb
    note: 5 hàm TODO
  - path: tests/test_inside_gpt2.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py iwslt15-en-vi
  - uv run jupyter lab tracks/ai-engineer/modules/08-interpretability/exercises/intermediate/01-gpt2-heads-lens-probe/starter/inside_gpt2.ipynb
  - uv run pytest tracks/ai-engineer/modules/08-interpretability/exercises/intermediate/01-gpt2-heads-lens-probe -q
---

## Mục tiêu

Áp ba công cụ của các bài Basic lên một model thật mà cộng đồng interpretability đã mổ xẻ kỹ: GPT-2 small, nạp vào chính lớp
`GPT` bạn viết ở module 05. Bạn tự tìm ra bản đồ head (previous-token, duplicate-token, induction), kiểm bằng ablation xem
head induction có cần thật không, đọc dự đoán hình thành qua từng tầng bằng logit lens, và dò thông tin "token đã xuất hiện
chưa" bằng probe có đủ đối chứng. Mỗi kết quả đi kèm câu hỏi: nó cho phép kết luận gì, không cho phép kết luận gì.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Thời gian trên là thời gian làm bài. Cả notebook lời giải chạy khoảng 2 phút trên CPU 4 luồng (đo trên PC dùng chung, 128 giây), chưa kể
lần đầu tải GPT-2 (548 MB từ Hugging Face). GPU không cần. Đọc mục 1 tới 4 phần lý thuyết. Mở `starter/inside_gpt2.ipynb`:

1. `gpt2_into_gpt_mini(gpt_module, hf_model)`: dựng lớp `GPT` của module 05 mang trọng số GPT-2 (đặc tả trong docstring).
2. `ablate_heads(model, heads, means=None)`: context manager tắt một nhóm head (zero hoặc mean ablation).
3. `in_context_loss(model, seq, half)`: loss trên bản thứ nhất và bản thứ hai của dãy lặp lại.
4. `repeated_token_labels(idx)`: nhãn cho bài probe.
5. `lens_metrics(lens_logits, final_logits, targets)`: CE, trùng top-1, KL của logit lens so với model.

Rồi chạy các cell `explore` theo thứ tự: chúng dùng `hooks.py`, `lens.py`, `probe.py` của ba bài Basic (chưa xong thì tự dùng lời
giải), tải GPT-2 và chạy bốn thí nghiệm (bản đồ head, ablation, logit lens, probe). Cell cuối (tuỳ chọn) chạy lại các phép đo trên
GPT mini tiếng Việt của bạn nếu bạn đặt biến môi trường `GPT_MINI_CKPT` tới checkpoint `gpt-mini-v1` của module 05 (bài
Advanced 01). Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `gpt2_into_gpt_mini` cho logits khớp `GPT2LMHeadModel` (test dựng một GPT-2 tí hon ngẫu nhiên, không tải gì), giữ weight
  tying, trả model ở chế độ eval.
- `ablate_heads` thay đúng output của head được chọn trước `attn.proj` (zero: chỉ còn bias; mean: đúng vector cho trước), không
  đụng head khác, gỡ hook cả khi có exception.
- `in_context_loss` lấy đúng các vị trí của hai bản, có hoặc không có token đầu.
- `repeated_token_labels` và `lens_metrics` đúng định nghĩa (KL theo chiều $$\mathrm{KL}(p_{\text{model}} \Vert p_{\text{lens}})$$).
- Cell `explore` chạy hết; trên GPT-2, logits của bản bạn nạp lệch bản Hugging Face dưới $$10^{-3}$$.

## Gợi ý

### Gợi ý 1

In `hf_model.state_dict().keys()` và `model.state_dict().keys()` cạnh nhau: tên khác nhau nhưng thứ tự tầng giống nhau. Trong
`transformers`, `Conv1D.weight` có shape `(in, out)`; ma trận vuông như `c_proj` của attention sẽ không báo lỗi shape nếu bạn
quên chuyển vị, chỉ sai số.

### Gợi ý 2

`contextlib.contextmanager` biến một generator thành context manager: phần trước `yield` chạy khi vào `with`, phần trong
`finally` chạy khi ra. Pre-hook của `attn.proj` thấy output các head nối liền, shape `(B, T, C)`, giống `z.l` của bài Basic 01
trước khi tách head. Với `in_context_loss`, logits ở vị trí $$p$$ dự đoán token ở vị trí $$p + 1$$: viết ra các chỉ số cho
`half = 3` trước khi code.
