# Hướng làm: dịch vụ RAG có trace, load test, SLO và chi phí

Bài không có code lời giải cho phần dịch vụ: kiến trúc, cách đo và báo cáo là của bạn. Dưới đây là các quyết định cần cân
nhắc, kết quả của một bản tham chiếu để so, và rubric chấm `REPORT.md`. Bốn hàm đọc trace được chấm có đặc tả trong notebook.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Span | `rag.request` gốc; con `guard.input`, `rag.retrieve`, `llm.chat`, `guard.output` | mỗi bước có thể chậm hay hỏng riêng; trace trả lời "thời gian đi đâu" mà không cần đoán |
| Thuộc tính LLM | `gen_ai.usage.*`, model, TTFT, `prompt_eval_s` và `eval_s` lấy từ dòng cuối stream của Ollama, chi phí | tách thời gian model chạy khỏi thời gian chờ trong server |
| Retrieval | `bge-m3` qua Ollama, top-3 trên cache, mỗi đoạn cắt 800 ký tự | prompt khoảng 800 token, cùng cỡ RAG thật nhỏ |
| Sinh | `qwen2.5:3b`, `temperature` 0, `num_predict` 160, stream | TTFT là SLI của chat |
| Tải | đo thời gian phục vụ trước (8 request), rồi open loop 0.15, 0.3, 0.45 request/giây, 30 request mỗi mức | dưới công suất ước khoảng 0.5 request/giây; Ollama dùng chung nên không đẩy quá công suất |
| SLI/SLO | E2E p95 không quá 5 giây, mục tiêu 95% request tốt (lỗi là xấu) | chat ngắn có stream; TTFT p95 dưới 2 giây là SLO thứ hai nên theo dõi |
| Chi phí API | giá Claude Haiku 5.5 trong bảng module 11 (kiểm 2026-11-01), token đo từ chính trace | chi phí theo phân phối token thật |
| Chi phí self-host | giá GPU **giả định** 0.30 USD/giờ, chia cho thông lượng ở mức đạt SLO | không có giá thật cho máy dùng chung; ghi rõ là giả định |

## Kết quả tham chiếu

PC của track, Ollama 0.13.5, RTX 3060 **dùng chung** với một job train khác, một request mỗi model (`Parallel:1`). Thời gian
phục vụ một request lúc máy rảnh: 1.2 tới 2.3 giây (lần đầu 7 giây vì nạp model). Chạy cả ba mức và thí nghiệm cache khoảng
10 phút.

| Mức tải (request/giây) | E2E p50 (s) | E2E p95 [CI 95%] (s) | TTFT p50 (s) | `llm.chat` p50 / p95 (s) | Chờ ngoài model p50 / p95 (s) | Đạt SLO 5 s | Burn rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.15 | 2.54 | 4.15 [3.48, 4.48] | 0.63 | 2.12 / 3.74 | 0.49 / 1.53 | 30/30 | 0 |
| 0.30 | 3.25 | 9.14 [7.18, 9.29] | 1.30 | 2.88 / 8.83 | 1.15 / 6.37 | 20/30 | 6.7 |
| 0.45 | 3.02 | 7.42 [5.70, 8.25] | 1.51 | 2.65 / 7.09 | 1.42 / 5.60 | 24/30 | 4.0 |

`rag.retrieve` khoảng 350 ms ở mọi mức (embed câu hỏi qua Ollama chiếm phần lớn, nhân ma trận trên 61 425 vector phần còn lại),
hai guardrail tất định dưới 0.2 ms. `llm.chat` chiếm khoảng 90% thời gian request. Token trung bình mỗi request: khoảng 760 tới
800 vào, 55 tới 64 ra.

Đọc bảng:

- **Hàng đợi, không phải model, làm p95 xấu đi**: thời gian model chạy (`prompt_eval` cộng `eval`) đứng yên khoảng 1.2 tới 1.5
  giây, còn phần chờ bên trong Ollama tăng từ 0.5 lên 1.2 tới 1.4 giây ở p50 và lên 5 tới 6 giây ở p95.
- **Mức 0.30 xấu hơn mức 0.45** ở p95. Không phải nghịch lý mà là nhiễu: 30 request, GPU dùng chung với một job khác (một đợt
  bận của job đó trùng lượt đo), và khoảng tin cậy hai mức chồng lên nhau. Báo cáo phải nói vậy thay vì vẽ đường cong trơn.
- **Capacity ở SLO**: chỉ mức 0.15 đạt SLO E2E p95 5 giây. Với tải đều cỡ đó, một GPU dùng chung phục vụ khoảng 540 request
  mỗi giờ.
- **Chi phí mỗi 1 000 request**: theo giá Haiku 5.5 và token đo được, khoảng 0.10 tới 0.11 USD (chưa tính embed). Self-host
  với GPU giả định 0.30 USD/giờ ở 540 request/giờ: khoảng 0.56 USD, đắt hơn API năm lần ở lưu lượng này; self-host chỉ rẻ hơn
  khi GPU được dùng hết công suất với batching (vLLM, mục 4 lý thuyết) hoặc khi lý do là dữ liệu chứ không phải tiền.
- **Prompt caching không cho lợi ích đo được ở đây**: với system prompt có một ví dụ dài (khoảng 900 token vào), trung vị thời
  gian xử lý prompt là 0.34 s khi phần cố định đứng trước và 0.28 s khi một dấu thời gian đứng đầu (TTFT 0.63 so với 0.55 s).
  Prefill 900 token trên GPU đã chỉ mất cỡ 0.3 giây, nên phần tiết kiệm được chìm trong nhiễu của GPU dùng chung. Cache đáng giá
  khi prefill đắt: prefix hàng nghìn token, CPU (bài Intermediate 02 đo khoảng 100 lần trên llama.cpp CPU), hoặc API tính tiền
  theo token (module 11). Một kết quả "không thấy lợi ích" được đo và giải thích có giá trị hơn một khẳng định không đo.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 10 | Mọi test pass |
| Trace | 15 | Span cho mọi bước, thuộc tính GenAI, PII đã che, tách thời gian chờ khỏi thời gian model chạy |
| Load test | 20 | Đo thời gian phục vụ trước, open loop ít nhất 3 mức với ít nhất 30 request mỗi mức, không vượt công suất trên tài nguyên dùng chung |
| Thống kê và SLO | 20 | p95/p99 có khoảng tin cậy, SLO có lý do, burn rate từng mức, không vẽ xu hướng từ chênh lệch nằm trong nhiễu |
| Chi phí | 15 | Token đo từ trace, giá có ngày kiểm hoặc ghi giả định, self-host theo thông lượng ở mức SLO, so với API |
| Báo cáo vận hành | 20 | Khuyến nghị capacity có số ở đầu, thí nghiệm cache có kết luận trung thực, runbook với cảnh báo cụ thể, giới hạn |

Đạt từ 70 điểm. Báo cáo dùng closed loop rồi báo độ trễ như của người dùng thật, hoặc tính chi phí self-host theo thông lượng tối
đa thay vì thông lượng ở mức SLO, không quá 50 điểm.
