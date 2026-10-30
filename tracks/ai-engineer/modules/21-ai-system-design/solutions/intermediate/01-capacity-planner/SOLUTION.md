# Lời giải: máy tính capacity

## Cách làm

Mỗi hàm là một công thức một dòng; phần đáng nghĩ là ghép chúng đúng thứ tự:

1. Lưu lượng: `peak_rps = requests_per_day / 86400 * peak_to_avg`.
2. Mỗi dòng benchmark là một **điểm vận hành**: giữ `c` request đồng thời thì mỗi request mất
   `latency = ttft + n_out * tpot`, và theo định luật Little một GPU phục vụ `c / latency` request/giây.
3. Lọc các điểm đạt cả hai SLO, lấy điểm có thông lượng cao nhất.
4. `gpus = ceil(peak * (1 + headroom) / rps_per_gpu - 1e-9) + redundancy`.
5. Chi phí: self-host là cố định (`gpus * giá/giờ * 730`), API là biến đổi; hoà vốn ở `fixed / (api - self)`.

## Đọc bảng benchmark (300 token output)

| Concurrency | Latency p95 | Request/giây mỗi GPU |
| --- | --- | --- |
| 1 | 3.68 s | 0.272 |
| 4 | 4.32 s | 0.926 |
| 8 | 4.98 s | 1.606 |
| 16 | 6.30 s | 2.540 |
| 32 | 8.95 s | 3.575 |
| 64 | 14.70 s | 4.354 |

Từ 1 lên 32 request đồng thời, mỗi request chậm hơn 2.4 lần nhưng GPU phục vụ gấp 13 lần. Đó là batching: decode bị
chặn bởi băng thông bộ nhớ, đọc trọng số một lần dùng cho cả batch (bài Basic 03). Vì vậy câu hỏi đúng không phải "GPU
chạy được bao nhiêu request" mà "ở SLO này, GPU chạy được bao nhiêu":

| SLO (TTFT 1 s) | Điểm vận hành | GPU cho 20 request/giây (headroom 20%, N+1) |
| --- | --- | --- |
| E2E 10 s | c = 32, 3.575 rps | 8 |
| E2E 8 s | c = 16, 2.540 rps | 11 |
| E2E 6 s | c = 8, 1.606 rps | 16 |
| E2E 10 s, output 150 token | c = 32, 6.737 rps | 5 |

Hai đòn bẩy rẻ nhất không nằm ở hạ tầng: **SLO** (thương lượng với product: stream thì SLO áp lên TTFT, E2E nới được)
và **độ dài output** (câu trả lời ngắn một nửa thì số GPU giảm từ 8 xuống 5).

## API hay self-host

8 GPU với giá thuê giả định 1.20 USD/giờ là 7 008 USD/tháng. Với API 0.0035 USD/request, hoà vốn ở khoảng 2.0 triệu
request/tháng; nếu so với một model nhỏ giá 0.000352 USD/request (Claude Haiku 5.5, giá kiểm 2026-10-30, request 3 350
token input trong đó 1 200 đọc từ cache, 250 token output) thì phải 19.9 triệu request/tháng. Con số này còn thiếu: lương kỹ sư vận hành, GPU dự phòng cho ngày cao điểm (thuê cả tháng
cho vài ngày), thời gian benchmark lại mỗi khi đổi model. Self-host thắng rõ khi lưu lượng lớn và đều, khi dữ liệu
không được rời hạ tầng, hoặc khi cần model đã fine-tune mà provider không phục vụ; còn lại API thường rẻ hơn tổng thể.

## Bẫy thường gặp

- Chọn concurrency lớn nhất còn đạt SLO thay vì thông lượng lớn nhất (test thứ tư bắt lỗi này).
- Chia `peak_rps` cho thông lượng ở concurrency 1 (không batching): 74 GPU chưa tính headroom, thay vì 8.
- Quên headroom hoặc N+1: một GPU hỏng lúc cao điểm là vi phạm SLO.
- Dùng benchmark đo ở prompt 500 token cho hệ thống có prompt 3 000 token: TTFT và bộ nhớ KV khác hẳn. Benchmark phải
  dùng phân phối độ dài prompt/output giống production.
