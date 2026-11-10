# Lời giải: đo độ trễ inference thật với Ollama

## Cách làm

- **`ollama_metrics`**: `resp.get(trường, 0)` cho mọi trường, chia `1e9` để ra giây, ép số token về `int`. Tốc độ là
  token chia thời gian, thời gian bằng 0 thì `0.0` (không chia cho số rất nhỏ: ra tốc độ vô lý hàng tỉ token/giây).
  `ttft_s = load_s + prefill_s`: trước khi có token đầu, server phải nạp model (nếu chưa nạp) và prefill cả prompt.
- **`summarize`**: `np.percentile` mặc định nội suy tuyến tính, cùng quy ước với pandas và phần lớn công cụ giám sát.
- **`fit_latency`**: ma trận thiết kế `[1, n_in, n_out]`, `np.linalg.lstsq`, rồi $$R^2$$ từ phần dư. Dưới 3 phép đo thì
  ba hệ số không xác định duy nhất, nên báo lỗi thay vì trả nghiệm tuỳ ý.
- **`stream_timing`**: TTFT là chunk đầu trừ `t_send`; TPOT là (chunk cuối − chunk đầu) / (số chunk − 1), khoảng cách
  trung bình giữa các token, không tính khoảng chờ trước token đầu.

## Số đo của lời giải mẫu

Cùng notebook, cùng máy (RTX 3050 Laptop 4GB, Ollama 0.13.5, `qwen2.5:3b` Q4_K_M), ba điều kiện khác nhau ngày
2026-10-30. Máy được dùng chung với các tiến trình khác, nên hai lần chạy notebook rơi vào lúc GPU bận 98–100% và Ollama
phải đẩy một phần model sang CPU (`ollama ps`: 1.39 trong 2.65 GB nằm trên GPU).

| Điều kiện | Prefill (token/giây) | Decode (token/giây) | Prefill / decode |
| --- | --- | --- | --- |
| GPU rảnh (hai response trong test, mục 4 lý thuyết) | khoảng 3 300 | 74 | khoảng 45 lần |
| Lần chạy 1, GPU bận | 346–498 (trung vị theo nhóm) | 14.4–16.7 | 31 lần |
| Lần chạy 2, GPU bận, model một phần trên CPU | 216–295 | 1.4–2.0 | 157 lần |

Quét độ dài output ở lần chạy 1 (prompt khoảng 320 token): decode 16 token mất 1.19 giây, 64 token 3.85 giây, 256 token
17.6 giây: **tuyến tính theo số token output**. Lần chạy 2 cùng quan hệ: 7.98, 46.3, 173.5 giây.

### Thời gian xếp hàng làm hỏng mô hình nếu không tách ra

`total_duration` của Ollama gồm cả thời gian request **chờ trong hàng đợi** khi model đang phục vụ request khác. Ở lần chạy
2, trung vị thời gian phục vụ (`load + prefill + decode`) của nhóm 16 token output là 9.65 giây nhưng `total_s` là 80.8 giây:
71 giây là xếp hàng. Lần gọi đầu có `total_s` 58.5 giây nhưng TTFT phía server chỉ 2.09 giây.

- Khớp trên `total_s`: $$R^2 = 0.58$$ (lần chạy 1 còn tệ hơn: $$R^2 = 0.12$$ và hệ số $$b$$ **âm**, vô nghĩa).
- Khớp trên `service_s`: $$R^2 = 0.84$$, $$b = 0.00348$$ giây/token input (khoảng 288 token/giây), $$c = 0.685$$ giây/token
  output (khoảng 1.5 token/giây), khớp tốc độ đo trực tiếp.

Bài học: độ trễ người dùng thấy = **xếp hàng** + phục vụ. Mô hình tuyến tính mô tả phần phục vụ; phần xếp hàng phụ thuộc
tải của cả hệ thống (module 20: batching, nhiều replica, giới hạn đồng thời). Trên máy riêng, `queue_s` gần 0 và hai cách
khớp gần như trùng nhau.

### Stream (lần chạy 2)

8 request, prompt 2 000 ký tự, 64 token output: TTFT client p50 3.07 giây, p95 3.62 giây; TTFT server p50 3.01 giây, nên
mạng localhost và phần còn lại chỉ thêm khoảng 60 ms. TPOT p50 0.51 giây (khoảng 2 token/giây), độ trễ toàn phần p50 35.8
giây, p95 40.5 giây. Ở lần chạy 1, TTFT client p50 33 giây trong khi TTFT server chỉ 2 giây: 31 giây xếp hàng mà server
không đếm vào `prompt_eval_duration`. Đo phía client là cách duy nhất thấy đúng thứ người dùng thấy.

## Trả lời câu hỏi cuối notebook

- **Prefill / decode**: 31 tới 157 lần khi GPU bận, khoảng 45 lần khi rảnh; luôn trên 10 lần. Prefill xử lý cả prompt
  song song (compute-bound); decode đọc toàn bộ trọng số cho mỗi token (memory-bound), và chịu thiệt nặng nhất khi trọng
  số phải đọc từ RAM qua CPU.
- **Đòn bẩy cho RAG 2 000 vào, 300 ra**: với hệ số GPU rảnh ($$b \approx 1/3300$$, $$c \approx 1/74$$), phần input là
  khoảng 0.6 giây, phần output khoảng 4.1 giây. Cắt nửa tài liệu tiết kiệm khoảng 0.3 giây; rút câu trả lời còn 150 token
  tiết kiệm khoảng 2 giây, **gấp khoảng 7 lần**. Với hệ số lần chạy 2, tỉ lệ còn lớn hơn (3.5 giây so với 103 giây).
- **Client và server**: lệch gồm mạng, serialize JSON, và **xếp hàng** (không nằm trong `prompt_eval_duration`).
- **GPU bận**: p50 và p95 đều tăng, nhưng p95 tăng nhiều hơn vì vài request rơi đúng lúc hàng đợi dài nhất.

## Bẫy thường gặp

- Quên chia `1e9`: tốc độ ra 0.00000007 token/giây.
- Khớp trên `total_duration` của máy dùng chung và tin hệ số âm.
- Gửi cùng một prompt nhiều lần để "đo cho chắc": Ollama giữ KV cache của prompt trước, prefill lần sau gần như bằng 0.
  Notebook dùng mỗi request một điều luật khác nhau vì lý do này.
- Báo một con số trung bình: trung bình che đuôi chậm. Báo p50 và p95 (hoặc p99), kèm số request đo.
- TPOT tính từ `t_send`: lẫn TTFT vào tốc độ decode.
