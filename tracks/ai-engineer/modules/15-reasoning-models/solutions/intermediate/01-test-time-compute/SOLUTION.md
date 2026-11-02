# Lời giải: test-time compute trên GSM8K

## Cách làm

- `build_messages`: chọn system theo `mode` từ một dict, `ValueError` cho mode lạ; câu hỏi giữ nguyên trong message `user`.
  Prompt CoT là prompt toán Qwen khuyến nghị cho Qwen2.5, để model dùng khung `\boxed{}` nó đã được train.
- `scaling_table`: hai cột `maj`, `pass` là một lời gọi `maj_at_k` / `coverage_at_k`. `bon_logprob` và `tokens` duyệt cùng
  các khối `k` liên tiếp như `maj_at_k` (bỏ phần dư), nên bốn cột đo trên **cùng** các khối và so được với nhau.
  `tokens` là tổng token của một khối, tức chi phí thật của "chạy k lần" (không phải k × trung bình của mọi lời giải: khi bỏ
  phần dư hai số khác nhau).
- `paired_bootstrap`: một ma trận chỉ số `(n_boot, n)` dùng chung cho hai cột. Hiệu theo cặp có phương sai
  $$\mathrm{Var}(b - a) = \mathrm{Var}(a) + \mathrm{Var}(b) - 2\mathrm{Cov}(a, b)$$: câu khó thì khó với cả hai, hiệp phương sai dương,
  khoảng hẹp hơn so hai khoảng riêng lẻ. Test kiểm độ rộng khớp $$1.96 \cdot \mathrm{sd}(b - a)/\sqrt n$$ trong 20%.
- Log-prob trung bình tính lại bằng một lượt forward ở `temperature` 1 (không phải 0.7 lúc lấy mẫu), qua `logits_to_keep`
  và `gather` trừ `logsumexp` theo từng chuỗi: log-softmax cả ma trận `(8, 513, 151 936)` fp32 cần hơn 2 GB và từng làm
  bản tham chiếu hết VRAM khi GPU đang chia với Ollama. Mẫu sinh được cache **trước** bước này để lỗi ở bước sau không làm
  mất 20 phút sinh.

## Kết quả tham chiếu

200 câu đầu tập test GSM8K. PC của track (RTX 3060 12GB, dùng chung với các job Ollama của module khác), Ollama 0.13.5,
Transformers 5.22, ngày 2026-11-01.

**Phần 3, `qwen2.5:3b` (Q4_K_M), `temperature` 0, `seed` 0:**

| Chế độ | Accuracy | Token ra TB | Giây trung vị mỗi câu | Bị cắt ở `num_predict` |
| --- | --- | --- | --- | --- |
| direct | 0.115 | 3.5 | 0.085 | 0 |
| CoT | 0.775 | 338 | 4.6 | 3 |

CoT − direct: **+0.660 [+0.595, +0.730]**. Chỉ 2 câu direct đúng mà CoT sai (đọc lời giải: một câu model giải đúng tới
gần cuối rồi đặt sai đại lượng vào hộp, một câu đọc nhầm đề), 134 câu ngược lại. Giá: gấp khoảng 98 lần token ra và 54 lần
độ trễ. Cả phần chạy khoảng 19 phút (direct 2 phút, CoT 17 phút) khi GPU đang chia với một agent khác dùng Ollama.

**Phần 4, `Qwen2.5-0.5B-Instruct` bf16, 16 lời giải mỗi câu ở `temperature` 0.7, tối đa 512 token:**

| k | maj@k | pass@k | best-of-k theo log-prob | Token mỗi câu |
| --- | --- | --- | --- | --- |
| 1 | 0.398 | 0.398 | 0.398 | 311 |
| 2 | 0.401 | 0.529 | 0.440 | 621 |
| 4 | 0.476 | 0.641 | 0.464 | 1 243 |
| 8 | 0.540 | 0.736 | 0.470 | 2 486 |
| 16 | 0.585 | 0.815 | 0.450 | 4 972 |

Greedy: 0.430 với 304 token mỗi câu. maj@16 − greedy: **+0.155 [+0.095, +0.215]**. Thời gian trên RTX 3060: greedy
83 giây, 3 200 lời giải lấy mẫu 1 129 giây (batch 64), tính lại log-prob 130 giây; tổng khoảng 22 phút. GPU 4GB của
laptop chậm hơn (chưa đo trên bản tham chiếu).

## Đọc kết quả

- **CoT là thứ đáng tiền nhất ở đây.** Với toán nhiều bước, viết lời giải tăng 66 điểm; không kỹ thuật nào khác trong
  bài đến gần. Trả lời thẳng của model 3B chỉ đúng khi phép tính đủ ngắn để làm "trong đầu".
- **Một mẫu kém greedy, nhiều mẫu thắng greedy.** Lấy mẫu ở 0.7 tụt khoảng 3 điểm mỗi lời giải; bỏ phiếu 2 lời giải gần
  như không giúp (hoà phiếu lấy lời giải đầu), từ 4 lời giải mới vượt greedy, và 16 lời giải hơn 15.5 điểm với khoảng tin
  cậy không chứa 0. Đổi lại tốn 16 lần token.
- **Đường maj@k phẳng dần theo log của compute**: mỗi lần gấp đôi số mẫu thêm 6 tới 7 điểm rồi ít dần. So với phần 3:
  `qwen2.5:3b` greedy (0.775, 338 token) vẫn hơn 0.5B bỏ phiếu 16 lời giải (0.585, gần 5 000 token). Ở đây model lớn hơn rẻ
  hơn **và** đúng hơn; test-time compute không thay được 6 lần tham số.
- **Khoảng cách pass@16 − maj@16 là 23 điểm**: 81.5% câu có ít nhất một lời giải đúng trong 16, nhưng bỏ phiếu chỉ chọn
  được 58.5%. Đó là phần một verifier tốt có thể lấy lại, và là lý do người ta train verifier/reward model (mục 2 lý thuyết)
  hoặc dùng verifier chính xác khi có (code chạy test).
- **Log-prob của chính model là verifier tệ**: best-of-k theo log-prob tăng chậm rồi **giảm** từ k = 8 sang 16. Lời giải
  có log-prob trung bình cao thường là lời giải ngắn, trơn tru, nhiều token "dễ" (lặp lại đề bài), không phải lời giải đúng.
  Chọn theo nó tối ưu đúng thứ không liên quan tới độ đúng: một bản thu nhỏ của reward hacking khi best-of-N với verifier tồi.

## Bẫy thường gặp

- Tính log-softmax trên cả vocab ở fp32 cho cả batch: hết VRAM (151 936 cột). Lấy `gather` trừ `logsumexp` từng chuỗi.
- Không cache lời giải trước các bước sau: một lỗi ở bước log-prob làm mất 20 phút sinh.
- So maj@k với greedy bằng hai khoảng tin cậy riêng: hai khoảng chồng nhau dù hiệu theo cặp rõ ràng khác 0.
- Đặt `num_predict` quá thấp cho CoT: lời giải bị cắt trước hộp, bộ trích lấy một số giữa chừng.
