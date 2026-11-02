# M08: Eval suite, observability, serving và đo chi phí, độ trễ

## Mục tiêu

Đưa trợ lý từ "chạy được trên máy tôi" thành một dịch vụ đo được: một lệnh chạy lại toàn bộ đánh giá và chặn hồi quy,
judge đã hiệu chuẩn với nhãn người, mỗi request có trace cho biết thời gian đi đâu, serve qua HTTP và đo dưới tải, báo
p50/p95 có khoảng tin cậy và chi phí mỗi 1 000 câu hỏi.

Dùng lại [module 20](../../modules/20-evaluation-production/README.md): eval offline/online và statistical power (mục 1),
judge và Cohen's kappa (mục 2, bài Intermediate 01), OpenTelemetry (mục 3, bài Basic 03), serving và load test open loop
(mục 4, 6, bài Intermediate 02), p50/p95 có khoảng tin cậy, chi phí, SLO (bài Basic 01, Advanced 02).

**Phần cứng:** CPU + Ollama (hoặc llama.cpp server), GPU 4GB; khoảng 10 tới 12 giờ làm.

## Việc cần làm

1. **Phần thuần** (`evals.py`, `tracing.py`): `latency_summary`, `percentile_ci`, `cost_per_query`, `cohen_kappa`,
   `regression_gate`, `Tracer`.
2. **Eval suite một lệnh** (`scripts/eval_suite.py`): retrieval (M01, M02) trên tập ghim, RAG (M03) trên 100 câu ghim,
   ngoài phạm vi và red-team (M07), agent (M06) trên S2, S3. Cache theo (cấu hình, câu hỏi); in một bảng và ghi JSON.
   `regression_gate` so với baseline đã commit; chạy được ở hai chế độ: nhanh (FakeLLM, cho CI, vài giây) và đầy đủ
   (model thật, chạy theo lịch).
3. **Hiệu chuẩn judge**: tự gán nhãn ít nhất 50 câu trả lời (mọi khẳng định có trong nguồn: có/không), đo accuracy và
   kappa giữa judge và nhãn của bạn, cho judge `qwen2.5:3b` và một judge mạnh hơn nếu có (`qwen2.5:7b` trên PC, hoặc
   API). Nếu so cặp hai cấu hình bằng judge, chấm cả hai thứ tự.
4. **Trace**: nối OpenTelemetry (hoặc `Tracer` rồi chuyển sang OTel) cho mỗi request: span gốc, retrieve (BM25, dense,
   fuse), chọn khoản, LLM (token vào/ra, model), guard. Câu hỏi trong trace đã che PII (module 19). Ghi ra JSONL, đọc lại
   bằng pandas: phần trăm thời gian mỗi span, p95 mỗi span.
5. **Serve**: một endpoint HTTP (FastAPI hoặc tương đương) trả câu trả lời và trích dẫn, gọi model qua Ollama hoặc
   llama.cpp server với mức quantize của M04. Load test **open loop** (lịch đến Poisson) ở ít nhất ba mức tải dưới và
   gần công suất đo được; tách thời gian xếp hàng khỏi thời gian phục vụ.
6. **Chi phí**: chi phí mỗi 1 000 câu cho (a) self-host trên máy của bạn (giả định giá điện/giờ GPU, ghi rõ) và (b) một
   API trả tiền theo token (giá kiểm trên trang chính thức kèm ngày, hoặc ghi GIẢ ĐỊNH), dùng số token đo từ trace.
7. `reports/EVAL_OPS.md`: bảng eval suite, kappa, bảng span, đồ thị độ trễ theo tải, SLO đề xuất (ví dụ p95 dưới X giây
   ở Y câu/phút) có căn cứ, chi phí.

## Kết quả nộp

- `legal_assistant/{evals,tracing}.py`, test M08 pass.
- `scripts/eval_suite.py`, baseline JSON, cấu hình CI chạy chế độ nhanh; service và script load test; log trace mẫu.
- `reports/EVAL_OPS.md`.

## Tiêu chí đạt

- [ ] Eval suite chạy lại bằng một lệnh; chế độ nhanh dưới 30 giây không cần mạng; cổng hồi quy làm CI đỏ khi một số đo
      tụt quá dung sai (chứng minh bằng một lần chạy cố ý làm hỏng).
- [ ] Judge có kappa với nhãn người trên ít nhất 50 câu; báo cáo nói judge sai theo hướng nào và dùng điểm judge tới đâu.
- [ ] Mỗi request có trace với ít nhất 4 loại span; bảng thời gian theo span chỉ ra nút thắt bằng số.
- [ ] p50/p95 có khoảng tin cậy bootstrap, ở ít nhất ba mức tải open loop, tách xếp hàng và phục vụ; điều kiện máy ghi
      rõ (GPU dùng chung hay không).
- [ ] Chi phí mỗi 1 000 câu cho hai phương án, mọi giá có nguồn và ngày kiểm hoặc ghi là giả định.

## Gợi ý

- Tách số đo của model (thay đổi theo máy, phiên bản Ollama) khỏi số đo tất định (retrieval): baseline của hai loại cần
  dung sai khác nhau.
- Statistical power: 100 câu chỉ phát hiện được chênh lệch lớn. Ghi cỡ tập eval nào phát hiện được chênh lệch bạn quan tâm.
- Closed loop với ít client che mất hàng đợi; open loop mới cho thấy độ trễ phình khi tải gần công suất.
- Một span LLM nên mang số token: chi phí và độ trễ đều tính từ đó, không ước lượng bằng số ký tự.
