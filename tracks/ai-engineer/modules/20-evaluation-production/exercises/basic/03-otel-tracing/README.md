---
title: Trace một pipeline RAG bằng OpenTelemetry
level: basic
services: []
files:
  - path: starter/tracing.py
    note: 2 hàm và 1 exporter TODO
  - path: tests/test_tracing.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/20-evaluation-production/exercises/basic/03-otel-tracing -q
---

## Mục tiêu

Tự nối OpenTelemetry SDK vào một pipeline RAG: mỗi request là một trace, retrieval và lời gọi LLM là span con mang token,
chi phí và model; câu hỏi đi vào trace đã che PII; lấy mẫu theo cả trace; và một exporter ghi span ra tệp JSON Lines
để đọc lại bằng pandas. Đó là phần lõi mà Langfuse, Phoenix hay mọi backend observability khác nhận vào.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Trong `starter/tracing.py` (`redact` đã có sẵn):

1. `make_provider(exporter, sample_ratio=1.0, service_name="zalo-rag") -> TracerProvider`: tạo `TracerProvider` mới
   (không gọi `trace.set_tracer_provider`), với resource `service.name`, sampler **lấy mẫu theo trace**: span gốc được
   giữ với xác suất `sample_ratio` theo trace id, span con theo quyết định của cha (`ParentBased` bọc
   `TraceIdRatioBased`). Gắn exporter bằng `SimpleSpanProcessor`. `ValueError` khi `sample_ratio` ngoài [0, 1].
2. `JsonlSpanExporter(path).export(spans)`: **nối thêm** vào tệp mỗi span một dòng JSON (UTF-8, giữ nguyên chữ tiếng Việt)
   với đúng các khoá: `name`, `trace_id` (32 ký tự hex), `span_id` (16 ký tự hex), `parent_span_id` (16 ký tự hex hoặc
   `null` với span gốc), `start_ns`, `end_ns`, `duration_ms`, `status` (`"UNSET"`, `"OK"` hoặc `"ERROR"`), `service`
   (giá trị `service.name` của resource), `attributes` (dict; giá trị kiểu tuple ghi thành list). Trả
   `SpanExportResult.SUCCESS`.
3. `traced_answer(question, retrieve, generate, tracer, prices) -> str`. `retrieve(question)` trả list dict có `id`;
   `generate(question, docs)` trả dict `text`, `model`, `input_tokens`, `output_tokens`; `prices` có `input`, `output`
   tính USD mỗi triệu token. Tạo:
   - span gốc `rag.request` với `app.question` = `redact(question)`, `app.cost_usd`, `app.answer_chars`;
   - span con `rag.retrieve` với `rag.top_k` (số tài liệu) và `rag.doc_ids` (list id dạng chuỗi);
   - span con `llm.chat` với `gen_ai.operation.name` = `"chat"`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`,
     `gen_ai.usage.output_tokens`, `app.cost_usd`.

   Trả `text`. Khi `retrieve` hay `generate` ném lỗi: span của bước đó và span gốc có status `ERROR` kèm event
   `exception`, và lỗi vẫn được ném ra cho người gọi.

## Tiêu chí đạt

- Ba span cùng một trace, `rag.retrieve` và `llm.chat` là con của `rag.request`, đúng thứ tự thời gian.
- Đủ thuộc tính với tên theo semantic conventions GenAI của OpenTelemetry; chi phí đúng; không span nào chứa email hay
  số điện thoại thô.
- Lỗi được ghi vào span và vẫn ném ra; span bước chạy xong không bị đánh lỗi.
- Với `sample_ratio=0.3` trên 400 request: mỗi trace giữ đủ cả ba span hoặc không span nào, tỉ lệ trace giữ lại trong
  [0.22, 0.38]; ratio 0 không ghi gì.
- Tệp JSON Lines đúng khoá, id hex đúng độ dài, `parent_span_id` khớp span gốc cùng trace.

## Gợi ý

### Gợi ý 1

`tracer.start_as_current_span(name)` dùng như context manager: span lồng bên trong tự thành con, và mặc định nó đã ghi
exception và đặt status lỗi khi có ngoại lệ đi qua. Đọc thuộc tính của `ReadableSpan` trong tài liệu SDK: `context`,
`parent`, `start_time`, `end_time`, `status`, `attributes`, `resource`.

### Gợi ý 2

`f"{x:032x}"` in một số nguyên thành hex 32 ký tự có số 0 đứng đầu. Thuộc tính kiểu list được SDK lưu thành tuple, nên
`json.dumps` vẫn ghi được nhưng test so với list: đổi tường minh cho rõ.
