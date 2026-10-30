# Lời giải: máy tính chi phí LLM API

## Cách làm

- `request_cost`: kiểm số âm, tính phần input thường `input - cached - write` (âm là lỗi), kiểm model có giá cache
  khi có token cache, rồi cộng bốn phần và chia $$10^6$$. Giá ghi cache `None` thì lấy giá input.
- `cost_per_1k_requests` và `monthly_cost` chỉ là nhân: $$1000 \cdot c$$ và $$c \cdot \text{requests\_per\_day} \cdot \text{days}$$.
- `agent_loop_usage`: dựng danh sách $$P_i = \text{prefix} + (i-1)\Delta$$ với $$\Delta = \text{output} + \text{tool\_result}$$,
  tổng input là $$\sum P_i = n \cdot \text{prefix} + \Delta \frac{n(n-1)}{2}$$. Có cache: đọc $$\sum_{i<n} P_i$$, ghi
  $$P_n$$ (bước 1 ghi $$P_1$$, mỗi bước sau ghi thêm $$\Delta$$).

## Câu hỏi cuối đề

Agent 10 bước, prefix 4 000, mỗi bước 300 token output và 1 500 token kết quả tool, giá Claude Sonnet 5.5 (input 2,
output 10, đọc cache 0.10, ghi cache 5 phút 2.50 USD mỗi triệu token, kiểm 2026-10-30):

| | Input | Đọc cache | Ghi cache | Output | Chi phí |
| --- | --- | --- | --- | --- | --- |
| Không cache | 121 000 | 0 | 0 | 3 000 | 0.272 USD |
| Prompt caching | 121 000 | 100 800 | 20 200 | 3 000 | 0.0906 USD |

Không cache, **89%** chi phí là input: agent đắt vì đọc lại lịch sử, không phải vì viết. Prompt caching giảm 67%.
Cùng bài toán trên Haiku 5.5 là 0.0136 và 0.0050 USD. Số token input theo số bước: 4 000 (1 bước), 38 000 (5),
121 000 (10), 422 000 (20), 1 564 000 (40): gấp đôi số bước thì input gấp gần bốn. Đây là lý do agent cần giới hạn
số bước, tóm tắt hoặc cắt kết quả tool cũ (context engineering, module 16), và vì sao "agent cho mọi thứ" làm vỡ
ngân sách.

## Vì sao các lựa chọn này

- **Token cache là một phần của input** vì đó là cách người thiết kế nghĩ ("prompt 3 000 token, 2 000 trúng cache").
  Usage của provider thì khác nhau (docs prompt caching, kiểm 2026-10-30): OpenAI Responses API báo `input_tokens`
  **đã gồm** `input_tokens_details.cached_tokens` và `cache_write_tokens`, đúng quy ước của bài; Anthropic báo
  `input_tokens` **chỉ là phần sau breakpoint cuối**, tổng input là `cache_read_input_tokens +
  cache_creation_input_tokens + input_tokens`. Đọc nhầm quy ước là đếm cache hai lần hoặc trừ hai lần. Khi nối với API thật, viết một hàm chuyển usage của từng provider về `Usage` của bạn và test nó.
- **Ném lỗi khi model không có giá cache** thay vì coi là 0: im lặng tính 0 làm chi phí thấp giả.
- **Ghi cache có giá riêng**: Anthropic tính ghi cache 1.25 lần giá input (5 phút) hoặc 2 lần (1 giờ). Nếu tỉ lệ trúng
  thấp, prompt caching có thể **đắt hơn** không cache. Trong ví dụ ở test, ghi 1 500 token mà không ai đọc lại làm
  request đắt hơn 11% so với không dùng cache.

## Bẫy thường gặp

- Chia $$10^3$$ thay vì $$10^6$$: lệch 1 000 lần.
- Cộng token cache vào input thay vì tách ra: chi phí cao hơn thật (0.00715 thay vì 0.00415 trong test).
- Vòng agent tính $$n \cdot P_1$$ (bỏ qua lịch sử tăng dần) hoặc $$n \cdot P_n$$.
- Quên reasoning token: model reasoning tính chúng là output (trang giá Gemini ghi rõ "output price including
  thinking tokens"), có thể gấp nhiều lần phần trả lời nhìn thấy.
