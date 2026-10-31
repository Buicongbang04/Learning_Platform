---
title: Scaling laws trên GPT mini và quy tắc Chinchilla
level: intermediate
services: []
files:
  - path: starter/scaling.ipynb
    note: 5 hàm TODO
  - path: tests/test_scaling.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py wikipedia-vi
  - uv run jupyter lab tracks/ai-engineer/modules/05-transformers-llm-architecture/exercises/intermediate/03-scaling-laws/starter/scaling.ipynb
  - uv run pytest tracks/ai-engineer/modules/05-transformers-llm-architecture/exercises/intermediate/03-scaling-laws -q
---

## Mục tiêu

Đếm tham số và FLOP của một Transformer bằng công thức, train một loạt GPT mini chỉ khác chiều rộng, khớp power law cho loss
theo số tham số, và dùng công thức của Chinchilla để chia một ngân sách compute giữa kích thước model và số token. Làm xong bạn
ước lượng được nhanh "model này train mất bao nhiêu GPU-giờ" và giải thích vì sao Llama 3 8B được train gấp gần 100 lần mức
Chinchilla khuyên.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Thời gian trên là thời gian làm bài. Notebook lời giải trên CPU 4 luồng: 5 model, 600 bước mỗi model, cả notebook 8 phút (PC, máy rảnh);
kernel `ai-gpu` dùng 5 model rộng hơn và 2 000 bước. Đọc mục 7 phần lý thuyết. Mở `starter/scaling.ipynb`:

1. `gpt_params(n_layer, n_embd, vocab_size, block_size)`: tổng tham số và tham số non-embedding của `GPT` bài Basic 01, bằng
   công thức (không khởi tạo model). `train_flops(n_params, n_tokens)`.
2. `fit_power_law(x, y)`: khớp $$y \approx c + a x^{-\alpha}$$.
3. `chinchilla_loss(n_params, n_tokens)` và `chinchilla_optimal(compute, tokens_per_param)`.

Rồi chạy các cell `explore`: train 5 model cùng số token, khớp $$L(N)$$, vẽ loss theo compute, tính ngân sách của Gopher theo
Chinchilla. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `gpt_params` đúng cho model của bài Basic 01 (27 584 tham số với 2 tầng, `n_embd` 32, vocab 50, block 16), cho GPT mini
  5 240 320 tham số của module, và xấp xỉ 124 triệu cho cấu hình GPT-2 small.
- `train_flops` theo $$6ND$$.
- `fit_power_law` lấy lại đúng tham số từ dữ liệu sinh theo công thức (sai số $$\alpha$$ dưới 5%), và khớp tốt dữ liệu có nhiễu nhỏ.
- `chinchilla_loss` đúng hằng số đã công bố; `chinchilla_optimal` trả cặp $$(N, D)$$ thoả $$6ND = C$$ và $$D = 20N$$.

## Gợi ý

### Gợi ý 1

Viết số tham số của một Block theo từng `nn.Linear` và `LayerNorm` của bài Basic 01 (mỗi Linear $$n_{in} n_{out} + n_{out}$$), rồi
cộng: kết quả là một đa thức bậc hai theo $$d$$. Phần embedding không nhân với số tầng; `lm_head` dùng chung trọng số nên không
cộng thêm.

### Gợi ý 2

Với $$c$$ cố định, $$\log(y - c) = \log a - \alpha \log x$$ là một đường thẳng, `np.polyfit(..., 1)` khớp được. Chỉ còn chọn $$c$$:
dò một lưới dày giữa 0 và $$\min y$$ (không được bằng $$\min y$$), chấm mỗi $$c$$ bằng sai số trên $$y$$ gốc. Với Chinchilla, thay
$$D = 20N$$ vào $$C = 6ND$$ rồi giải $$N$$.
