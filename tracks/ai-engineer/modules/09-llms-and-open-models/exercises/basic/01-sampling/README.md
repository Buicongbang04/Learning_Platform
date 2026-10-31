---
title: Tự cài sampling trên logits (greedy, temperature, top-k, top-p, penalty)
level: basic
services: []
files:
  - path: starter/sampling.py
    note: 7 hàm TODO
  - path: tests/test_sampling.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/09-llms-and-open-models/exercises/basic/01-sampling -q
---

## Mục tiêu

Hiểu chính xác các núm `temperature`, `top_k`, `top_p`, `repetition_penalty`, `presence_penalty`,
`frequency_penalty` mà mọi API LLM và Ollama đều có, bằng cách tự cài chúng trên một vector logits. Làm xong bạn
đọc được cấu hình sampling trong `generation_config.json` của một model và biết nó làm gì với phân phối token.

## Đề bài

**Phần cứng:** CPU · ~45 phút

Trong `starter/sampling.py`, chỉ dùng numpy, viết theo đúng docstring và công thức ở mục 5 phần lý thuyết:

1. `softmax(logits, temperature=1.0)`: ổn định số (logit 1 000 không làm `exp` tràn), logit `-inf` cho xác suất 0,
   `temperature <= 0` thì `ValueError`.
2. `greedy(logits)`: chỉ số logit lớn nhất, bằng nhau lấy chỉ số nhỏ.
3. `top_k_filter(logits, k)`: giữ các logit `>=` logit lớn thứ $$k$$ (bằng ở biên thì giữ hết), còn lại `-inf`.
4. `top_p_filter(logits, p)`: giữ **tập nhỏ nhất** các token xác suất cao nhất có tổng $$\ge p$$. Token làm tổng
   vượt $$p$$ được giữ; luôn còn ít nhất 1 token.
5. `apply_repetition_penalty(logits, generated, penalty)`: kiểu CTRL / Hugging Face, chia logit dương, nhân logit
   âm, mỗi token đã sinh phạt một lần.
6. `apply_presence_frequency(logits, generated, presence, frequency)`: kiểu OpenAI, trừ theo số lần xuất hiện.
7. `sample_next(logits, rng, *, temperature, top_k, top_p, repetition_penalty, generated)`: ghép các bước theo
   thứ tự penalty, temperature (0 là greedy), top-k, top-p, softmax, rút bằng `rng`.

Mọi hàm trả bản sao, không sửa mảng đầu vào.

## Tiêu chí đạt

- `softmax` khớp định nghĩa tới `1e-12`, ổn định với logit lớn, đúng với `temperature` 0.25 và 2.
- `top_k_filter`, `top_p_filter` giữ đúng tập token trên phân phối $$[0.5, 0.3, 0.15, 0.05]$$ ở mọi ngưỡng test,
  kể cả khi logits không sắp xếp và khi bằng xác suất.
- Repetition penalty phân biệt logit dương và âm; presence/frequency khớp giá trị tính tay.
- `sample_next`: temperature 0 không dùng `rng`; 20 000 lần rút có tần suất khớp xác suất lý thuyết sai số
  0.015 với từng cấu hình (top-k, top-p, temperature 2 + top-p, repetition penalty); cùng seed cho cùng chuỗi.

## Gợi ý

### Gợi ý 1

Trừ `max` trước khi `exp` không đổi kết quả softmax vì nhân tử $$e^{-m}$$ triệt tiêu ở tử và mẫu. Với top-p:
sắp xác suất giảm dần (`np.argsort(-probs, kind="stable")` để bằng nhau giữ chỉ số nhỏ trước), lấy tổng tích luỹ,
rồi tìm vị trí **đầu tiên** tổng chạm $$p$$: `np.searchsorted` làm đúng việc này.

### Gợi ý 2

Thứ tự trong `sample_next` quan trọng: top-p tính trên phân phối **sau** temperature, nên temperature cao làm tập
nucleus rộng ra. Với $$p = [0.5, 0.3, 0.15, 0.05]$$ và $$T = 2$$, xác suất thành khoảng $$[0.38, 0.29, 0.21, 0.12]$$
và top-p 0.75 giữ 3 token thay vì 2. Rút token: `rng.choice(len(probs), p=probs)`.
