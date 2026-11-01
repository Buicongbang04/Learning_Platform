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
chung** với job của module khác (mức bận khác nhau giữa các lần chạy), cùng model Qwen2.5-0.5B-Instruct Q4_K_M (tệp GGUF của Ollama), `max_tokens` 64. Notebook lời
giải chạy khoảng 8 phút.

**Cấu hình mặc định của `llama_cpp.server`**, closed loop (hai lần chạy notebook, 2026-11-02 lúc 00:25 và 05:17):

| Đồng thời | Thành công | Lỗi | Request/giây |
| --- | --- | --- | --- |
| 1 | 16, 16 | 0, 0 | 0.96, 0.92 |
| 2 | 1, 1 | 15, 15 | 0.21, 0.19 |

Mặc định `--interrupt_requests` là `true`: request mới tới **ngắt** request đang stream. Client nhận chunk `role` rồi stream
kết thúc không có token nào, HTTP 200, không báo lỗi. Một load generator chỉ đếm HTTP status sẽ báo "16/16 thành công" với
độ trễ rất đẹp. Đây là lý do `stream_chat` coi "không có token" là lỗi, và lý do đầu tiên phải đọc ở mọi bảng load test là
cột thành công.

**Closed loop** (`--interrupt_requests false`) và Ollama, lần chạy thứ hai (05:17):

| Server | Đồng thời | Request/giây | Token/giây | TTFT p50 (s) | TTFT p95 (s) | Inter-token p50 (s) |
| --- | --- | --- | --- | --- | --- | --- |
| llama.cpp, CPU | 1 | 0.95 | 41.1 | 0.20 | 0.31 | 0.019 |
| llama.cpp, CPU | 2 | 0.91 | 39.5 | 1.17 | 1.78 | 0.020 |
| llama.cpp, CPU | 4 | 0.80 | 34.8 | 3.79 | 5.01 | 0.021 |
| llama.cpp, CPU | 8 | 0.75 | 32.6 | 8.48 | 10.78 | 0.022 |
| Ollama, GPU dùng chung | 1 | 1.56 | 75.7 | 0.27 | 0.33 | 0.007 |
| Ollama, GPU dùng chung | 2 | 2.35 | 113.8 | 0.46 | 0.62 | 0.008 |
| Ollama, GPU dùng chung | 4 | 2.75 | 133.0 | 0.91 | 1.47 | 0.006 |
| Ollama, GPU dùng chung | 8 | 2.83 | 137.2 | 1.88 | 2.80 | 0.006 |

Phần Ollama đo trên GPU. Ba lần chạy (một lần thử và hai lần notebook) cho request/giây ở mức 1, 2, 4, 8 lần lượt là 1.21,
1.77, 1.61, 1.79; 0.91, 1.94, 2.14, 2.11; 1.56, 2.35, 2.75, 2.83: GPU dùng chung làm số tuyệt đối dao động gần gấp đôi, nhưng
hình dạng giống nhau. Lần chạy thứ nhất của llama.cpp cho 0.97, 0.96, 0.82, 0.83 request/giây và TTFT p50 0.19, 1.13, 3.70,
7.55 s.

**Open loop** trên llama.cpp, 30 request mỗi mức, client giữ tối đa 1 request trong server. Notebook đặt mức tải bằng 0.4,
0.75 và 1.0 lần công suất ước từ thời gian phục vụ p50 của closed loop ở mức 1 (1.0 s, tức 0.40, 0.75, 1.00 request/giây):

| Tốc độ đến | Thời gian phục vụ p50 / p95 (s) | Hàng đợi p50 / p95 (s) | E2E p95 (s) |
| --- | --- | --- | --- |
| 0.40 | 1.47 / 1.79 | 0.04 / 2.71 | 4.02 |
| 0.75 | 1.38 / 1.77 | 2.06 / 4.59 | 5.87 |
| 1.00 | 1.38 / 1.72 | 2.63 / 7.87 | 8.97 |

Lần chạy đầu (mức cố định 0.3, 0.6, 0.8 request/giây) cho hàng đợi p50 0.03, 1.31, 1.88 s với thời gian phục vụ 1.27 tới
1.38 s.

**Prefix cache** (system prompt khoảng 1 740 token, `max_tokens` 1, giây mỗi lời gọi, lần chạy thứ hai; lần đầu cho cùng
hình dạng):

| Lời gọi | Không `--cache` | `--cache ram` |
| --- | --- | --- |
| A lần đầu | 14.44 | 14.85 |
| A, câu hỏi khác (2 lần) | 0.12, 0.13 | 0.37, 0.39 |
| B lần đầu | 16.09 | 14.25 |
| A, B, A xen kẽ | 16.19, 16.35, 15.57 | 0.77, 0.80, 0.81 |
| A có thêm dấu cách ở đầu | 13.88 | 17.81 |
| A sau đó | 13.55 | 1.42 |

## Đọc kết quả

- **llama.cpp server một context**: thông lượng phẳng (thậm chí giảm nhẹ) theo số request đồng thời, TTFT tăng gần tuyến tính
  vì request chờ **bên trong server**, inter-token đứng yên vì mỗi lúc chỉ một chuỗi được decode. Cột `queue_p95` bằng 0:
  load generator closed loop không nhìn thấy hàng đợi đó, chỉ thấy TTFT dài ra.
- **Ollama** (cấu hình `Parallel:1` theo log server) chỉ decode một request một lúc, nhưng thông lượng tăng từ 1 lên 2 request
  đồng thời (ba lần chạy: 1.21 lên 1.77, 0.91 lên 1.94, 1.56 lên 2.35 request/giây) rồi tăng chậm dần. Nguyên nhân **chưa được đo trực tiếp**; số liệu gợi ý một cách giải thích
  khả dĩ: ở mức 1, mỗi request có khoảng 0.3 giây không phải decode (TTFT p50 0.27 tới 0.31 s, gồm nhận request, dựng prompt, prefill)
  trong tổng khoảng 0.6 tới 1.1 giây, và khi chỉ có một request thì phần đó nối tiếp phần decode. Từ mức 2 luôn có request chờ sẵn, nên
  nhiều khả năng phần không-decode của request này chồng lên phần decode của request kia. Inter-token ở lần chạy thứ nhất cũng giảm (0.014 xuống
  0.009 s) khi tải liên tục, có thể do GPU dùng chung giữ xung nhịp cao hơn khi bận (chưa kiểm). TTFT vẫn tăng nhiều lần từ 1
  lên 8.
- **Open loop**: thời gian phục vụ đứng yên khoảng 1.4 giây ở mọi mức, còn hàng đợi p50 tăng từ gần 0 lên hơn 2.5 giây. Công
  suất ước từ closed loop (1.0 s mỗi request) **lạc quan**: trong open loop, thời gian phục vụ thật là 1.4 s (thứ tự câu hỏi khác,
  request đến lúc server vừa xong request trước), nên mức "0.75" thật ra đã ở cỡ 1.0 lần công suất và mức "1.0" vượt công suất;
  với nhiều request hơn, hàng đợi ở hai mức đó sẽ tăng không giới hạn. Ước công suất từ chính open loop ở tải thấp an toàn hơn.
  Phân vị 95 trên 30 mẫu nhiễu hơn p50 nhiều: lần chạy đầu, p95 hàng đợi ở hai mức trên đảo thứ tự (4.66 so với 4.40). Bootstrap
  của bài Basic 01 trên một lượt 40 request ở 0.8 request/giây cho p95 E2E 9.44 s với khoảng [7.71, 9.97] (mục 6 lý thuyết).
- **Prefix cache**: cùng slot, cùng prefix, prompt 1 740 token chỉ mất 0.12 giây thay vì 13 tới 16 giây, hơn 100 lần. Xen
  kẽ hai tài liệu thì không còn trúng (slot chỉ giữ request ngay trước). `--cache ram` lưu trạng thái theo prefix nên xen kẽ vẫn
  trúng (khoảng 0.8 giây: phải chép lại trạng thái vào context, chậm hơn lần trúng cùng slot vài lần nhưng nhanh hơn lần gọi đầu
  hàng chục lần), đổi lại lần trúng cùng slot chậm hơn một chút (0.37 so với 0.12). Một dấu cách ở đầu system prompt làm trượt
  cả hai kiểu cache.

## Lỗi hay gặp

- Đọc cả body rồi mới tách dòng: mọi token có cùng thời điểm, TTFT bằng E2E.
- Tin HTTP 200 là thành công.
- Ngủ theo khoảng cách giữa hai request: sai số cộng dồn làm tải thật thấp hơn tải định chạy.
- Đặt semaphore trước khi ngủ tới lịch: request chờ chỗ trước cả khi "đến", hàng đợi đo được sai.
- Không làm nóng server trước lượt đo đầu tiên: lần nạp model nằm trong p95 của mức tải thấp nhất.
- Bỏ quên server chạy nền sau khi đo, hoặc bind `0.0.0.0` trên máy dùng chung.
