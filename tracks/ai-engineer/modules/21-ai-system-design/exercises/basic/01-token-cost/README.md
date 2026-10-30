---
title: Máy tính chi phí LLM API theo token
level: basic
services: []
files:
  - path: starter/cost.py
    note: 4 hàm TODO
  - path: tests/test_cost.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/21-ai-system-design/exercises/basic/01-token-cost -q
---

## Mục tiêu

Tự viết máy tính chi phí mà mọi câu hỏi system design đều cần trong năm phút đầu: một request tốn bao nhiêu, 1 000
request tốn bao nhiêu, một tháng tốn bao nhiêu, và vì sao một agent 10 bước đắt hơn 10 lần một câu hỏi đơn lẻ rất
nhiều. Làm xong bạn tính được ngay trên giấy và biết chỗ nào hay tính sai.

## Đề bài

**Phần cứng:** CPU · ~45 phút

`starter/cost.py` đã có hai dataclass: `Price` (giá USD cho **1 triệu token**: `input`, `output`, `cached_input`,
`cache_write`) và `Usage` (`input_tokens`, `output_tokens`, `cached_tokens`, `cache_write_tokens`). Quy ước của bài,
giống mục 3 lý thuyết: `input_tokens` là **tổng** token input, đã gồm phần đọc từ cache và phần ghi vào cache. Chỉ
dùng thư viện chuẩn. Viết bốn hàm:

1. `request_cost(usage, price) -> float`: chi phí USD của một request. Token input thường (không thuộc cache) tính giá
   `input`, token đọc từ cache tính giá `cached_input`, token ghi vào cache tính giá `cache_write` (nếu `None` thì như
   `input`), token output tính giá `output`. Ném `ValueError` khi: có số token âm; `cached_tokens + cache_write_tokens`
   vượt `input_tokens`; có `cached_tokens > 0` mà model không có giá cache (`cached_input` là `None`).
2. `cost_per_1k_requests(usage, price) -> float`: chi phí cho 1 000 request giống nhau.
3. `monthly_cost(usage, price, requests_per_day, days=30) -> float`. `ValueError` nếu `requests_per_day` hoặc `days` âm.
4. `agent_loop_usage(prefix_tokens, step_output_tokens, tool_result_tokens, steps, cache_prefix=False) -> Usage`:
   tổng token của một vòng agent `steps` bước. Mỗi bước là một lần gọi LLM gửi lại **toàn bộ** hội thoại: prompt bước
   $$i$$ (từ 1) dài $$P_i = \text{prefix} + (i - 1)(\text{output} + \text{tool\_result})$$ token, và bước nào cũng sinh
   `step_output_tokens` token. Với `cache_prefix=True` (prompt caching kiểu Anthropic, đánh dấu cache ở cuối prompt):
   bước 1 ghi cả $$P_1$$ vào cache; bước $$i \ge 2$$ đọc $$P_{i-1}$$ từ cache và ghi phần mới $$P_i - P_{i-1}$$.
   `ValueError` nếu `steps < 1` hoặc có số âm.

Sau khi test xanh, tự trả lời (không chấm): với giá Claude Sonnet 5.5 ở bảng mục 3 lý thuyết (đã kiểm 2026-10-30), một
agent 10 bước, prefix 4 000 token, mỗi bước 300 token output và 1 500 token kết quả tool tốn bao nhiêu khi có và không
có prompt caching? Bao nhiêu phần trăm chi phí nằm ở input?

## Tiêu chí đạt

- Chi phí một request khớp giá trị tính tay (sai số 1e-12), trả `float`; output và input tính đúng giá riêng.
- Token cache là **một phần** của `input_tokens`, không cộng thêm; giá ghi cache mặc định như input.
- Chi phí mỗi 1 000 request và mỗi tháng đúng; `days` thay đổi được.
- Vòng agent: tổng input tăng theo $$\frac{n(n-1)}{2}$$ chứ không tuyến tính; số token đọc/ghi cache đúng quy ước.
- Mọi đầu vào sai ở trên ném `ValueError`.

## Gợi ý

### Gợi ý 1

Đơn vị giá là USD cho 1 000 000 token, không phải 1 000 token (một số trang giá cũ dùng 1K token; luôn đọc tiêu đề
cột). Tính phần input "thường" trước: `input_tokens - cached_tokens - cache_write_tokens`; nếu âm thì đầu vào sai.

### Gợi ý 2

Với vòng agent, viết hẳn danh sách $$P_1, \dots, P_n$$ rồi cộng: tổng input là $$\sum_i P_i$$. Có cache thì token đọc
từ cache là $$P_1 + \dots + P_{n-1}$$, và token ghi là phần còn lại (bằng đúng $$P_n$$). Kiểm bằng ví dụ prefix 3 000,
mỗi bước thêm 1 000 token, 5 bước: 25 000 token input, 18 000 đọc cache, 7 000 ghi cache.
