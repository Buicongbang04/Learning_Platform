# Lời giải: flow train, evaluate, register với retry

Mã nằm trong `pipeline.py` cạnh tệp này.

## Retry đặt ở đâu và cho lỗi nào

Retry thuộc về **bước có lỗi tạm thời**: đọc dữ liệu qua mạng, gọi API. Không đặt retry cho `train_model`: huấn luyện lỗi do
dữ liệu hay mã sẽ lỗi lại y hệt, chỉ tốn thêm thời gian và tiền. Không đặt ở cấp flow: thử lại cả flow làm lặp việc đã xong
(và nếu bước register không idempotent, tạo trùng version).

`retry_condition_fn` tách lỗi tạm thời khỏi lỗi vĩnh viễn. `ValueError("schema sai")` thử lại 3 lần vẫn sai, và trong lúc đó
che mất lỗi thật khỏi người trực. Danh sách lỗi tạm thời là danh sách cho phép (`ConnectionError`, `TimeoutError`), không phải
danh sách cấm: lỗi lạ coi là vĩnh viễn cho tới khi có bằng chứng ngược lại.

## Các quyết định

- **`retries=2`, độ trễ cố định nhỏ.** Ở production dùng backoff tăng dần (`retry_delay_seconds=[5, 30, 120]`) và jitter để nhiều flow
  không dội lại cùng lúc; test dùng 0.2 giây.
- **Gate `min_r2` nằm trong flow, trước khi đăng ký.** Registry không nên chứa model chưa qua cổng tối thiểu; cổng đầy đủ
  (slice, latency, lineage) là chuyện của module 04.
- **Tham số `loader` là hàm.** Flow nhận "cách lấy dữ liệu" thay vì đường dẫn giúp test bơm lỗi tạm thời mà không cần mạng thật.
  Cái giá là `validate_parameters=False` và flow không còn tham số JSON thuần cho UI/deployment; ở bản thật loader được tạo từ
  tham số đơn giản bên trong flow.
- **Đăng ký "tạo nếu chưa có".** Hai flow chạy song song có thể cùng tạo registered model; bắt lỗi `already exists` và đi tiếp.
- **Cloudpickle cho model sklearn** vì `skops` từ chối `Tree` chưa tin cậy; đây là điểm bảo mật cần ghi lại trong model card.

## Lỗi hay gặp

- `retries=3` rồi đếm sai: `retries` là số lần **thử lại**, tổng số lần gọi là `retries + 1`.
- Dùng `except Exception: return None` trong loader để "cho flow khỏi chết": flow xanh mà không có dữ liệu.
- Quên rằng retry phát lại cả thân task: loader có tác dụng phụ (ghi tệp dở) phải idempotent.
