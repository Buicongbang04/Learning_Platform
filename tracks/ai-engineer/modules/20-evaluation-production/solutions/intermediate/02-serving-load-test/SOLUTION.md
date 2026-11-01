# Lời giải: load test llama.cpp server và Ollama

## Cách làm

- `parse_sse_line`: chỉ dòng `data:` mang dữ liệu; `[DONE]` là tín hiệu kết thúc; dòng `:` (comment, keep-alive) và
  `event:` bỏ qua.
- `stream_chat`: ghi `clock()` **khi nhận** từng chunk có chữ (không phải khi xong), lưu `usage` khi chunk mang nó, bọc cả
  khối stream trong `try` để lỗi giữa chừng thành bản ghi. Chunk đầu chỉ có `role` và chunk rỗng không phải token.
- `run_open_loop`: thời điểm đến tuyệt đối `t0 + arrivals[i]`, ngủ tới đó rồi mới vào semaphore, nên thời gian chờ
  semaphore chính là hàng đợi phía client và `t_send - t_arrival` đo được nó.
- `run_closed_loop`: `concurrency` worker cùng lặp trên **một** iterator chỉ số: mỗi chỉ số được lấy đúng một lần mà không
  cần khoá (asyncio chạy một luồng).
- `summarize`: phân vị chỉ trên request thành công; inter-token gộp mọi khoảng của mọi request.

## Kết quả tham chiếu

PC của track: llama.cpp server (`llama-cpp-python` 0.3.36) chạy CPU 4 luồng dưới `nice`, Ollama 0.13.5 trên RTX 3060 **dùng
chung** với một job train khác, cùng model Qwen2.5-0.5B-Instruct Q4_K_M (tệp GGUF của Ollama), `max_tokens` 64. Notebook lời
giải chạy khoảng 8 phút.

**Cấu hình mặc định của `llama_cpp.server`**, closed loop:

| Đồng thời | Thành công | Lỗi | Request/giây |
| --- | --- | --- | --- |
| 1 | 16 | 0 | 0.96 |
| 2 | 1 | 15 | 0.21 |

Mặc định `--interrupt_requests` là `true`: request mới tới **ngắt** request đang stream. Client nhận chunk `role` rồi stream
kết thúc không có token nào, HTTP 200, không báo lỗi. Một load generator chỉ đếm HTTP status sẽ báo "16/16 thành công" với
độ trễ rất đẹp. Đây là lý do `stream_chat` coi "không có token" là lỗi, và lý do đầu tiên phải đọc ở mọi bảng load test là
cột thành công.

**Closed loop** (`--interrupt_requests false`) và Ollama:

| Server | Đồng thời | Request/giây | Token/giây | TTFT p50 (s) | TTFT p95 (s) | Inter-token p50 (s) |
| --- | --- | --- | --- | --- | --- | --- |
| llama.cpp, CPU | 1 | 0.97 | 42.2 | 0.19 | 0.30 | 0.019 |
| llama.cpp, CPU | 2 | 0.96 | 41.5 | 1.13 | 1.68 | 0.019 |
| llama.cpp, CPU | 4 | 0.82 | 35.6 | 3.70 | 5.07 | 0.020 |
| llama.cpp, CPU | 8 | 0.83 | 35.8 | 7.55 | 10.26 | 0.019 |
| Ollama, GPU dùng chung | 1 | 0.91 | 43.9 | 0.31 | 0.35 | 0.014 |
| Ollama, GPU dùng chung | 2 | 1.94 | 94.1 | 0.49 | 0.88 | 0.009 |
| Ollama, GPU dùng chung | 4 | 2.14 | 103.5 | 1.22 | 1.87 | 0.009 |
| Ollama, GPU dùng chung | 8 | 2.11 | 102.1 | 2.61 | 3.31 | 0.009 |

Một lần chạy thử trước đó của phần Ollama cho 1.21, 1.77, 1.61, 1.79 request/giây: GPU dùng chung làm số tuyệt đối dao động
nhiều, nhưng hình dạng giống nhau.

**Open loop** trên llama.cpp, 30 request mỗi mức, client giữ tối đa 1 request trong server:

| Tốc độ đến | Thời gian phục vụ p50 / p95 (s) | Hàng đợi p50 / p95 (s) | E2E p95 (s) |
| --- | --- | --- | --- |
| 0.3 | 1.35 / 1.55 | 0.03 / 1.95 | 3.12 |
| 0.6 | 1.38 / 1.91 | 1.31 / 4.66 | 6.26 |
| 0.8 | 1.27 / 1.55 | 1.88 / 4.40 | 5.64 |

**Prefix cache** (system prompt khoảng 1 740 token, `max_tokens` 1, giây mỗi lời gọi):

| Lời gọi | Không `--cache` | `--cache ram` |
| --- | --- | --- |
| A lần đầu | 12.87 | 13.53 |
| A, câu hỏi khác (2 lần) | 0.12, 0.12 | 0.37, 0.35 |
| B lần đầu | 12.46 | 12.54 |
| A, B, A xen kẽ | 12.40, 12.45, 12.68 | 0.77, 0.79, 0.79 |
| A có thêm dấu cách ở đầu | 13.19 | 13.00 |
| A sau đó | 12.81 | 1.11 |

## Đọc kết quả

- **llama.cpp server một context**: thông lượng phẳng (thậm chí giảm nhẹ) theo số request đồng thời, TTFT tăng gần tuyến tính
  vì request chờ **bên trong server**, inter-token đứng yên vì mỗi lúc chỉ một chuỗi được decode. Cột `queue_p95` bằng 0:
  load generator closed loop không nhìn thấy hàng đợi đó, chỉ thấy TTFT dài ra.
- **Ollama** (cấu hình `Parallel:1` theo log server) cũng chỉ chạy một request một lúc, nhưng thông lượng tăng từ 1 lên 2 request
  đồng thời rồi phẳng: ở mức 1, giữa hai request có khoảng trống (client nhận xong mới gửi tiếp, server chuẩn bị request mới) mà
  GPU ngồi không; từ mức 2 luôn có request chờ sẵn. Inter-token còn giảm khi tải liên tục, nhiều khả năng do GPU dùng chung giữ
  xung nhịp cao hơn khi bận (chưa kiểm). TTFT vẫn tăng nhiều lần từ 1 lên 8.
- **Open loop**: thời gian phục vụ đứng yên khoảng 1.3 giây ở mọi mức, còn hàng đợi p50 tăng từ gần 0 lên gần 2 giây. Công
  suất ước theo thời gian phục vụ là khoảng 0.75 request/giây, nên mức 0.8 đã vượt công suất: với nhiều request hơn hàng đợi sẽ
  tăng không giới hạn. Với 30 request, p95 của hàng đợi ở mức 0.6 và 0.8 đảo thứ tự (4.66 so với 4.40): phân vị 95 trên 30 mẫu
  là gần như mẫu lớn nhì, nhiễu hơn p50 nhiều. Bootstrap của bài Basic 01 trên một lượt 40 request ở mức 0.8 cho p95 E2E 9.44 s
  với khoảng [7.71, 9.97] (mục 6 lý thuyết).
- **Prefix cache**: cùng slot, cùng prefix, prompt 1 740 token chỉ mất 0.12 giây thay vì 12 tới 13 giây, khoảng 100 lần. Xen
  kẽ hai tài liệu thì không còn trúng (slot chỉ giữ request ngay trước). `--cache ram` lưu trạng thái theo prefix nên xen kẽ vẫn
  trúng (khoảng 0.8 giây: phải chép lại trạng thái vào context), đổi lại lần trúng cùng slot chậm hơn một chút (0.35 so với
  0.12). Một dấu cách ở đầu system prompt làm trượt cả hai kiểu cache.

## Lỗi hay gặp

- Đọc cả body rồi mới tách dòng: mọi token có cùng thời điểm, TTFT bằng E2E.
- Tin HTTP 200 là thành công.
- Ngủ theo khoảng cách giữa hai request: sai số cộng dồn làm tải thật thấp hơn tải định chạy.
- Đặt semaphore trước khi ngủ tới lịch: request chờ chỗ trước cả khi "đến", hàng đợi đo được sai.
- Không làm nóng server trước lượt đo đầu tiên: lần nạp model nằm trong p95 của mức tải thấp nhất.
- Bỏ quên server chạy nền sau khi đo, hoặc bind `0.0.0.0` trên máy dùng chung.
