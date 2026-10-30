---
title: Mô phỏng LLM gateway - cache, cascade, fallback, circuit breaker
level: intermediate
services: []
files:
  - path: starter/gateway.py
    note: 2 hàm TODO; khối __main__ in bảng so sánh cấu hình
  - path: tests/test_gateway.py
    note: Không sửa
  - path: tests/fixtures/trace.csv
    note: 2 000 request GIẢ LẬP trong 1 giờ của chatbot CSKH (sinh bằng make_trace.py)
run:
  - uv run pytest tracks/ai-engineer/modules/21-ai-system-design/exercises/intermediate/02-gateway-simulator -q
  - uv run python tracks/ai-engineer/modules/21-ai-system-design/exercises/intermediate/02-gateway-simulator/starter/gateway.py
---

## Mục tiêu

Tự viết lõi của một LLM gateway (mục 5 lý thuyết) dưới dạng mô phỏng trên trace, để thấy bằng số mỗi thành phần
đổi chi phí, độ trễ, độ sẵn sàng ra sao, và một quyết định cache sai làm lộ dữ liệu khách hàng thế nào. Làm xong bạn
có công cụ trả lời "thêm cache/cascade/fallback thì được gì, mất gì" trước khi viết dòng code production nào.

## Đề bài

**Phần cứng:** CPU · ~90 phút

`tests/fixtures/trace.csv` là 2 000 request **giả lập** (không phải log thật; xem `make_trace.py`) trong một giờ của
chatbot CSKH: 53% là câu hỏi FAQ lặp theo phân phối Zipf, 47% là câu hỏi cá nhân có cùng văn bản giữa nhiều khách
("đơn của tôi đâu"), model chính sự cố 10 phút (t từ 1 500 tới 2 100 s) cộng 1.5% lỗi lẻ tẻ. Mỗi request là dict:
`id`, `t` (giây đến), `user`, `key` (câu hỏi đã chuẩn hoá), `personal` (bool), `in_tok`, `out_tok`, `small_conf` (độ
tự tin của model nhỏ, 0..1), `large_ok` (model lớn có trả lời thành công không), `lat_small`, `lat_large`,
`lat_fallback` (giây, độ trễ nếu gọi model đó).

`starter/gateway.py` có sẵn `ModelSpec(name, input_price, output_price)` (USD mỗi triệu token) và `GatewayConfig`. Viết:

1. `call_cost(model, in_tok, out_tok) -> float`: chi phí USD một lần gọi.
2. `simulate(trace, config, small, large, fallback) -> dict`: xử lý request theo thứ tự `t` tăng dần (trace có thể
   không sắp xếp). Với mỗi request:
   - **Cache** (khi `cache_ttl_s > 0`). Khoá là `(user, key)` nếu `cache_scope == "user"`, là `key` nếu `"global"` hoặc
     `"public"`. Với `"public"`, request `personal` không đọc và không ghi cache. Trúng khi khoá có trong cache và
     `t - t_lưu <= cache_ttl_s`: độ trễ `cache_latency_s`, chi phí 0. Trúng mà request là `personal` và câu trả lời
     trong cache do **user khác** tạo ra thì tính một lần **rò rỉ** (`leaks`). Request được phục vụ không qua cache thì
     ghi (hoặc ghi đè) cache với thời điểm `t` và user hiện tại. Lần trúng không làm mới thời điểm lưu.
   - **Cascade** (khi `cascade_threshold` không phải `None`): gọi small trước (trả tiền, cộng `lat_small`). Nếu
     `small_conf >= cascade_threshold` thì small trả lời, xong. Không thì gọi tiếp large.
   - **Large**: nếu `large_ok` thì trả tiền, cộng `lat_large`, xong. Nếu lỗi thì cộng `timeout_s` (chờ rồi bỏ), không
     mất tiền; khi `fallback` bật thì gọi fallback (trả tiền, cộng `lat_fallback`), không bật thì request **thất bại**.
   - **Circuit breaker** (khi `breaker_failures = k > 0`): đếm số lần large lỗi **liên tiếp** (một lần large thành công
     đặt lại về 0). Khi đếm đạt `k`, ngắt tới `t + breaker_cooldown_s`: trong thời gian đó không gọi large (không chờ
     timeout, không tính vào `calls["large"]`), đi thẳng fallback hoặc thất bại. Hết thời gian ngắt thì thử large lại;
     lỗi tiếp thì ngắt lại ngay.

   Trả dict: `requests`, `served`, `availability` (= served / requests), `cache_hits`, `cache_hit_rate`
   (= hits / requests), `leaks`, `cost_usd`, `cost_per_1k` (= cost / requests × 1 000), `p50_s`, `p95_s` (percentile
   tuyến tính của độ trễ các request **được phục vụ**, dùng `numpy.percentile`), `calls` (dict số lần gọi `small`,
   `large`, `fallback`, kể cả lần large lỗi). `ValueError` nếu trace rỗng hoặc `cache_scope` lạ.

Mô phỏng bỏ qua tranh chấp tài nguyên giữa các request (mỗi request độc lập, chỉ trạng thái cache và breaker đi theo
thời gian). Khi test xanh, chạy `starter/gateway.py` để in bảng so sánh các cấu hình, rồi làm trắc nghiệm của bài trong
app. Giá trong khối `__main__` là giả định.

## Tiêu chí đạt

- Mọi test trên trace nhỏ tự dựng qua: chi phí, độ trễ, số lần gọi đúng cho từng thành phần và tổ hợp của chúng.
- Cache theo user, TTL, rò rỉ của cache global, và cache public không đụng câu hỏi cá nhân đúng như định nghĩa.
- Circuit breaker ngắt sau `k` lỗi liên tiếp, không ngắt khi lỗi xen kẽ thành công.
- Trên trace đầy đủ: chỉ large có availability 0.837 và 5.156 USD/1 000 request; cache public trúng 47.8%, 0 rò rỉ,
  2.882 USD/1 000; cache global rò rỉ 925 lần.

## Gợi ý

### Gợi ý 1

Một vòng `for` duy nhất qua trace đã sắp xếp, trạng thái giữ ngoài vòng: `cache` (dict khoá → (t, user)),
`fails_in_row`, `open_until`, danh sách độ trễ, tổng chi phí, bộ đếm. Mỗi request đi lần lượt: cache → (small) →
(large nếu breaker cho phép) → (fallback). Dùng một biến `served` để biết request đã có câu trả lời chưa.

### Gợi ý 2

Hai lỗi hay gặp: (1) ghi cache cả khi request thất bại (lần sau "trúng" một câu trả lời không tồn tại); (2) với
`"public"`, chặn đọc cache của request cá nhân nhưng quên chặn ghi. Viết test nhỏ của riêng bạn cho từng nhánh trước
khi chạy trace 2 000 dòng: lỗi ở trace lớn rất khó lần.
