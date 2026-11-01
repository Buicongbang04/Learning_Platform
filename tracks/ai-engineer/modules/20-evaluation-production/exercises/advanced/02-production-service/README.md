---
title: Dịch vụ RAG pháp luật có trace, load test, SLO và chi phí (portfolio)
level: advanced
services: []
files:
  - path: starter/service.ipynb
    note: 4 hàm TODO, dịch vụ tự thiết kế
  - path: starter/REPORT.md
    note: Báo cáo vận hành
  - path: tests/test_service.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py zalo-legal
  - ollama pull qwen2.5:3b
  - ollama pull bge-m3
  - uv run jupyter lab tracks/ai-engineer/modules/20-evaluation-production/exercises/advanced/02-production-service/starter/service.ipynb
  - uv run pytest tracks/ai-engineer/modules/20-evaluation-production/exercises/advanced/02-production-service -q
---

## Mục tiêu

Vận hành một dịch vụ LLM nhỏ như một kỹ sư production: mọi request có trace, biết thời gian đi đâu, đo dưới tải thật, đặt
SLO có căn cứ, tính được mỗi 1 000 request tốn bao nhiêu theo hai cách triển khai, và viết một báo cáo mà người trực vận hành
dùng được. Đây là bài portfolio: báo cáo và notebook của bạn là thứ đưa vào hồ sơ.

## Đề bài

**Phần cứng:** GPU 4GB · ~360 phút

Thời gian trên là thời gian làm bài. `qwen2.5:3b` chạy hết trên GPU 4GB; chỉ có CPU thì mỗi request chậm hơn nhiều lần
và các mức tải phải hạ tương ứng (chưa đo). Bản tham chiếu chạy khoảng 15 phút cho ba mức tải và thí nghiệm cache. Cần
cache `bge-m3.npy` của module 13. Có thể thay Ollama bằng llama.cpp server (bài Intermediate 02) với một model GGUF.

1. Trong `starter/service.ipynb`, cell chấm điểm: `load_spans`, `span_table`, `cost_per_1k`, `root_slo` đúng mô tả trong
   notebook (đọc trace JSON Lines của bài Basic 03).
2. Phần `explore` là thiết kế của bạn, theo năm bước gợi ý trong notebook: dịch vụ có span cho guardrail, retrieval, LLM
   (stream, có TTFT); đo thời gian phục vụ rồi load test open loop ở ba mức tải tới khoảng 80% công suất, mỗi mức ít nhất 30
   request; bảng span, p50/p95/p99 có khoảng tin cậy, SLO và burn rate; chi phí self-host (giá GPU **giả định**, ghi rõ) và API
   (bảng giá có ngày kiểm); thí nghiệm prompt caching.
3. Viết `starter/REPORT.md` theo khung, rồi làm phần trắc nghiệm của bài trong app.

**Một `REPORT.md` tốt**:

- Mở bằng **capacity và SLO có số**, ví dụ minh hoạ với số bịa: "ở 0.3 request/giây, E2E p95 là X giây [khoảng tin cậy];
  SLO đề xuất E2E p95 dưới Y giây đạt tới 0.4 request/giây; vượt mức đó hàng đợi chiếm phần lớn độ trễ".
- Bảng span theo mức tải và câu đọc bảng: bước nào chiếm thời gian, bước nào đổi theo tải (hàng đợi ở đâu).
- Chi phí mỗi 1 000 request: self-host theo thông lượng **ở mức SLO** (không phải thông lượng tối đa), API có và không có
  cache, và điểm hoà vốn (module 21).
- Prompt caching: TTFT hoặc thời gian xử lý prompt khi phần cố định đứng trước so với khi có thứ thay đổi đứng đầu.
- **Runbook** ngắn: cảnh báo nào (burn rate, cửa sổ), làm gì khi cảnh báo, dashboard cần những panel nào.
- **Giới hạn**: máy dùng chung, một model, phân phối câu hỏi lấy từ tập ghim chứ không phải lưu lượng thật.

## Tiêu chí đạt

- `load_spans`, `span_table` đúng cột, thứ tự, phân vị, tỉ lệ lỗi và tỉ lệ thời gian trên tệp trace tự dựng; `cost_per_1k`
  coi span gốc thiếu chi phí là 0; `root_slo` tính request lỗi là xấu; cả hai báo `ValueError` khi không có span gốc.
- `REPORT.md` không còn TODO, ít nhất 600 từ, có ít nhất 6 dòng bảng.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Viết dịch vụ đồng bộ (một hàm `answer`) rồi chạy nó trong `asyncio.to_thread` từ load generator của bài Intermediate 02;
context của OpenTelemetry đi theo luồng nên span vẫn đúng cha con. Ghi mỗi mức tải ra một tệp trace riêng để so.

### Gợi ý 2

Ollama trả `prompt_eval_duration` và `eval_duration` ở dòng cuối của stream: so tổng hai số đó với thời gian span `llm.chat`
để tách thời gian chờ trong Ollama khỏi thời gian model chạy. Với thí nghiệm cache, cần một phần cố định đủ dài (vài trăm
token trở lên) và các request liên tiếp cùng một biến thể, vì server giữ KV của request ngay trước.
