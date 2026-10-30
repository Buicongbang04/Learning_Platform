# Hướng làm: review design doc VietSky

Bài không có code lời giải. Dưới đây là các lỗi đã cài vào doc, con số tính lại, và rubric. Bản tham chiếu
(`review.py`, `claims.yaml` 6 claim, `REVIEW.md` 9 vấn đề khoảng 1 400 từ) đã qua toàn bộ test của bài.

## `review.py`

Một bảng `kind → tập input bắt buộc` dùng chung cho kiểm đầu vào; mỗi kind một công thức như Basic 01, Basic 02,
Intermediate 01. `rel_error` chia cho giá trị **tính lại** (đúng), không chia cho con số của doc: chia cho con số sai
thì một lỗi gấp 7 lần chỉ hiện là 86%.

## Kiểm số liệu

Sáu con số định lượng của mục 4 (id có thể khác bản của bạn):

| Claim | Doc | Tính lại | Lệch | Nhận xét |
| --- | --- | --- | --- | --- |
| Chi phí / 1 000 request | 6.80 USD | 10.00 USD | 32% | output tính theo giá input |
| Chi phí tháng | 122 400 USD | 122 400 USD | 0% | phép nhân đúng nhưng dùng con số sai ở trên: thật là 180 000, **vượt ngân sách 150 000** |
| Request đồng thời | 1.9 | 120 | 98% | chia thay vì nhân (Little) |
| Trọng số 4-bit | 3.8e9 byte | 3.8e9 byte | 0% | đúng |
| KV cache / token | 401 408 byte | 57 344 byte | 600% | dùng 28 attention head thay cho 4 KV head; GPU 24 GB chứa khoảng 40 chuỗi 8k, không phải 6 |
| Số GPU | 6 | 8 | 25% | quên headroom 20% |

Hai bài học: lỗi lan truyền (chi phí tháng) không bắt được bằng kiểm từng dòng; và lỗi có thể nằm về phía an toàn
(KV cache thừa 7 lần làm thuê thừa GPU) hoặc phía nguy hiểm (chi phí thiếu 32%, đồng thời thiếu 60 lần).

## Các vấn đề đã cài

| # | Vấn đề | Mức độ | Đề xuất cốt lõi |
| --- | --- | --- | --- |
| 1 | Agent tự hoàn tới 12 triệu đồng, email đưa nguyên văn vào prompt: prompt injection gián tiếp ra tiền thật | chặn ship | điều kiện hoàn tiền kiểm bằng code; người duyệt; tool chỉ trên booking của người gửi đã xác thực; red-team |
| 2 | Semantic cache dùng chung, cosine 0.85, cho cả câu trả lời cá nhân: lộ booking của khách khác, gộp nhầm "đổi" với "huỷ" | chặn ship | chỉ cache câu hỏi chung, khoá kèm phiên bản chính sách |
| 3 | Log nguyên văn email, mã đặt chỗ, số hộ chiếu sang SaaS nước ngoài, lưu vô thời hạn | chặn ship | ẩn PII trước log và trước API, thời hạn lưu, hạ tầng được phê duyệt |
| 4 | Fine-tune hằng tháng để "học" chính sách đổi hằng tuần, không trích dẫn | nghiêm trọng | RAG có ngày hiệu lực, trích dẫn, từ chối khi thiếu căn cứ |
| 5 | Chi phí tính thiếu, thực tế vượt ngân sách | nghiêm trọng | sửa; caching, model nhỏ cho phân loại, rút gọn lịch sử |
| 6 | p95 bằng tổng p95 từng bước; yêu cầu viết theo trung bình; đồng thời 1.9 | nghiêm trọng | SLO theo p95 đo trên trace từng request; Little; backpressure |
| 7 | Một nhà cung cấp, retry ngay 5 lần (retry storm), không timeout, không fallback | nghiêm trọng | timeout, retry có backoff và jitter, circuit breaker, provider thứ hai, chế độ suy giảm |
| 8 | "Độ chính xác 95%" không định nghĩa; model fine-tune tự chấm mình; thang 1–5 đổi thành phần trăm | nghiêm trọng | golden set có người chấm, judge khác model và hiệu chuẩn, chỉ số kinh doanh (tự giải quyết, CSAT) |
| 9 | Triển khai 100% cùng lúc | nghiêm trọng | canary 5% → 25% → 100% với tiêu chí dừng |
| 10 | Dự phòng self-host định cỡ sai, không rõ mục đích | nên sửa | tính lại; nói rõ dự phòng cho sự cố hay cho đàm phán giá |

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 10 | Mọi test pass |
| Ba lỗi chặn ship | 25 | Tìm đủ vấn đề 1–3, giải thích được cơ chế tấn công hoặc rò rỉ cụ thể, không chỉ "nên cẩn thận" |
| Kiến trúc và đánh giá | 20 | Vấn đề 4, 8, 9: vì sao fine-tune sai cho kiến thức đổi nhanh; vì sao tự chấm và thang 1–5 không phải độ chính xác |
| Số liệu | 20 | Đủ 6 claim; bắt 4 lỗi; tự lần được lỗi lan truyền sang chi phí tháng và kết luận vượt ngân sách; nêu lỗi p95 |
| Độ tin cậy và vận hành | 10 | Vấn đề 7 với đề xuất cụ thể (con số timeout, số lần retry, điều kiện breaker) |
| Chất lượng review | 15 | Xếp mức độ đúng, tóm tắt cho người ra quyết định, đề xuất làm được (không chỉ "dùng guardrails"), giọng xây dựng |

Đạt từ 70 điểm. Review chỉ có lỗi số học, không có ba lỗi chặn ship, không quá 45 điểm.
